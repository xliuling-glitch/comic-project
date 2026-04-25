# 企业微信 (WeCom) 技能

## 功能

通过企业微信机器人 Webhook 发送消息到企业微信群聊。

## 配置

在 `TOOLS.md` 中添加：

```markdown
### 企业微信

- Webhook: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
```

## 使用方法

### 发送文本消息

```bash
curl "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"text","text":{"content":"Hello World"}}'
```

### 发送 Markdown 消息

```bash
curl "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"msgtype":"markdown","markdown":{"content":"**Hello World**"}}'
```

## API 参考

- [企业微信机器人 API 文档](https://developer.work.weixin.qq.com/document/path/91770)
