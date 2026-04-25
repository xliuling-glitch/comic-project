#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品自动发布工具 - 主入口
支持：
- 解析夸克/百度网盘链接
- 从 ZIP 压缩包自动提取主图和商品介绍
- 自动发布到微信朋友圈 / 咸鱼
"""

import argparse
import json
import os
import logging
from product_parser import ProductParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Main')

def load_config(config_path='config.json'):
    """加载配置"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    parser = argparse.ArgumentParser(description='商品自动发布工具')
    parser.add_argument('zip_file', nargs='?', help='ZIP 压缩文件路径')
    parser.add_argument('--platform', '-p', choices=['wechat', 'xianyu', 'none'], default='none', 
                        help='发布平台：wechat(微信)/xianyu(咸鱼)/none(仅解析)')
    parser.add_argument('--output', '-o', help='输出解析结果到 JSON 文件')
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 初始化解析器
    product_parser = ProductParser(download_dir=config.get('download_dir', 'downloads'))
    
    if not args.zip_file:
        print("""
商品自动发布工具
================

使用方法：
  python main.py <ZIP文件路径> [--platform wechat/xianyu]

示例：
  python main.py ./商品.zip --platform xianyu
  python main.py ./商品.zip --platform wechat

功能：
  1. 自动解压 ZIP
  2. 自动识别主图（优先找带"主图""封面"的图片）
  3. 自动读取商品介绍（txt/md 文件）
  4. 自动填写到对应平台，准备发布

压缩包格式建议：
  商品名称.zip
  ├── 主图.jpg
  ├── 图片1.jpg
  ├── 图片2.jpg
  └── 描述.txt
      (第一行是标题，可以包含价格: 价格: 99)
")
        return
    
    # 解析 ZIP 文件
    logger.info(f"正在解析：{args.zip_file}")
    product_info = product_parser.parse_zip_file(args.zip_file)
    
    if not product_info:
        logger.error("❌ 解析失败，未找到商品信息")
        print("\n未能解析商品信息，请检查：")
        print("1. ZIP 文件中是否包含 .txt 或 .md 文件作为描述")
        print("2. 是否包含 JPG/PNG 图片文件")
        print("3. 文件编码是否为 UTF-8")
        return
    
    # 输出解析结果
    print("\n" + "="*60)
    print("✅ 解析成功！")
    print(f"📝 标题：{product_info['title']}")
    print(f"💰 价格：{product_info['price'] or '未找到'}")
    print(f"🖼️ 主图：{os.path.basename(product_info['main_image']) if product_info['main_image'] else '无'}")
    print(f"📄 图片数量：{len(product_info['images'])}")
    print("-"*60)
    print("描述预览：")
    desc_preview = product_info['description'][:200]
    if len(product_info['description']) > 200:
        desc_preview += "..."
    print(desc_preview)
    print("="*60 + "\n")
    
    # 输出到 JSON 文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(product_info, f, ensure_ascii=False, indent=2)
        logger.info(f"解析结果已保存到：{args.output}")
    
    # 根据平台发布
    if args.platform == 'xianyu':
        from xianyu_publisher import XianyuPublisher
        publisher = XianyuPublisher(config.get('xianyu', {}))
        success = publisher.publish(product_info)
        if not success:
            logger.error("❌ 咸鱼发布失败")
            return 1
    elif args.platform == 'wechat':
        from wechat_publisher import WeChatPublisher
        publisher = WeChatPublisher(config.get('wechat', {}))
        text = publisher.format_product_text(product_info)
        print("\n生成的微信文案：")
        print("-"*60)
        print(text)
        print("-"*60)
        print("\n请复制上面的文案，手动粘贴到朋友圈！")
        print(f"图片位置：{os.path.dirname(product_info['main_image'])}")
    
    logger.info("处理完成！")
    return 0

if __name__ == '__main__':
    exit(main())
