#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 + OpenClaw 集成
通过 OpenClaw CLI 调用主会话处理消息
"""

import asyncio
import json
import uuid
import os
import sys
import subprocess
import logging

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wecom_bot import WeComBot

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('OpenClawWeCom')

# OpenClaw 配置
OPENCLAW_MODEL = "bailian/qwen3.5-plus"  # 使用 OpenClaw 配置的模型
OPENCLAW_CLI = r"C:\Users\Administrator\AppData\Roaming\npm\node_modules\openclaw\dist\index.js"  # OpenClaw CLI 路径
NODE_EXE = "node"  # Node.js 可执行文件


class OpenClawWeComIntegration:
    """企业微信机器人 + OpenClaw 集成"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.bot = WeComBot(config_path)
        self._conversation_history = {}  # 简单的多轮对话缓存
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
            
            logger.info(f"[消息] 来自 {from_userid} ({chat_type}): {msgtype}")
            
            if msgtype == 'text':
                content = body.get('text', {}).get('content', '')
                await self._process_with_openclaw(req_id, content, from_userid, chat_type)
                
        @self.bot.on_event
        async def handle_event(data):
            """处理事件"""
            body = data.get('body', {})
            event_type = body.get('event', {}).get('eventtype')
            req_id = data.get('headers', {}).get('req_id')
            from_userid = body.get('from', {}).get('userid', 'unknown')
            
            logger.info(f"[事件] {event_type} - 来自 {from_userid}")
            
            if event_type == 'enter_chat':
                await self._handle_enter_chat(req_id, from_userid)
    
    async def _process_with_openclaw(self, req_id: str, content: str, 
                                      from_userid: str, chat_type: str):
        """
        使用 OpenClaw 处理消息
        
        通过 openclaw agent 命令调用
        """
        stream_id = str(uuid.uuid4())
        
        try:
            # 发送"思考中"提示
            await self.bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": False,
                    "content": "🤔 OpenClaw 正在思考..."
                }
            })
            
            # 构建用户上下文
            user_context = f"用户 ID: {from_userid}\n会话类型：{chat_type}\n\n"
            full_prompt = user_context + content
            
            # 调用 OpenClaw CLI (通过 node 直接运行)
            # 使用 --model 指定模型，使用 --message 发送消息
            cmd = [
                NODE_EXE, OPENCLAW_CLI, 'agent',
                '--model', OPENCLAW_MODEL,
                '--message', full_prompt
            ]
            
            logger.info(f"执行 OpenClaw 命令：{' '.join(cmd)}")
            
            # 执行命令并获取输出
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=r'C:\Users\Administrator\.openclaw\workspace'
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60  # 60 秒超时
            )
            
            if process.returncode == 0:
                response = stdout.decode('utf-8', errors='ignore').strip()
                logger.info(f"OpenClaw 响应：{response[:200]}...")
                
                # 流式发送响应（分块）
                if response:
                    chunks = self._split_text(response, chunk_size=100)
                    for i, chunk in enumerate(chunks):
                        is_last = (i == len(chunks) - 1)
                        await self.bot.respond_msg(req_id, {
                            "msgtype": "stream",
                            "stream": {
                                "id": stream_id,
                                "finish": is_last,
                                "content": chunk + ("\n" if not is_last else "")
                            }
                        })
                        if not is_last:
                            await asyncio.sleep(0.05)  # 打字机效果
                else:
                    await self.bot.respond_msg(req_id, {
                        "msgtype": "stream",
                        "stream": {
                            "id": stream_id,
                            "finish": True,
                            "content": "OpenClaw 没有返回内容。"
                        }
                    })
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"OpenClaw 错误：{error_msg}")
                await self.bot.respond_msg(req_id, {
                    "msgtype": "stream",
                    "stream": {
                        "id": stream_id,
                        "finish": True,
                        "content": f"抱歉，OpenClaw 调用失败：{error_msg[:200]}"
                    }
                })
                
        except asyncio.TimeoutError:
            logger.error("OpenClaw 调用超时")
            await self.bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": True,
                    "content": "抱歉，OpenClaw 响应超时（>60 秒）。请稍后再试。"
                }
            })
        except Exception as e:
            logger.error(f"处理异常：{e}")
            await self.bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": True,
                    "content": f"抱歉，处理消息时出错：{str(e)}"
                }
            })
    
    def _split_text(self, text: str, chunk_size: int = 100) -> list:
        """分割文本用于流式发送"""
        # 按段落分割，保持语义完整
        paragraphs = text.split('\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    async def _handle_enter_chat(self, req_id: str, from_userid: str):
        """处理用户进入会话事件"""
        welcome_msg = f"""👋 您好！我是 **OpenClaw 智能助手**～

我可以帮您：
- 📝 回答各种问题
- 🔧 执行自动化任务
- 📊 查询信息和数据
- 💬 陪您聊天解闷
- 🧠 使用记忆和工具

有什么需要尽管告诉我！"""
        
        await self.bot.respond_welcome_msg(req_id, {
            "msgtype": "text",
            "text": {
                "content": welcome_msg
            }
        })
    
    async def run(self):
        """启动集成服务"""
        print("=" * 60)
        print("OpenClaw + 企业微信机器人 集成服务")
        print("=" * 60)
        print(f"模型：{OPENCLAW_MODEL}")
        print("正在启动...")
        await self.bot.run()


async def main():
    """主函数"""
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print(f"错误：配置文件 {config_path} 不存在")
        return
    
    integration = OpenClawWeComIntegration(config_path)
    await integration.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务已停止")
