#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 - 诊断版（带详细日志）
"""

import asyncio
import json
import os
import sys
import logging
import dashscope
from dashscope import Generation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_debug.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('DebugBot')

# 配置
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')

# 读取配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

logger.info("=" * 60)
logger.info("企业微信机器人 - 诊断版")
logger.info("=" * 60)
logger.info(f"BotID: {config.get('bot_id', 'N/A')[:10]}...")
logger.info(f"Secret: {config.get('secret', 'N/A')[:10]}...")
logger.info(f"WebSocket: {config.get('websocket_url')}")
logger.info("=" * 60)

bot = WeComBot('config.json')

@bot.on_message
async def on_message(data):
    logger.info("📩 " + "=" * 50)
    logger.info("收到消息回调！")
    logger.info(f"完整数据：{json.dumps(data, indent=2, ensure_ascii=False)}")
    
    body = data.get('body', {})
    req_id = data.get('headers', {}).get('req_id')
    msgtype = body.get('msgtype')
    content = body.get('text', {}).get('content', '') if msgtype == 'text' else ''
    from_userid = body.get('from', {}).get('userid', 'unknown')
    
    logger.info(f"发送者：{from_userid}")
    logger.info(f"消息类型：{msgtype}")
    logger.info(f"消息内容：{content}")
    logger.info(f"req_id: {req_id}")
    
    try:
        # 调用 AI
        logger.info("正在调用 Qwen API...")
        response = Generation.call(
            model='qwen-plus',
            messages=[{'role': 'user', 'content': content}]
        )
        
        logger.info(f"API 状态码：{response.status_code}")
        
        if response.status_code == 200:
            reply = response.output.get('text', '无回复')
            logger.info(f"AI 回复内容：{reply[:200]}...")
            
            # 发送回复
            logger.info(f"正在发送回复到 req_id: {req_id}")
            result = await bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": reply}
            })
            logger.info(f"✅ 发送结果：{result}")
        else:
            logger.error(f"❌ API 错误：{response.code} - {response.message}")
            await bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": f"API 错误：{response.code}"}
            })
    except Exception as e:
        logger.error(f"❌ 处理异常：{e}", exc_info=True)
        await bot.respond_msg(req_id, {
            "msgtype": "text",
            "text": {"content": f"错误：{str(e)}"}
        })
    
    logger.info("📩 " + "=" * 50)

@bot.on_event
async def on_event(data):
    logger.info("🎯 " + "=" * 50)
    logger.info("收到事件回调！")
    logger.info(f"完整数据：{json.dumps(data, indent=2, ensure_ascii=False)}")
    
    event_type = data.get('body', {}).get('event', {}).get('eventtype')
    req_id = data.get('headers', {}).get('req_id')
    
    logger.info(f"事件类型：{event_type}")
    
    if event_type == 'enter_chat':
        logger.info("用户进入会话，发送欢迎语...")
        await bot.respond_welcome_msg(req_id, {
            "msgtype": "text",
            "text": {"content": "👋 你好！我是诊断版机器人，一切正常！"}
        })
    
    logger.info("🎯 " + "=" * 50)

if __name__ == '__main__':
    logger.info("🚀 正在启动机器人...")
    asyncio.run(bot.run())
