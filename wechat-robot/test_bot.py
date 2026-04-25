#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 - 简化测试版（用于调试）
"""

import asyncio
import json
import uuid
import os
import sys
import logging
import dashscope
from dashscope import Generation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot

# 配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TestBot')
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')

bot = WeComBot('config.json')

@bot.on_message
async def on_message(data):
    body = data.get('body', {})
    req_id = data.get('headers', {}).get('req_id')
    content = body.get('text', {}).get('content', '')
    from_userid = body.get('from', {}).get('userid', 'unknown')
    
    logger.info(f"收到消息 from {from_userid}: {content}")
    
    try:
        # 直接调用 API（不流式）
        logger.info("正在调用 Qwen API...")
        response = Generation.call(
            model='qwen-plus',
            messages=[{'role': 'user', 'content': content}]
        )
        
        if response.status_code == 200:
            reply = response.output.get('text', '无回复')
            logger.info(f"API 回复：{reply[:50]}...")
            
            # 发送回复
            result = await bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": reply}
            })
            logger.info(f"发送结果：{result}")
        else:
            logger.error(f"API 错误：{response.code} - {response.message}")
            await bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": f"API 错误：{response.code}"}
            })
    except Exception as e:
        logger.error(f"处理异常：{e}", exc_info=True)
        await bot.respond_msg(req_id, {
            "msgtype": "text",
            "text": {"content": f"错误：{str(e)}"}
        })

@bot.on_event
async def on_event(data):
    event_type = data.get('body', {}).get('event', {}).get('eventtype')
    req_id = data.get('headers', {}).get('req_id')
    logger.info(f"收到事件：{event_type}")
    
    if event_type == 'enter_chat':
        await bot.respond_welcome_msg(req_id, {
            "msgtype": "text",
            "text": {"content": "你好！我是测试机器人 🤖"}
        })

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("企业微信机器人 - 简化测试版")
    logger.info("=" * 50)
    asyncio.run(bot.run())
