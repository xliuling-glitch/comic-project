#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw + 企业微信机器人集成示例
将企业微信消息接入 OpenClaw，由 AI 处理并回复
"""

import asyncio
import json
import uuid
import os
import sys

# 添加父目录到路径，以便导入 wecom_bot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wecom_bot import WeComBot


class OpenClawWeComIntegration:
    """OpenClaw 与企业微信机器人集成"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.bot = WeComBot(config_path)
        self._setup_callbacks()
    
    def _setup_callbacks(self):
        """设置回调处理"""
        
        @self.bot.on_message
        async def handle_message(data):
            """处理用户消息"""
            body = data.get('body', {})
            msgtype = body.get('msgtype')
            req_id = data.get('headers', {}).get('req_id')
            from_userid = body.get('from', {}).get('userid', 'unknown')
            chat_type = body.get('chattype', 'single')
            
            print(f"[消息] 来自 {from_userid} ({chat_type}): {msgtype}")
            
            if msgtype == 'text':
                content = body.get('text', {}).get('content', '')
                await self._process_text_message(req_id, content, from_userid, chat_type)
                
            elif msgtype == 'mixed':
                # 图文混排消息
                print(f"[混合消息] 内容：{body}")
                
        @self.bot.on_event
        async def handle_event(data):
            """处理事件"""
            body = data.get('body', {})
            event_type = body.get('event', {}).get('eventtype')
            req_id = data.get('headers', {}).get('req_id')
            from_userid = body.get('from', {}).get('userid', 'unknown')
            
            print(f"[事件] {event_type} - 来自 {from_userid}")
            
            if event_type == 'enter_chat':
                await self._handle_enter_chat(req_id, from_userid)
                
            elif event_type == 'template_card_event':
                # 模板卡片点击事件
                event_data = body.get('event', {})
                print(f"[卡片点击] {event_data}")
                
            elif event_type == 'disconnected_event':
                print("[警告] 连接被断开，可能是有新连接建立")
    
    async def _process_text_message(self, req_id: str, content: str, 
                                     from_userid: str, chat_type: str):
        """
        处理文本消息
        
        这里可以集成 OpenClaw 或任何 LLM API
        """
        # TODO: 在这里调用 OpenClaw / LLM 处理消息
        # 示例：简单的 AI 回复逻辑
        
        stream_id = str(uuid.uuid4())
        
        # 模拟思考中
        await self.bot.respond_msg(req_id, {
            "msgtype": "stream",
            "stream": {
                "id": stream_id,
                "finish": False,
                "content": "🤔 正在思考..."
            }
        })
        
        # 模拟 AI 回复 - 实际使用时替换为真实的 LLM 调用
        response = await self._call_ai(content, from_userid, chat_type)
        
        # 流式发送回复
        chunks = self._split_response(response)
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            await self.bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": is_last,
                    "content": chunk
                }
            })
            if not is_last:
                await asyncio.sleep(0.1)  # 模拟打字机延迟
    
    async def _call_ai(self, content: str, from_userid: str, chat_type: str) -> str:
        """
        调用 AI 处理消息
        
        这里可以集成：
        - OpenClaw 本地 API
        - OpenAI / Claude / Qwen 等 LLM
        - 自定义业务逻辑
        """
        # 示例：简单的规则回复
        content_lower = content.lower()
        
        if '你好' in content or 'hello' in content:
            return "您好！我是您的智能助手，有什么可以帮您的吗？😊"
        
        elif '时间' in content or '几点' in content:
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return f"当前时间是：{now}"
        
        elif '帮助' in content or 'help' in content:
            return """**我能帮您做什么？**

- 📝 回答各种问题
- 📊 查询信息和数据
- 🔧 执行自动化任务
- 💬 陪您聊天解闷

直接告诉我您的需求吧！"""
        
        else:
            return f"""收到您的消息了：

> {content}

这是一个示例回复。请集成真实的 LLM API（如 OpenClaw、Qwen、Claude 等）来获取智能回复。

**配置方法：**
编辑 `openclaw_integration.py` 中的 `_call_ai` 方法，接入您的 AI 服务。"""
    
    def _split_response(self, text: str, chunk_size: int = 50) -> list:
        """将回复分割成小块，用于流式发送"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks if chunks else [text]
    
    async def _handle_enter_chat(self, req_id: str, from_userid: str):
        """处理用户进入会话事件"""
        welcome_msg = f"""👋 您好！我是智能助手～

我可以帮您：
- 回答问题、查询信息
- 处理文档、分析数据
- 执行自动化任务

有什么需要尽管告诉我！"""
        
        await self.bot.respond_welcome_msg(req_id, {
            "msgtype": "text",
            "text": {
                "content": welcome_msg
            }
        })
    
    async def run(self):
        """启动集成服务"""
        print("=" * 50)
        print("OpenClaw + 企业微信机器人集成服务")
        print("=" * 50)
        print("正在启动...")
        await self.bot.run()


async def main():
    """主函数"""
    # 检查配置文件
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        print("请复制 config.example.json 为 config.json 并填写 BotID 和 Secret")
        return
    
    # 创建并运行集成服务
    integration = OpenClawWeComIntegration(config_path)
    await integration.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务已停止")
