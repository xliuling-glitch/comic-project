#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品自动发布模块
- 解析夸克/百度网盘链接
- 自动下载并解压压缩包
- 提取主图和商品介绍
- 自动发布到企业微信
"""

import os
import re
import json
import zipfile
import logging
import requests
from typing import Optional, Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger('ProductPublisher')

class ProductParser:
    """商品信息解析器"""
    
    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
    def extract_share_link(self, text: str) -> Optional[Tuple[str, str]]:
        """
        从文本中提取分享链接和提取码
        
        Returns:
            (链接, 提取码) 或 None
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
        
        # 查找链接
        all_patterns = [
            ('quark', p) for p in quark_patterns
        ] + [
            ('baidu', p) for p in baidu_patterns
        ]
        
        for type_name, pattern in all_patterns:
            matches = re.findall(pattern, text)
            if matches:
                link = matches[0]
                # 查找提取码
                code_matches = re.findall(code_pattern, text)
                code = code_matches[0] if code_matches else ""
                logger.info(f"找到{type_name}链接：{link}，提取码：{code}")
                return (type_name, link, code)
                
        return None
    
    def find_product_info(self, folder_path: Path) -> Optional[Dict]:
        """
        在文件夹中查找商品信息
        
        查找规则：
        - 找 .txt/.md 文件作为商品介绍
        - 找 主图 封面图 第一个图片作为主图
        """
        product_info = {
            'title': '',
            'description': '',
            'price': '',
            'main_image': None,
            'images': [],
            'source_folder': str(folder_path)
        }
        
        # 查找描述文件
        desc_files = list(folder_path.glob('*.txt')) + list(folder_path.glob('*.md'))
        
        if desc_files:
            # 使用第一个文本文件作为描述
            with open(desc_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
                product_info['description'] = content
                
                # 从第一行提取标题
                first_line = content.split('\n')[0].strip()
                if first_line:
                    product_info['title'] = first_line.replace('#', '').strip()
        
        # 查找图片文件
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
        images = []
        for ext in image_extensions:
            images.extend(folder_path.glob(ext))
            images.extend(folder_path.glob(ext.upper()))
        
        # 排序，优先找主图/封面
        def image_priority(img_path):
            name = img_path.name.lower()
            if '主图' in name or '封面' in name or 'cover' in name:
                return 0
            if 'img' in name or '图' in name:
                return 1
            return 2
        
        images.sort(key=image_priority)
        
        if images:
            product_info['main_image'] = str(images[0])
            product_info['images'] = [str(img) for img in images]
        
        # 如果没有标题，使用文件夹名称
        if not product_info['title']:
            product_info['title'] = folder_path.name
            
        return product_info if product_info['description'] or product_info['main_image'] else None
    
    def extract_zip(self, zip_path: Path, extract_dir: Path) -> Optional[Path]:
        """解压 ZIP 文件"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # 检查是否有嵌套文件夹
                top_dirs = set()
                for name in zf.namelist():
                    if not name.endswith('/'):
                        top_dirs.add(name.split('/')[0])
                
                if len(top_dirs) == 1:
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
        """解析 ZIP 压缩包，提取商品信息"""
        zip_path = Path(zip_path)
        if not zip_path.exists():
            logger.error(f"文件不存在：{zip_path}")
            return None
            
        # 创建解压目录
        extract_dir = self.download_dir / zip_path.stem
        extract_dir.mkdir(exist_ok=True)
        
        # 解压
        product_dir = self.extract_zip(zip_path, extract_dir)
        if not product_dir:
            return None
            
        # 查找商品信息
        # 先检查顶层目录
        product_info = self.find_product_info(product_dir)
        
        if product_info:
            return product_info
            
        # 如果顶层没有，检查子目录
        for sub_dir in product_dir.iterdir():
            if sub_dir.is_dir():
                product_info = self.find_product_info(sub_dir)
                if product_info:
                    return product_info
        
        return None

class QuarkDownloader:
    """夸克网盘下载器（需要配置 Cookie）"""
    
    def __init__(self, cookie: str = None):
        self.session = requests.Session()
        if cookie:
            # 设置 Cookie
            for cookie_item in cookie.split(';'):
                if '=' in cookie_item:
                    name, value = cookie_item.split('=', 1)
                    self.session.cookies.set(name.strip(), value.strip())
    
    def get_download_url(self, share_url: str, pwd: str) -> Optional[str]:
        """
        获取下载链接
        注：需要有效的 Cookie 才能下载，这是一个占位实现
        实际使用需要根据夸克 API 进行调整
        """
        # 这里需要实现夸克网盘 API 调用
        # 由于反爬限制，建议手动下载后发送给机器人处理
        logger.info(f"需要手动下载：{share_url} 提取码：{pwd}")
        return None

class BaiduDownloader:
    """百度网盘下载器（需要配置 Cookie）"""
    
    def __init__(self, cookie: str = None):
        self.session = requests.Session()
        if cookie:
            for cookie_item in cookie.split(';'):
                if '=' in cookie_item:
                    name, value = cookie_item.split('=', 1)
                    self.session.cookies.set(name.strip(), value.strip())
    
    def get_download_url(self, share_url: str, pwd: str) -> Optional[str]:
        """获取下载链接"""
        # 同样需要实现百度网盘 API
        # 由于反爬限制，建议手动下载后发送给机器人处理
        logger.info(f"需要手动下载：{share_url} 提取码：{pwd}")
        return None

class AutoProductPublisher:
    """商品自动发布器"""
    
    def __init__(self, bot, config_path: str = None):
        self.bot = bot
        self.parser = ProductParser()
        
        # 加载配置
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}
            
        # 初始化下载器（如果有 cookie）
        self.quark_downloader = QuarkDownloader(self.config.get('quark_cookie'))
        self.baidu_downloader = BaiduDownloader(self.config.get('baidu_cookie'))
        
    def format_product_markdown(self, product_info: Dict) -> str:
        """将商品信息格式化为 Markdown"""
        title = product_info.get('title', '商品')
        description = product_info.get('description', '')
        price = product_info.get('price', '')
        
        markdown = f"# {title}\n\n"
        
        if price:
            markdown += f"**价格：** {price}\n\n"
            
        if description:
            markdown += f"{description}\n\n"
            
        image_count = len(product_info.get('images', []))
        if image_count > 1:
            markdown += f"*共 {image_count} 张图片*\n"
            
        return markdown.strip()
    
    async def upload_image(self, image_path: str) -> Optional[str]:
        """上传图片到企业微信，返回 media_id"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片不存在：{image_path}")
                return None
                
            file_size = os.path.getsize(image_path)
            
            # 检查大小限制（企业微信要求图片 ≤ 2MB）
            if file_size > 2 * 1024 * 1024:
                logger.warning(f"图片过大：{file_size} bytes，超过 2MB 限制")
                return None
                
            with open(image_path, 'rb') as f:
                image_data = f.read()
                
            # 初始化上传
            filename = os.path.basename(image_path)
            upload_id = await self.bot.upload_media_init(
                file_type="image",
                filename=filename,
                total_size=file_size,
                total_chunks=1
            )
            
            if not upload_id:
                logger.error("初始化上传失败")
                return None
                
            # 上传分片
            import base64
            base64_data = base64.b64encode(image_data).decode()
            success = await self.bot.upload_media_chunk(upload_id, 0, base64_data)
            
            if not success:
                logger.error("上传分片失败")
                return None
                
            # 完成上传
            result = await self.bot.upload_media_finish(upload_id)
            if result:
                media_id = result.get('media_id')
                logger.info(f"图片上传成功：media_id={media_id}")
                return media_id
                
            return None
            
        except Exception as e:
            logger.error(f"上传图片失败：{e}")
            return None
    
    async def publish_product(self, chat_id: str, chat_type: int, product_info: Dict):
        """发布商品"""
        try:
            # 格式化描述
            markdown_content = self.format_product_markdown(product_info)
            
            # 如果有主图，先上传并发送图片
            main_image_path = product_info.get('main_image')
            if main_image_path:
                media_id = await self.upload_image(main_image_path)
                if media_id:
                    # 发送图片
                    await self.bot.send_msg(chat_id, chat_type, {
                        "msgtype": "image",
                        "image": {
                            "media_id": media_id
                        }
                    })
            
            # 发送文本描述（markdown 格式）
            await self.bot.send_msg(chat_id, chat_type, {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_content
                }
            })
            
            logger.info(f"商品发布成功：{product_info.get('title')}")
            return True
            
        except Exception as e:
            logger.error(f"发布商品失败：{e}")
            return False
    
    async def process_message(self, data):
        """处理接收到的消息，检查是否包含分享链接"""
        body = data.get('body', {})
        msgtype = body.get('msgtype')
        chat_id = body.get('chatid')
        chat_type = body.get('chat_type', 1)  # 1=单聊，2=群聊
        
        if msgtype != 'text':
            return False
            
        content = body.get('text', {}).get('content', '')
        
        # 提取分享链接
        result = self.parser.extract_share_link(content)
        if not result:
            # 没有链接，检查是否是本地文件上传？
            # 如果是已经发送的 ZIP 文件，需要处理
            return False
            
        type_name, link, code = result
        
        # 回复用户正在处理
        req_id = data.get('headers', {}).get('req_id')
        if req_id:
            await self.bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {
                    "content": f"收到{type_name}分享链接：\n{link}\n提取码：{code}\n\n正在处理中，请稍候..."
                }
            })
        
        # 尝试下载（如果配置了 cookie）
        # 如果没有配置 cookie，提示手动下载
        download_url = None
        
        if type_name == 'quark':
            if self.quark_downloader.cookie:
                download_url = self.quark_downloader.get_download_url(link, code)
        elif type_name == 'baidu':
            if self.baidu_downloader.cookie:
                download_url = self.baidu_downloader.get_download_url(link, code)
                
        if not download_url:
            # 提示用户手动下载后发送 ZIP 文件
            if req_id:
                await self.bot.respond_msg(req_id, {
                    "msgtype": "text",
                    "text": {
                        "content": (
                            "由于网盘反爬限制，请您：\n\n"
                            "1. 使用浏览器或客户端打开链接\n"
                            "2. 下载压缩包（.zip 文件）到本地\n"
                            "3. 将 ZIP 文件发送到这里\n"
                            "4. 我会自动解析并发布商品\n\n"
                            "链接内容已收到，等你发文件哦😊"
                        )
                    }
                })
            return False
            
        # 如果成功获取下载链接，下载并处理...
        # 这部分需要完善下载逻辑，此处省略
        
        return True
    
    async def process_file(self, data):
        """处理接收到的文件（ZIP）"""
        body = data.get('body', {})
        msgtype = body.get('msgtype')
        
        if msgtype != 'file':
            return False
            
        chat_id = body.get('chatid')
        chat_type = body.get('chat_type', 1)
        filename = body.get('file', {}).get('filename', '')
        url = body.get('file', {}).get('url', '')
        
        # 只处理 ZIP 文件
        if not filename.lower().endswith('.zip'):
            return False
            
        logger.info(f"收到 ZIP 文件：{filename}，下载地址：{url}")
        
        # 回复用户
        req_id = data.get('headers', {}).get('req_id')
        if req_id:
            await self.bot.respond_msg(req_id, {
                "msgtype": "text", 
                "text": {
                    "content": f"收到文件：{filename}\n正在解析商品信息，请稍候..."
                }
            })
            
        try:
            # 下载文件
            download_path = str(self.parser.download_dir / filename)
            response = requests.get(url)
            with open(download_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"文件已下载：{download_path}")
            
            # 解析 ZIP 文件
            product_info = self.parser.parse_zip_file(download_path)
            
            if not product_info:
                if req_id:
                    await self.bot.respond_msg(req_id, {
                        "msgtype": "text",
                        "text": {
                            "content": "❌ 未能找到商品信息，请检查压缩包格式。\n\n正确格式：\n- 压缩包内包含 .txt/.md 文件作为商品描述\n- 包含 JPG/PNG 图片作为商品图片\n- 带有「主图」或「封面」的图片会优先作为首图"
                        }
                    })
                return False
                
            # 发布商品
            success = await self.publish_product(chat_id, chat_type, product_info)
            
            if success and req_id:
                await self.bot.respond_msg(req_id, {
                    "msgtype": "text",
                    "text": {
                        "content": f"✅ 商品「{product_info.get('title')}」发布成功！"
                    }
                })
                
            return success
            
        except Exception as e:
            logger.error(f"处理文件失败：{e}")
            if req_id:
                await self.bot.respond_msg(req_id, {
                    "msgtype": "text",
                    "text": {
                        "content": f"❌ 处理文件失败：{str(e)}"
                    }
                })
            return False
