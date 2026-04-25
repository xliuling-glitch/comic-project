#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""企业微信机器人 - 完整诊断版"""
import asyncio, json, os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot
import dashscope
from dashscope import Generation

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FullBot')

dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')
bot = WeComBot('config.json')

@bot.on_message
async def on_msg(data):
    logger.info("="*80)
    logger.info("收到消息回调")
    logger.info("完整数据:\n%s", json.dumps(data, indent=2, ensure_ascii=False))
    
    body = data.get('body', {})
    headers = data.get('headers', {})
    req_id = headers.get('req_id')
    msgtype = body.get('msgtype')
    content = body.get('text', {}).get('content', '') if msgtype == 'text' else ''
    uid = body.get('from', {}).get('userid', '?')
    
    logger.info(f"发送者：{uid}")
    logger.info(f"消息类型：{msgtype}")
    logger.info(f"消息内容：{content}")
    logger.info(f"req_id: {req_id}")
    
    try:
        logger.info("调用 Qwen API...")
        r = Generation.call(model='qwen-plus', messages=[{'role':'user','content':content}])
        logger.info(f"API status: {r.status_code}")
        
        if r.status_code == 200:
            reply = r.output.get('text', 'hi')
            logger.info(f"AI 回复：{reply[:200]}...")
            
            # 构建回复消息 - 尝试不同格式
            # 格式 1: 标准格式
            reply_msg = {
                "cmd": "aibot_respond_msg",
                "headers": {"req_id": req_id},
                "body": {
                    "msgtype": "text",
                    "text": {"content": reply}
                }
            }
            
            logger.info("发送回复消息:")
            logger.info(json.dumps(reply_msg, indent=2, ensure_ascii=False))
            
            # 直接通过 WebSocket 发送
            if bot.ws and bot.connected:
                await bot.ws.send(json.dumps(reply_msg))
                logger.info("消息已发送到 WebSocket")
                
                # 等待响应
                try:
                    resp = await asyncio.wait_for(bot.ws.recv(), timeout=10)
                    resp_data = json.loads(resp)
                    logger.info(f"收到响应：{json.dumps(resp_data, indent=2, ensure_ascii=False)}")
                    
                    if resp_data.get('errcode') == 0:
                        logger.info("✅ 回复成功！")
                    else:
                        logger.error(f"❌ 回复失败：{resp_data.get('errcode')} - {resp_data.get('errmsg')}")
                except asyncio.TimeoutError:
                    logger.error("等待响应超时")
            else:
                logger.error("WebSocket 未连接")
        else:
            logger.error(f"API 错误：{r.code} - {r.message}")
    except Exception as e:
        logger.error(f"异常：{e}", exc_info=True)
    
    logger.info("="*80)

@bot.on_event
async def on_event(data):
    logger.info("收到事件：%s", json.dumps(data, indent=2, ensure_ascii=False))
    et = data.get('body',{}).get('event',{}).get('eventtype','?')
    if et == 'enter_chat':
        logger.info("用户进入会话")

logger.info("="*80)
logger.info("企业微信机器人 - 完整诊断版启动")
logger.info("="*80)
asyncio.run(bot.run())
