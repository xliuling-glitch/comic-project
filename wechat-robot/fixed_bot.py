#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 - 最终修复版
根据官方文档：https://developer.work.weixin.qq.com/document/path/101463
"""
import asyncio, json, os, sys, logging, aiohttp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot
import dashscope
from dashscope import Generation

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FixedBot')

dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')
bot = WeComBot('config.json')

@bot.on_message
async def on_msg(data):
    logger.info("="*80)
    body = data.get('body', {})
    req_id = data.get('headers', {}).get('req_id')
    msgtype = body.get('msgtype')
    content = body.get('text', {}).get('content', '') if msgtype == 'text' else ''
    uid = body.get('from', {}).get('userid', '?')
    response_url = body.get('response_url', '')
    
    logger.info(f"收到消息 from {uid}: {content}")
    logger.info(f"req_id: {req_id}")
    logger.info(f"response_url: {response_url[:80]}...")
    
    try:
        # 调用 AI
        r = Generation.call(model='qwen-plus', messages=[{'role':'user','content':content}])
        logger.info(f"API status: {r.status_code}")
        
        if r.status_code == 200:
            reply = r.output.get('text', 'hi')
            logger.info(f"AI 回复：{reply[:100]}...")
            
            # 通过 HTTP 发送回复（使用 response_url）
            if response_url:
                # 正确的格式：msgtype + 对应类型的内容
                reply_data = {
                    "msgtype": "text",
                    "text": {
                        "content": reply
                    }
                }
                
                logger.info(f"发送回复：{json.dumps(reply_data, ensure_ascii=False)}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(response_url, json=reply_data) as resp:
                        result = await resp.json()
                        logger.info(f"HTTP 响应：{result}")
                        
                        if result.get('errcode') == 0:
                            logger.info("✅ 回复成功！")
                        else:
                            logger.error(f"❌ 回复失败：{result.get('errcode')} - {result.get('errmsg')}")
            else:
                logger.error("没有 response_url，无法回复")
        else:
            logger.error(f"API 错误：{r.code} - {r.message}")
    except Exception as e:
        logger.error(f"异常：{e}", exc_info=True)
    
    logger.info("="*80)

@bot.on_event
async def on_event(data):
    et = data.get('body',{}).get('event',{}).get('eventtype','?')
    logger.info(f"事件：{et}")

logger.info("="*80)
logger.info("企业微信机器人 - 最终修复版")
logger.info("="*80)
asyncio.run(bot.run())
