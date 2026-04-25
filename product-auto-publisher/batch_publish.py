#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量上架商品
从你的货源文档（CSV/JSON/Markdown）批量读取商品，逐个自动上架
支持你的："我会有一个网盘资料的文档记录上架和货源地址"
"""

import argparse
import json
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from product_parser import ProductParser
from xianyu_publisher import XianyuPublisher
from auto_responder import AutoResponder
from xianyu_monitor import XianyuChatMonitor
from batch_publisher import BatchProductReader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BatchPublish')

def load_config(config_path='config.json'):
    """加载配置"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    parser = argparse.ArgumentParser(description='批量上架商品到咸鱼')
    parser.add_argument('source_file', help='货源文档路径 (.csv/.json/.md)')
    parser.add_argument('--monitor', '-m', action='store_true', help='批量上架完成后启动监控')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser.add_argument('--delay', '-d', type=int, default=10, help='上架完一个后等待多少秒再上架下一个')
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 读取批量商品列表
    reader = BatchProductReader()
    products = reader.auto_read(args.source_file)
    
    if not products:
        logger.error("❌ 没有读到任何商品，请检查文件格式")
        print("\n支持的格式：")
        print("1. CSV：表头包含 title,price,zip_path,share_url,share_code")
        print("2. Markdown：每个商品用 ## 标题分隔，带- 价格: xxx 链接: xxx 提取码: xxx")
        print("3. JSON：是一个商品数组")
        return 1
    
    logger.info(f"📋 读到 {len(products)} 个商品，准备批量上架")
    print(f"\n📋 读到 {len(products)} 个商品：")
    for i, p in enumerate(products, 1):
        print(f"  {i}. {p['title']} - ¥{p.get('price', '暂无')}")
    print()
    
    # 启动浏览器
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    if config.get('xianyu', {}).get('chrome_user_data_dir'):
        chrome_options.add_argument(f"--user-data-dir={config['xianyu']['chrome_user_data_dir']}")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.2.taobao.com/")
    logger.info("浏览器已启动，请确保已登录咸鱼账号")
    
    # 检查登录
    input("请确认浏览器已经打开并登录成功，按回车继续...")
    
    # 初始化发布器
    publisher = XianyuPublisher(config.get('xianyu', {}))
    publisher.driver = driver
    
    # 初始化自动回复器（如果需要监控）
    auto_responder = None
    monitor = None
    if args.monitor:
        auto_responder = AutoResponder(config.get('auto_reply', {}))
        monitor = XianyuChatMonitor(driver, auto_responder)
        publisher.monitor = monitor
        
        # 加载已有商品
        products_file = 'registered_products.json'
        if os.path.exists(products_file):
            with open(products_file, 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
                for p in existing_products:
                    auto_responder.add_product(
                        p.get('product_name'),
                        p.get('share_url'),
                        p.get('share_code'),
                        p.get('price')
                    )
            logger.info(f"已加载 {len(existing_products)} 个已注册商品")
    
    # 解析器
    download_dir = config.get('download_dir', 'downloads')
    product_parser = ProductParser(download_dir=download_dir)
    
    # AI 生成器（优化标题/描述/主图）
    from ai_generator import AIGenerator
    ai_generator = AIGenerator(config.get('ai'))
    
    # 保存所有上架成功的商品
    success_count = 0
    fail_count = 0
    registered_products_file = 'registered_products.json'
    
    # 读取已有商品
    all_registered = []
    if os.path.exists(registered_products_file):
        with open(registered_products_file, 'r', encoding='utf-8') as f:
            all_registered = json.load(f)
    
    # 逐个上架
    for idx, product in enumerate(products, 1):
        print(f"\n{'='*60}")
        logger.info(f"[{idx}/{len(products)}] 正在上架：{product['title']}")
        print(f"[{idx}/{len(products)}] 商品：{product['title']}")
        
        try:
            # 获取 ZIP 路径
            zip_path = product.get('zip_path')
            if not zip_path:
                logger.error(f"❌ 没有 ZIP 路径，跳过：{product['title']}")
                fail_count += 1
                continue
                
            # 如果 ZIP 路径是相对路径，相对于源文件所在目录
            if not os.path.isabs(zip_path):
                base_dir = os.path.dirname(os.path.abspath(args.source_file))
                zip_path = os.path.join(base_dir, zip_path)
            
            if not os.path.exists(zip_path):
                logger.error(f"❌ ZIP 文件不存在：{zip_path}，跳过")
                fail_count += 1
                continue
                
            # 解析商品
            parsed_info = product_parser.parse_zip_file(zip_path)
            if not parsed_info:
                logger.error(f"❌ 解析 ZIP 失败，跳过：{zip_path}")
                fail_count += 1
                continue
                
            # 合并从文档读到的信息
            if product.get('price') and not parsed_info.get('price'):
                parsed_info['price'] = product['price']
            if product.get('share_url'):
                parsed_info['share_url'] = product['share_url']
            if product.get('share_code'):
                parsed_info['share_code'] = product['share_code']
            if product.get('description') and not parsed_info.get('description'):
                parsed_info['description'] = product['description']
            if product.get('category') and not parsed_info.get('category'):
                parsed_info['category'] = product['category']
            
            # AI 优化（如果启用）
            if ai_generator.enabled:
                logger.info(f"🤖 AI 优化商品信息：{parsed_info['title']}")
                parsed_info = ai_generator.optimize_product(parsed_info)
                print(f"  ✅ AI 优化完成：{parsed_info['title']}")
            
            # 输出信息
            print(f"  标题：{parsed_info['title']}")
            print(f"  价格：¥{parsed_info.get('price', '未知')}")
            print(f"  图片：{len(parsed_info.get('images', []))}张")
            
            # 发布
            success = publisher.publish(parsed_info)
            
            if success:
                success_count += 1
                logger.info(f"✅ 上架成功：{product['title']}")
                
                # 注册商品到自动发货
                if parsed_info.get('share_url') and parsed_info.get('share_code'):
                    # 保存到注册列表
                    all_registered.append({
                        'product_name': parsed_info['title'],
                        'share_url': parsed_info['share_url'],
                        'share_code': parsed_info['share_code'],
                        'price': parsed_info.get('price', ''),
                        'source_file': args.source_file
                    })
                    
                    # 如果有监控器，也注册进去
                    if auto_responder:
                        auto_responder.add_product(
                            parsed_info['title'],
                            parsed_info['share_url'],
                            parsed_info['share_code'],
                            parsed_info.get('price', '')
                        )
                    logger.info(f"✅ 已注册到自动发货：{product['title']}")
                
                # 保存
                with open(registered_products_file, 'w', encoding='utf-8') as f:
                    json.dump(all_registered, f, ensure_ascii=False, indent=2)
            else:
                fail_count += 1
                logger.warning(f"⚠️  上架未完成：{product['title']}（需要你手动完成分类和发布）")
            
            # 等待用户确认继续
            print(f"\n当前商品处理完成，请在浏览器完成手动操作（选分类，点发布），完成后按回车继续下一个...")
            input()
            
            # 等待一下，避免操作太快
            if idx < len(products):
                logger.info(f"等待 {args.delay} 秒后上架下一个...")
                time.sleep(args.delay)
            
        except Exception as e:
            logger.error(f"❌ 上架异常：{e}")
            fail_count += 1
            print("发生异常，按回车继续下一个...")
            input()
            continue
    
    # 批量上架完成
    print("\n" + "="*60)
    logger.info("🎉 批量上架完成！")
    logger.info(f"   成功：{success_count} 个")
    logger.info(f"   失败/跳过：{fail_count} 个")
    print(f"\n🎉 批量上架完成！")
    print(f"   ✅ 成功：{success_count} 个")
    print(f"   ❌ 失败/跳过：{fail_count} 个")
    print(f"   📦 已注册自动发货：{len(all_registered)} 个商品")
    print("="*60 + "\n")
    
    # 如果需要启动监控
    if args.monitor:
        logger.info("🚀 启动聊天监控，开始自动回复和自动发货...")
        monitor.go_to_chat_list()
        monitor.start_monitoring()
    
    return 0

if __name__ == '__main__':
    exit(main())
