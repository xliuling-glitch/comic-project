#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品信息解析器
从 ZIP 压缩包中解析商品主图和介绍
"""

import os
import re
import zipfile
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger('ProductParser')

class ProductParser:
    """商品信息解析器"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True, parents=True)
        
    def extract_share_link(self, text: str) -> Optional[Dict]:
        """
        从文本中提取分享链接信息
        
        Returns:
            {
                'type': 'quark'/'baidu',
                'url': 链接,
                'code': 提取码
            } 或 None
        """
        # 夸克链接匹配
        quark_patterns = [
            r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+',
            r'https?://panquark\.cn/s/[a-zA-Z0-9]+',
            r'https?://.*quark.*?/(s/|share/)[a-zA-Z0-9]+'
        ]
        
        # 百度网盘链接匹配
        baidu_patterns = [
            r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+',
            r'https?://pan\.baidu\.com/share/link\?shareid=[0-9]+&uk=[0-9]+'
        ]
        
        # 提取码匹配
        code_pattern = r'提取码[:：\s]*([a-zA-Z0-9]{4})'
        
        # 检查夸克
        for pattern in quark_patterns:
            matches = re.findall(pattern, text)
            if matches:
                url = matches[0]
                code_matches = re.findall(code_pattern, text)
                code = code_matches[0] if code_matches else ""
                return {
                    'type': 'quark',
                    'url': url,
                    'code': code
                }
                
        # 检查百度
        for pattern in baidu_patterns:
            matches = re.findall(pattern, text)
            if matches:
                url = matches[0]
                code_matches = re.findall(code_pattern, text)
                code = code_matches[0] if code_matches else ""
                return {
                    'type': 'baidu',
                    'url': url,
                    'code': code
                }
                
        return None
    
    def find_product_info(self, folder_path: Path) -> Optional[Dict]:
        """
        在文件夹中查找商品信息
        
        查找规则：
        - 找 .txt/.md 文件作为商品介绍
        - 第一个图片或带"主图""封面"的作为主图
        - 返回商品信息字典
        """
        product_info = {
            'title': '',
            'description': '',
            'price': '',
            'original_price': '',
            'main_image': None,
            'images': [],
            'tags': [],
            'category': '',
            'source_folder': str(folder_path)
        }
        
        # 查找描述文件（按优先级）
        desc_candidates = []
        for ext in ['*.md', '*.txt', '*.description']:
            desc_candidates.extend(folder_path.glob(ext))
            desc_candidates.extend(folder_path.glob(ext.upper()))
        
        if desc_candidates:
            # 使用第一个文本文件作为描述
            desc_file = desc_candidates[0]
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()
                product_info['description'] = content.strip()
                
                # 解析内容找标题、价格等
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                
                if lines:
                    # 第一行作为标题
                    product_info['title'] = lines[0].replace('#', '').replace('##', '').strip()
                    
                    # 查找价格
                    price_patterns = [
                        r'价格[:：]\s*(\d+\.?\d*)',
                        r'￥\s*(\d+\.?\d*)',
                        r'¥\s*(\d+\.?\d*)',
                    ]
                    for pattern in price_patterns:
                        price_match = re.findall(pattern, content, re.I)
                        if price_match:
                            product_info['price'] = price_match[0]
                            break
                    
                    # 查找原价
                    original_price_patterns = [
                        r'原价[:：]\s*(\d+\.?\d*)',
                        r'原价.*?(\d+\.?\d*)',
                    ]
                    for pattern in original_price_patterns:
                        match = re.findall(pattern, content, re.I)
                        if match:
                            product_info['original_price'] = match[0]
                            break
                    
                    # 查找标签/分类
                    category_match = re.findall(r'分类[:：]\s*(.+)', content, re.I)
                    if category_match:
                        product_info['category'] = category_match[0].strip()
                    
                    tags_match = re.findall(r'标签[:：]\s*(.+)', content, re.I)
                    if tags_match:
                        tags_str = tags_match[0].strip()
                        product_info['tags'] = [t.strip() for t in re.split(r'[，,、\s]+', tags_str) if t.strip()]
        
        # 查找图片文件
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp', '*.JPG', '*.PNG']
        images = []
        for ext in image_extensions:
            images.extend(folder_path.glob(ext))
        
        # 排序，优先找主图/封面
        def image_priority(img_path: Path):
            name = img_path.name.lower()
            if '主图' in name or '封面' in name or 'cover' in name or 'main' in name:
                return 0
            if '首图' in name or '图1' in name:
                return 1
            if 'img' in name or '图' in name:
                return 2
            return 3
        
        images.sort(key=image_priority)
        
        if images:
            product_info['main_image'] = str(images[0])
            product_info['images'] = [str(img) for img in images]
        
        # 如果没有标题，使用文件夹名称
        if not product_info['title']:
            product_info['title'] = folder_path.name
            
        # 如果至少有图片或描述，就返回
        if product_info['description'] or product_info['main_image']:
            logger.info(f"解析成功：{product_info['title']}, 主图={product_info['main_image']}, {len(product_info['images'])}张图")
            return product_info
        
        logger.warning("未找到任何商品信息")
        return None
    
    def extract_zip(self, zip_path: Path, extract_dir: Path) -> Optional[Path]:
        """解压 ZIP 文件"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # 检查是否有嵌套文件夹
                top_dirs = set()
                for name in zf.namelist():
                    if not name.endswith('/') and '/' in name:
                        top_dirs.add(name.split('/')[0])
                    elif not name.endswith('/'):
                        top_dirs.add('')
                
                if len(top_dirs) == 1 and list(top_dirs)[0]:
                    # 单层结构，直接解压
                    zf.extractall(extract_dir)
                    return extract_dir / list(top_dirs)[0]
                else:
                    # 直接解压到当前目录
                    zf.extractall(extract_dir)
                    return extract_dir
                    
        except Exception as e:
            logger.error(f"解压失败：{e}")
            return None
    
    def parse_zip_file(self, zip_path: str) -> Optional[Dict]:
        """
        解析 ZIP 压缩包，提取商品信息
        
        Args:
            zip_path: ZIP 文件路径
            
        Returns:
            商品信息字典，解析失败返回 None
        """
        zip_path = Path(zip_path)
        if not zip_path.exists():
            logger.error(f"文件不存在：{zip_path}")
            return None
            
        # 创建解压目录
        extract_dir = self.download_dir / zip_path.stem
        if extract_dir.exists():
            # 如果已经解压过，直接解析
            product_info = self.find_product_info(extract_dir)
            if product_info:
                return product_info
        
        extract_dir.mkdir(exist_ok=True, parents=True)
        
        # 解压
        product_dir = self.extract_zip(zip_path, extract_dir)
        if not product_dir:
            return None
            
        # 查找商品信息，先检查顶层目录
        product_info = self.find_product_info(product_dir)
        
        if product_info:
            return product_info
            
        # 如果顶层没有，检查所有子目录
        for sub_dir in product_dir.iterdir():
            if sub_dir.is_dir():
                product_info = self.find_product_info(sub_dir)
                if product_info:
                    return product
        
        # 如果所有子目录都没找到，检查顶层所有文件
        product_info = self.find_product_info(product_dir)
        return product_info
    
    def get_image_files(self, product_info: Dict) -> List[str]:
        """获取所有图片文件路径"""
        return product_info.get('images', [])
    
    def get_main_image(self, product_info: Dict) -> Optional[str]:
        """获取主图路径"""
        return product_info.get('main_image')
