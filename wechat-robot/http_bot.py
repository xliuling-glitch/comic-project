#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""企业微信机器人 - HTTP 回复版本"""
import asyncio, json, os, sys, logging, aiohttp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot
import dashscope
from dashscope import Generation

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('HTTPBot')

dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')
bot = WeComBot('config.json')

@bot.on_message
async def on_msg(data):
    body = data.get('body', {})
    req_id = data.get('headers', {}).get('req_id')
    msgtype = body.get('msgtype')
    content = body.get('text', {}).get('content', '') if msgtype == 'text' else ''
    uid = body.get('from', {}).get('userid', '?')
    response_url = body.get('response_url', '')
    
    logger.info(f"[MSG] from {uid}: {content}")
    logger.info(f"response_url: {response_url}")
    
    try:
        r = Generation.call(model='qwen-plus', messages=[{'role':'user','content':content}])
        
        if r.status_code == 200:
            reply = r.output.get('text', 'hi')
            logger.info(f"[REPLY] {reply[:100]}...")
            
            # 通过 HTTP POST 发送到 response_url
            if response_url:
                # 尝试格式 2: 不加 msgtype
                reply_data = {
                    "text": {"content": reply}
                }
                logger.info(f"发送数据 (格式 2): {json.dumps(reply_data, ensure_ascii=False)}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(response_url, json=reply_data) as resp:
                        result = await resp.json()
                        logger.info(f"HTTP 响应：{result}")
                        
                        if result.get('errcode') == 0:
                            logger.info("✅ HTTP 回复成功！")
                        else:
                            logger.error(f"❌ HTTP 回复失败：{result}")
            else:
                logger.error("没有 response_url")
        else:
            logger.error(f"API 错误：{r.code}")
    except Exception as e:
        logger.error(f"异常：{e}", exc_info=True)

@bot.on_event
async def on_event(data):
    et = data.get('body',{}).get('event',{}).get('eventtype','?')
    logger.info(f"[EVENT] {et}")

logger.info("="*60)
logger.info("企业微信机器人 - HTTP 回复版本")
logger.info("="*60)
asyncio.run(bot.run())
