#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量上架商品
从你的货源文档批量读取商品信息，一个个自动上架
格式支持：
- CSV 格式
- JSON 格式
- Markdown 列表格式
"""

import csv
import json
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger('BatchPublisher')

class BatchProductReader:
    """从文档批量读取商品信息"""
    
    def __init__(self):
        pass
    
    def read_from_csv(self, file_path: str) -> List[Dict]:
        """
        从 CSV 文件读取
        
        CSV 表头要求：title,price,zip_path,share_url,share_code
        或者：商品名称,价格,压缩包路径,链接,提取码
        """
        products = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 兼容不同表头名称
                    product = {}
                    # 尝试各种命名
                    product['title'] = self._find_field(row, ['title', '商品名称', '名称', '商品名'])
                    product['price'] = self._find_field(row, ['price', '价格', '售价'])
                    product['zip_path'] = self._find_field(row, ['zip_path', '压缩包', '压缩包路径', '文件路径'])
                    product['share_url'] = self._find_field(row, ['share_url', '链接', '网盘链接', 'url'])
                    product['share_code'] = self._find_field(row, ['share_code', 'code', '提取码', '密码'])
                    product['description'] = self._find_field(row, ['description', '描述', '介绍'], '')
                    
                    # 只要有标题就加进去
                    if product['title']:
                        products.append(product)
                        
            logger.info(f"从 CSV 读取了 {len(products)} 个商品")
            return products
            
        except Exception as e:
            logger.error(f"读取 CSV 失败：{e}")
            return []
    
    def read_from_json(self, file_path: str) -> List[Dict]:
        """从 JSON 文件读取"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    logger.info(f"从 JSON 读取了 {len(data)} 个商品")
                    return data
                elif isinstance(data, dict) and 'products' in data:
                    products = data['products']
                    logger.info(f"从 JSON 读取了 {len(products)} 个商品")
                    return products
            return []
        except Exception as e:
            logger.error(f"读取 JSON 失败：{e}")
            return []
    
    def read_from_markdown(self, file_path: str) -> List[Dict]:
        """
        从 Markdown 文档读取
        格式示例：
        ## 商品名称
        - 价格：99
        - 压缩包：./files/商品.zip
        - 链接：https://pan.quark.cn/s/xxx
        - 提取码：abcd
        - 描述：xxxx
        
        或者一行一个：
        - [商品名](链接) 价格: 99 提取码: abcd  文件: xxx.zip
        """
        products = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按 ## 分割商品
            sections = re.split(r'^##\s+', content, flags=re.M)
            
            for section in sections:
                if not section.strip():
                    continue
                    
                lines = section.strip().split('\n')
                title = lines[0].strip()
                product = {
                    'title': title,
                    'price': '',
                    'zip_path': '',
                    'share_url': '',
                    'share_code': '',
                    'description': ''
                }
                
                # 解析剩下的行
                desc_lines = []
                for line in lines[1:]:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 匹配 - 价格: xxx
                    price_match = re.match(r'[-*]*\s*价格[:：]\s*(\d+\.?\d*)', line, re.I)
                    if price_match:
                        product['price'] = price_match.group(1)
                        continue
                        
                    zip_match = re.match(r'[-*]*\s*(压缩包|文件|zip)[:：]\s*(.+)', line, re.I)
                    if zip_match:
                        product['zip_path'] = zip_match.group(2).strip()
                        continue
                        
                    url_match = re.match(r'[-*]*\s*(链接|网盘|url)[:：]\s*(https?://.+)', line, re.I)
                    if url_match:
                        product['share_url'] = url_match.group(2).strip()
                        continue
                        
                    code_match = re.match(r'[-*]*\s*(提取码|密码|code)[:：]\s*([a-zA-Z0-9]{4})', line, re.I)
                    if code_match:
                        product['share_code'] = code_match.group(2).strip()
                        continue
                        
                    # 其他行当作描述
                    desc_lines.append(line)
                
                if desc_lines:
                    product['description'] = '\n'.join(desc_lines)
                
                if product['title']:
                    products.append(product)
            
            # 如果没有找到分节，尝试一行一个商品格式
            if not products:
                # 匹配 - 商品名 价格:99 链接:xxx 提取码:abcd
                pattern = r'[-*]\s+(.+?)\s+价格[:：]\s*(\d+\.?\d*)\s+链接[:：]\s*(https?://\S+)\s+提取码[:：]\s*([a-zA-Z0-9]{4})'
                matches = re.findall(pattern, content, re.I)
                for match in matches:
                    title, price, url, code = match
                    products.append({
                        'title': title.strip(),
                        'price': price.strip(),
                        'share_url': url.strip(),
                        'share_code': code.strip(),
                        'zip_path': ''
                    })
            
            logger.info(f"从 Markdown 读取了 {len(products)} 个商品")
            return products
            
        except Exception as e:
            logger.error(f"读取 Markdown 失败：{e}")
            return []
    
    def _find_field(self, row: Dict, names: List[str], default: str = None) -> Optional[str]:
        """查找字段，兼容不同表头"""
        for name in names:
            if name in row:
                return row[name].strip()
            # 试试大写小写
            if name.lower() in row:
                return row[name.lower()].strip()
        return default
    
    def auto_read(self, file_path: str) -> List[Dict]:
        """自动识别格式读取"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            return self.read_from_csv(file_path)
        elif suffix in ['.json']:
            return self.read_from_json(file_path)
        elif suffix in ['.md', '.markdown']:
            return self.read_from_markdown(file_path)
        elif suffix in ['.txt']:
            # txt 试试 markdown 格式
            return self.read_from_markdown(file_path)
        else:
            logger.warning(f"不支持的文件格式：{suffix}")
            return []
