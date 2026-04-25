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
import logging
import dashscope
from dashscope import Generation

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('OpenClawWeCom')

# 添加父目录到路径，以便导入 wecom_bot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wecom_bot import WeComBot

# 配置通义千问
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')
QWEN_MODEL = 'qwen-plus'  # 可选：qwen-turbo, qwen-plus, qwen-max


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
        处理文本消息 - 使用 Qwen 流式输出
        """
        stream_id = str(uuid.uuid4())
        
        try:
            # 使用 Qwen 流式调用
            messages = [
                {'role': 'system', 'content': '你是一个友好的智能助手，回答简洁、有用、有趣。支持 Markdown 格式。'},
                {'role': 'user', 'content': content}
            ]
            
            # 第一次回复：思考中
            await self.bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": False,
                    "content": "🤔 正在思考..."
                }
            })
            
            # 流式调用 Qwen（同步方式，在 executor 中运行）
            loop = asyncio.get_event_loop()
            full_response = await loop.run_in_executor(
                None,
                lambda: self._call_qwen_stream(messages)
            )
            
            if full_response:
                # 分块发送响应
                chunks = self._split_response(full_response, 50)
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
                        await asyncio.sleep(0.05)
            else:
                await self.bot.respond_msg(req_id, {
                    "msgtype": "stream",
                    "stream": {
                        "id": stream_id,
                        "finish": True,
                        "content": "抱歉，我没有理解您的问题。"
                    }
                })
                
        except Exception as e:
            logger.error(f"处理异常：{e}")
            # 降级为非流式
            response = await self._call_ai(content, from_userid, chat_type)
            await self.bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": response}
            })
    
    def _call_qwen_stream(self, messages: list) -> str:
        """同步调用 Qwen（用于在 executor 中运行）"""
        try:
            response = Generation.call(
                model=QWEN_MODEL,
                messages=messages,
                result_format='message'
            )
            
            if response.status_code == 200 and response.output:
                # output 是 dict 类型，直接获取 text 字段
                content = response.output.get('text', '')
                return content if content else "抱歉，我没有理解您的问题。"
            else:
                err_code = getattr(response, 'code', 'unknown')
                err_msg = getattr(response, 'message', 'unknown')
                logger.error(f"Qwen API 错误：{err_code} - {err_msg}")
                return f"抱歉，AI 服务暂时不可用。"
        except Exception as e:
            logger.error(f"Qwen 调用异常：{e}")
            return f"抱歉，处理您的消息时遇到了一些问题：{str(e)}"
    
    async def _call_ai(self, content: str, from_userid: str, chat_type: str) -> str:
        """
        调用通义千问 (Qwen) 处理消息（备用非流式）
        
        使用阿里云 DashScope API
        """
        try:
            messages = [
                {'role': 'system', 'content': '你是一个友好的智能助手，回答简洁、有用、有趣。支持 Markdown 格式。'},
                {'role': 'user', 'content': content}
            ]
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Generation.call(model=QWEN_MODEL, messages=messages, result_format='message')
            )
            
            if response and response.status_code == 200 and response.output:
                return response.output.get('text', '抱歉，我没有理解您的问题。')
            else:
                err_code = getattr(response, 'code', 'unknown')
                err_msg = getattr(response, 'message', 'unknown')
                logger.error(f"Qwen API 错误：{err_code} - {err_msg}")
                return f"抱歉，AI 服务暂时不可用。"
                
        except Exception as e:
            logger.error(f"AI 调用异常：{e}")
            return f"抱歉，处理您的消息时遇到了一些问题：{str(e)}"
    
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
