#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咸鱼自动发布器
通过 Selenium 控制浏览器操作咸鱼后台发布商品
"""

import os
import time
import logging
from typing import Optional, List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger('XianyuPublisher')

class XianyuPublisher:
    """咸鱼自动发布器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.driver: Optional[webdriver.Chrome] = None
        
    def start_browser(self) -> bool:
        """启动浏览器"""
        try:
            options = webdriver.ChromeOptions()
            # 保持登录状态，使用已有用户数据
            if self.config.get('chrome_user_data_dir'):
                options.add_argument(f"--user-data-dir={self.config['chrome_user_data_dir']}")
            options.add_argument('--start-maximized')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://www.2.taobao.com/")
            
            logger.info("浏览器已启动，请确保已登录咸鱼账号")
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"启动浏览器失败：{e}")
            logger.error("请确保已安装 Chrome 浏览器和 chromedriver")
            return False
    
    def wait_for_element(self, by, value, timeout: int = 10):
        """等待元素加载"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception:
            return None
    
    def upload_images(self, image_paths: List[str]) -> bool:
        """上传图片"""
        try:
            # 找到文件上传输入框
            # 咸鱼的上传控件是 input type=file
            file_input = self.wait_for_element(By.CSS_SELECTOR, "input[type='file']")
            if not file_input:
                logger.error("找不到文件上传控件")
                return False
            
            # 拼接所有图片路径（用换行符分隔）
            # Windows 下需要绝对路径
            abs_paths = [os.path.abspath(path) for path in image_paths]
            file_input.send_keys('\n'.join(abs_paths))
            
            logger.info(f"已上传 {len(abs_paths)} 张图片")
            time.sleep(5 + len(abs_paths))  # 等待上传完成
            return True
            
        except Exception as e:
            logger.error(f"上传图片失败：{e}")
            return False
    
    def fill_product_info(self, product_info: Dict) -> bool:
        """填写商品信息"""
        try:
            # 标题
            title = product_info.get('title', '')
            if title:
                title_input = self.wait_for_element(By.CSS_SELECTOR, "[placeholder*='标题'], [name*='title']")
                if title_input:
                    title_input.clear()
                    title_input.send_keys(title)
                    logger.info(f"填写标题：{title}")
            
            time.sleep(1)
            
            # 价格
            price = product_info.get('price', '')
            if price:
                price_input = self.wait_for_element(By.CSS_SELECTOR, "[placeholder*='价格'], [name*='price']")
                if price_input:
                    price_input.clear()
                    price_input.send_keys(str(price))
                    logger.info(f"填写价格：{price}")
            
            time.sleep(1)
            
            # 商品描述
            description = product_info.get('description', '')
            if description:
                desc_input = self.wait_for_element(By.CSS_SELECTOR, "[placeholder*='描述'], [name*='desc'], textarea")
                if desc_input:
                    desc_input.clear()
                    desc_input.send_keys(description)
                    logger.info("填写描述完成")
            
            time.sleep(1)
            
            # 分类
            # 分类需要点击选择，这里跳过，留给用户手动选择
            # 不同商品分类不一样
                
            return True
            
        except Exception as e:
            logger.error(f"填写信息失败：{e}")
            return False
    
    def publish(self, product_info: Dict) -> bool:
        """
        发布商品到咸鱼
        
        流程：
        1. 打开咸鱼发布页面
        2. 上传图片
        3. 填写标题、价格、描述
        4. 等待用户确认分类后点击发布
        """
        if not self.driver:
            if not self.start_browser():
                return False
        
        logger.info(f"开始发布商品到咸鱼：{product_info['title']}")
        
        try:
            # 打开发布页面
            self.driver.get("https://www.2.taobao.com/list/item/goodsPublish.htm")
            time.sleep(3)
            
            # 检查是否需要登录
            if "login" in self.driver.current_url:
                logger.error("需要登录，请先在浏览器手动登录咸鱼账号")
                return False
            
            # 上传图片
            images = product_info.get('images', [])
            if not images:
                logger.error("没有图片，无法发布")
                return False
            
            logger.info(f"准备上传 {len(images)} 张图片")
            if not self.upload_images(images):
                return False
            
            # 填写信息
            if not self.fill_product_info(product_info):
                logger.warning("部分信息填写失败，请手动补全")
            
            logger.info("\n" + "="*60)
            logger.info("✅ 图片已上传，基本信息已填写")
            logger.info("📝 请手动完成：")
            logger.info("   1. 选择商品分类")
            logger.info("   2. 检查价格、描述是否正确")
            logger.info("   3. 点击发布按钮")
            logger.info("="*60 + "\n")
            
            # 如果有网盘链接信息，自动注册到自动回复器，下单自动发
            if hasattr(self, 'monitor') and self.monitor:
                if product_info.get('share_url') and product_info.get('share_code'):
                    self.monitor.register_product(
                        product_info['title'],
                        product_info['share_url'],
                        product_info['share_code'],
                        product_info.get('price', '')
                    )
                    logger.info(f"✅ 已注册商品「{product_info['title']}」到自动发货列表")
                    logger.info("买家付款后会自动发送网盘链接！")
            
            return True
            
        except Exception as e:
            logger.error(f"发布失败：{e}")
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
    
    def format_description(self, product_info: Dict) -> str:
        """格式化商品描述"""
        description = product_info.get('description', '')
        title = product_info.get('title', '')
        price = product_info.get('price', '')
        
        if not description:
            description = title
        
        # 咸鱼常用描述格式
        template = f"""{description}

商品：{title}
价格：¥{price}

实拍图片，所见即所得~"""
        
        return template.strip()
