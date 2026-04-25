#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单稳定的机器人版本 - 带日志"""
import asyncio, json, os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot
import dashscope
from dashscope import Generation

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('SimpleBot')

dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')
bot = WeComBot('config.json')

@bot.on_message
async def on_msg(data):
    body = data.get('body', {})
    req_id = data.get('headers', {}).get('req_id')
    content = body.get('text', {}).get('content', '')
    uid = body.get('from', {}).get('userid', '?')
    logger.info(f"[MSG] from {uid}: {content}")
    
    try:
        logger.info("Calling Qwen API...")
        r = Generation.call(model='qwen-plus', messages=[{'role':'user','content':content}])
        logger.info(f"API status: {r.status_code}")
        
        if r.status_code == 200:
            reply = r.output.get('text', 'hi')
            logger.info(f"[REPLY] {reply[:100]}...")
            await bot.respond_msg(req_id, "text", {"content": reply})
            logger.info("Reply sent OK")
        else:
            logger.error(f"[ERR] API {r.code} - {r.message}")
            await bot.respond_msg(req_id, "text", {"content": f"Error: {r.code}"})
    except Exception as e:
        logger.error(f"[ERR] {e}", exc_info=True)
        await bot.respond_msg(req_id, "text", {"content": f"Error: {str(e)}"})

@bot.on_event
async def on_event(data):
    et = data.get('body',{}).get('event',{}).get('eventtype','?')
    req_id = data.get('headers',{}).get('req_id')
    logger.info(f"[EVENT] {et}")
    if et == 'enter_chat':
        await bot.respond_welcome_msg(req_id, {"msgtype":"text","text":{"content":"你好！机器人正常运作"}})
        logger.info("Welcome sent")

logger.info("="*50)
logger.info("企业微信机器人 - 启动中")
logger.info("="*50)
asyncio.run(bot.run())
