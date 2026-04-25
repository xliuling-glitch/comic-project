#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咸鱼全自动服务
- 自动上架商品（从 ZIP 解析）
- 自动监控聊天消息
- 自动回复常见问题
- 买家下单自动发网盘链接
"""

import argparse
import json
import os
import logging
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from product_parser import ProductParser
from xianyu_publisher import XianyuPublisher
from xianyu_monitor import XianyuChatMonitor
from auto_responder import AutoResponder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AutoService')

def load_config(config_path='config.json'):
    """加载配置"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    parser = argparse.ArgumentParser(description='咸鱼全自动商品发布+客服')
    parser.add_argument('zip_file', nargs='?', help='ZIP 压缩文件路径（包含商品信息）')
    parser.add_argument('--share-url', help='网盘分享链接')
    parser.add_argument('--share-code', help='网盘提取码')
    parser.add_argument('--monitor', '-m', action='store_true', help='发布后启动监控自动回复和自动发货')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    if args.monitor and not args.zip_file:
        # 只启动监控
        logger.info("只启动聊天监控服务...")
        
        # 启动浏览器
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        if config.get('xianyu', {}).get('chrome_user_data_dir'):
            chrome_options.add_argument(f"--user-data-dir={config['xianyu']['chrome_user_data_dir']}")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.2.taobao.com/")
        
        # 初始化自动回复
        auto_responder = AutoResponder(config.get('auto_reply', {}))
        
        # 加载已注册商品
        products_file = 'registered_products.json'
        if os.path.exists(products_file):
            with open(products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
                for p in products:
                    auto_responder.add_product(
                        p.get('product_name'),
                        p.get('share_url'),
                        p.get('share_code'),
                        p.get('price')
                    )
            logger.info(f"已加载 {len(products)} 个注册商品")
        
        # 开始监控
        monitor = XianyuChatMonitor(driver, auto_responder)
        monitor.go_to_chat_list()
        monitor.start_monitoring()
        return 0
    
    if not args.zip_file:
        print("""
咸鱼全自动商品发布+客服系统
============================

使用方法：

1. 发布商品并启动监控：
   python auto_service.py 商品.zip --share-url "https://pan.quark.cn/s/xxx" --share-code abcd --monitor

2. 仅发布商品：
   python auto_service.py 商品.zip --share-url "https://pan.quark.cn/s/xxx" --share-code abcd

3. 只启动监控（已发布完商品，只做自动回复）：
   python auto_service.py --monitor

功能：
- ✅ 自动从 ZIP 解析商品信息（标题、价格、图片）
- ✅ 自动上传图片、填写信息到咸鱼
- ✅ 自动注册商品网盘链接
- ✅ 买家下单付款自动发链接
- ✅ 自动回复常见售后问题
- ✅ 持续监控聊天消息

商品 ZIP 格式：
  商品.zip
  ├── 主图.jpg
  ├── 图片1.jpg
  ├── ...
  └── 描述.txt （包含标题、价格、介绍）
""")
        return 0
    
    # 解析 ZIP 文件
    download_dir = config.get('download_dir', 'downloads')
    product_parser = ProductParser(download_dir=download_dir)
    
    # AI 生成器（优化标题/描述/主图）
    from ai_generator import AIGenerator
    ai_generator = AIGenerator(config.get('ai'))
    
    logger.info(f"正在解析商品：{args.zip_file}")
    product_info = product_parser.parse_zip_file(args.zip_file)
    
    if not product_info:
        logger.error("❌ 解析商品失败")
        return 1
    
    # 添加网盘信息
    if args.share_url:
        product_info['share_url'] = args.share_url
        product_info['share_code'] = args.share_code or ''
    else:
        # 尝试从描述中提取链接
        # 如果描述中已经有链接，可以提取出来
        # 这里简化处理，要求必须传参数
        logger.warning("⚠️  没有提供 --share-url 和 --share-code，下单后无法自动发货")
    
    # AI 优化（如果启用）
    if ai_generator.enabled:
        logger.info(f"🤖 AI 优化商品信息：{product_info['title']}")
        product_info = ai_generator.optimize_product(product_info)
    
    # 输出解析结果
    print("\n" + "="*60)
    print("✅ 解析成功！")
    print(f"📝 标题：{product_info['title']}")
    print(f"💰 价格：{product_info['price'] or '未找到'}")
    print(f"🖼️ 主图：{os.path.basename(product_info['main_image']) if product_info['main_image'] else '无'}")
    print(f"📄 图片数量：{len(product_info['images'])}")
    if args.share_url:
        print(f"🔗 网盘：{args.share_url} 提取码：{args.share_code}")
    print("="*60 + "\n")
    
    # 启动发布
    logger.info("开始发布商品到咸鱼...")
    
    # 启动浏览器
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    if config.get('xianyu', {}).get('chrome_user_data_dir'):
        chrome_options.add_argument(f"--user-data-dir={config['xianyu']['chrome_user_data_dir']}")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # 初始化发布器
    publisher = XianyuPublisher(config.get('xianyu', {}))
    publisher.driver = driver
    
    # 如果要监控，初始化监控器
    monitor = None
    if args.monitor:
        auto_responder = AutoResponder(config.get('auto_reply', {}))
        monitor = XianyuChatMonitor(driver, auto_responder)
        publisher.monitor = monitor  # 让发布器能注册商品
        
        # 加载已保存的商品
        products_file = 'registered_products.json'
        if os.path.exists(products_file):
            with open(products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
                for p in products:
                    auto_responder.add_product(
                        p.get('product_name'),
                        p.get('share_url'),
                        p.get('share_code'),
                        p.get('price')
                    )
            logger.info(f"已加载 {len(products)} 个已注册商品")
    
    # 发布商品
    success = publisher.publish(product_info)
    
    if not success:
        logger.error("❌ 发布失败")
        return 1
    
    # 保存注册商品
    if args.share_url and args.share_code:
        products_file = 'registered_products.json'
        
        # 读取已有商品
        products = []
        if os.path.exists(products_file):
            with open(products_file, 'r', encoding='utf-8') as f:
                products = json.load(f)
        
        # 添加新商品
        products.append({
            'product_name': product_info['title'],
            'share_url': args.share_url,
            'share_code': args.share_code,
            'price': product_info.get('price', ''),
            'created_at': product_info.get('created_at', '')
        })
        
        # 保存
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 商品已注册到自动发货列表，共 {len(products)} 个商品")
    
    # 如果需要监控，开始监控
    if args.monitor and monitor:
        logger.info("🚀 开始聊天监控，处理自动回复和自动发货...")
        monitor.go_to_chat_list()
        monitor.start_monitoring()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
