# 企业微信智能机器人 - WebSocket 长连接接入

基于企业微信官方文档实现的智能机器人长连接客户端，支持消息接收、流式回复、主动推送等功能。

## 特性

- ✅ **WebSocket 长连接** - 无需公网 IP，内网可访问
- ✅ **免加解密** - WSS 协议自带加密，业务层无需处理
- ✅ **原生流式** - 完美支持 LLM 打字机输出
- ✅ **心跳保活** - 自动心跳维持连接
- ✅ **断线重连** - 自动重连机制
- ✅ **素材上传** - 支持分片上传临时素材

## 快速开始

### 1. 准备工作

在企业微信管理后台：
1. 进入「智能机器人」配置页面
2. 开启「API 模式」并选择「长连接」
3. 获取 **BotID** 和 **Secret**

### 2. 安装依赖

```bash
cd wechat-robot
pip install -r requirements.txt
```

### 3. 配置

复制配置文件模板并填写凭证：

```bash
copy config.example.json config.json
```

编辑 `config.json`：

```json
{
  "bot_id": "YOUR_BOT_ID",
  "secret": "YOUR_SECRET",
  "websocket_url": "wss://openws.work.weixin.qq.com",
  "heartbeat_interval": 30,
  "reconnect_delay": 5,
  "max_reconnect_attempts": 10
}
```

### 4. 运行

```bash
python wecom_bot.py
```

## 使用示例

### 基础用法

```python
import asyncio
from wecom_bot import WeComBot

bot = WeComBot('config.json')

@bot.on_message
async def handle_message(data):
    body = data.get('body', {})
    msgtype = body.get('msgtype')
    req_id = data.get('headers', {}).get('req_id')
    
    if msgtype == 'text':
        content = body.get('text', {}).get('content', '')
        print(f"收到消息：{content}")
        
        # 回复消息
        await bot.respond_msg(req_id, {
            "msgtype": "text",
            "text": {
                "content": "收到您的消息了！"
            }
        })

@bot.on_event
async def handle_event(data):
    event_type = data.get('body', {}).get('event', {}).get('eventtype')
    req_id = data.get('headers', {}).get('req_id')
    
    if event_type == 'enter_chat':
        # 回复欢迎语
        await bot.respond_welcome_msg(req_id, {
            "msgtype": "text",
            "text": {
                "content": "您好！我是智能助手~"
            }
        })

asyncio.run(bot.run())
```

### 流式消息回复

```python
@bot.on_message
async def handle_message(data):
    req_id = data.get('headers', {}).get('req_id')
    stream_id = str(uuid.uuid4())
    
    # 第一段
    await bot.respond_msg(req_id, {
        "msgtype": "stream",
        "stream": {
            "id": stream_id,
            "finish": False,
            "content": "正在思考..."
        }
    })
    
    # 中间内容
    await bot.respond_msg(req_id, {
        "msgtype": "stream",
        "stream": {
            "id": stream_id,
            "finish": False,
            "content": "这是更多思考内容..."
        }
    })
    
    # 完成
    await bot.respond_msg(req_id, {
        "msgtype": "stream",
        "stream": {
            "id": stream_id,
            "finish": True,
            "content": "思考完毕！"
        }
    })
```

### Markdown 消息

```python
await bot.respond_msg(req_id, {
    "msgtype": "markdown",
    "markdown": {
        "content": "# 标题\n**加粗**\n*斜体*\n- 列表项\n[链接](https://...)"
    }
})
```

### 主动推送消息

```python
# 单聊推送
await bot.send_msg("userid123", 1, {
    "msgtype": "markdown",
    "markdown": {
        "content": "这是一条主动推送的消息"
    }
})

# 群聊推送
await bot.send_msg("chatid456", 2, {
    "msgtype": "markdown",
    "markdown": {
        "content": "群聊通知内容"
    }
})
```

### 上传并发送图片

```python
import base64

async def send_image(chat_id, image_path):
    # 读取图片
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # 初始化上传
    upload_id = await bot.upload_media_init(
        file_type="image",
        filename="test.png",
        total_size=len(image_data),
        total_chunks=1
    )
    
    # 上传分片
    base64_data = base64.b64encode(image_data).decode()
    await bot.upload_media_chunk(upload_id, 0, base64_data)
    
    # 完成上传
    result = await bot.upload_media_finish(upload_id)
    media_id = result.get('media_id')
    
    # 发送图片
    await bot.send_msg(chat_id, 1, {
        "msgtype": "image",
        "image": {
            "media_id": media_id
        }
    })
```

## 消息类型支持

| 类型 | msgtype | 说明 |
|------|---------|------|
| 文本 | text | 普通文本消息 |
| 流式 | stream | 流式消息（打字机效果）|
| Markdown | markdown | Markdown 格式消息 |
| 模板卡片 | template_card | 交互式卡片（仅单聊）|
| 图片 | image | 图片消息 |
| 文件 | file | 文件消息 |
| 语音 | voice | 语音消息 |
| 视频 | video | 视频消息 |

## 事件类型支持

| 事件 | eventtype | 说明 |
|------|-----------|------|
| 进入会话 | enter_chat | 用户首次进入单聊 |
| 卡片点击 | template_card_event | 用户点击模板卡片 |
| 用户反馈 | feedback_event | 用户对回复进行反馈 |
| 连接断开 | disconnected_event | 新连接建立导致旧连接断开 |

## 频率限制

- 每个会话：**30 条/分钟**，**1000 条/小时**
- 素材上传：**30 次/分钟**，**1000 次/小时**

## 文件大小限制

| 类型 | 限制 |
|------|------|
| 图片 | ≤ 2MB (png/jpg/jpeg/gif) |
| 语音 | ≤ 2MB (amr) |
| 视频 | ≤ 10MB (mp4) |
| 普通文件 | ≤ 20MB |

## 注意事项

1. **每个机器人同一时间只能保持一个有效连接** - 新连接会踢掉旧连接
2. **收到回调后需在 5 秒内回复** - 欢迎语和卡片更新有超时限制
3. **流式消息需在 6 分钟内完成** - 否则自动结束
4. **临时素材有效期 3 天** - 过期需重新上传
5. **心跳间隔建议 30 秒** - 防止连接被网关切断

## 与 OpenClaw 集成

将 `WeComBot` 集成到 OpenClaw 中，可实现企业微信机器人的智能化：

```python
# 在 OpenClaw 中调用 LLM 处理消息
@bot.on_message
async def handle_message(data):
    req_id = data.get('headers', {}).get('req_id')
    content = data.get('body', {}).get('text', {}).get('content', '')
    
    # 调用 OpenClaw/LLM 处理
    response = await call_llm(content)
    
    # 流式回复
    stream_id = str(uuid.uuid4())
    for chunk in response:
        await bot.respond_msg(req_id, {
            "msgtype": "stream",
            "stream": {
                "id": stream_id,
                "finish": False,
                "content": chunk
            }
        })
    
    # 结束流式
    await bot.respond_msg(req_id, {
        "msgtype": "stream",
        "stream": {
            "id": stream_id,
            "finish": True,
            "content": ""
        }
    })
```

## 参考文档

- [企业微信智能机器人长连接官方文档](https://developer.work.weixin.qq.com/document/path/101463)
