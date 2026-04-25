#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 - 商品自动发布版
功能：
1. 接收夸克/百度网盘链接，引导用户发送文件
2. 接收 ZIP 文件，自动解析商品信息（主图+介绍）
3. 自动发布商品（先发送主图，再发送 markdown 介绍）
"""

import asyncio
import json
import logging
from wecom_bot import WeComBot
from product_publisher import AutoProductPublisher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProductPublisherBot')

async def main():
    # 读取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 创建机器人
    bot = WeComBot('config.json')
    
    # 创建商品自动发布器
    publisher = AutoProductPublisher(bot, 'product_publisher_config.json')
    
    # 注册消息回调
    @bot.on_message
    async def handle_message(data):
        body = data.get('body', {})
        msgtype = body.get('msgtype')
        logger.info(f"收到消息，类型：{msgtype}")
        
        if msgtype == 'text':
            # 处理文本消息，尝试提取分享链接
            handled = await publisher.process_message(data)
            if not handled:
                # 不是链接，可以回复默认提示
                content = body.get('text', {}).get('content', '')
                req_id = data.get('headers', {}).get('req_id')
                
                # 如果用户说"发布商品"或者单个商品，提示用法
                if '发布' in content or '商品' in content:
                    await bot.respond_msg(req_id, {
                        "msgtype": "text",
                        "text": {
                            "content": (
                                "📦 **商品自动发布使用方法**\n\n"
                                "1. 直接发送网盘链接（夸克/百度均可），加上提取码\n"
                                "2. 根据提示下载后把 ZIP 文件发过来\n"
                                "3. 我会：\n"
                                "   - 自动解压\n"
                                "   - 提取主图（找带「主图」「封面」的图片）\n"
                                "   - 读取商品介绍（找 txt 或 md 文件）\n"
                                "   - 自动发布：先发图，再发文字介绍\n\n"
                                "单个商品直接发就可以自动发布了！"
                            )
                        }
                    })
                else:
                    # 默认回复
                    await bot.respond_msg(req_id, {
                        "msgtype": "text",
                        "text": {
                            "content": "👋 我是商品自动发布助手。发送网盘链接+提取码，我帮你自动解析发布商品！"
                        }
                    })
                    
        elif msgtype == 'file':
            # 处理文件，尝试解析 ZIP 发布商品
            await publisher.process_file(data)
            
        else:
            logger.info(f"未处理的消息类型：{msgtype}")
    
    # 注册事件回调
    @bot.on_event
    async def handle_event(data):
        body = data.get('body', {})
        event_type = body.get('event', {}).get('eventtype')
        req_id = data.get('headers', {}).get('req_id')
        logger.info(f"收到事件：{event_type}")
        
        if event_type == 'enter_chat':
            await bot.respond_welcome_msg(req_id, {
                "msgtype": "markdown",
                "markdown": {
                    "content": (
                        "# 👋 您好！我是商品自动发布助手\n\n"
                        "您可以发送：\n"
                        "- **夸克/百度网盘链接 + 提取码**\n"
                        "- **ZIP 压缩文件**\n\n"
                        "我会自动解析商品信息并发布！\n\n"
                        "支持：自动识别主图、自动读取商品介绍、图文分开发布"
                    )
                }
            })
    
    # 启动机器人
    logger.info("🚀 商品自动发布机器人启动中...")
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
