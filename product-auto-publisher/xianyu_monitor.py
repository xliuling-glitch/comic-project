#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
咸鱼聊天监控
- 持续监控新消息
- 自动回复客服咨询
- 检测到下单自动发送网盘链接
"""

import time
import logging
from typing import Optional, List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from auto_responder import AutoResponder

logger = logging.getLogger('XianyuMonitor')

class XianyuChatMonitor:
    """咸鱼聊天监控器"""
    
    def __init__(self, driver: webdriver.Chrome, auto_responder: AutoResponder):
        self.driver = driver
        self.auto_responder = auto_responder
        self.last_processed_msg_id = None
        self.check_interval = 10  # 检查间隔（秒）
        
    def go_to_chat_list(self):
        """进入聊天列表页面"""
        try:
            self.driver.get("https://s.2.taobao.com/ms/list.htm")
            time.sleep(3)
            logger.info("已进入聊天列表页面")
            return True
        except Exception as e:
            logger.error(f"进入聊天列表失败：{e}")
            return False
    
    def get_unread_chats(self) -> List[Dict]:
        """获取未读消息的聊天"""
        unread = []
        try:
            # 查找未读消息条目，需要根据实际页面结构调整选择器
            chat_items = self.driver.find_elements(By.CSS_SELECTOR, ".msg-item, .list-item, [data-unread]")
            
            for item in chat_items:
                try:
                    unread_count = item.get_attribute("data-unread")
                    if unread_count and int(unread_count) > 0:
                        title = item.find_element(By.CSS_SELECTOR, ".title, .user-name").text.strip()
                        last_msg = item.find_element(By.CSS_SELECTOR, ".last-msg, .content").text.strip()
                        unread.append({
                            'element': item,
                            'title': title,
                            'unread_count': int(unread_count),
                            'last_msg': last_msg
                        })
                except Exception:
                    continue
                    
            logger.info(f"找到 {len(unread)} 个未读聊天")
            return unread
            
        except Exception as e:
            logger.error(f"获取未读列表失败：{e}")
            return []
    
    def open_chat(self, chat_item) -> bool:
        """打开聊天窗口"""
        try:
            chat_item['element'].click()
            time.sleep(2)
            logger.info(f"打开聊天：{chat_item['title']}")
            return True
        except Exception as e:
            logger.error(f"打开聊天失败：{e}")
            return False
    
    def get_new_messages(self) -> List[str]:
        """获取聊天中的新消息"""
        messages = []
        try:
            # 查找消息列表，选择器需要根据实际调整
            msg_elements = self.driver.find_elements(By.CSS_SELECTOR, ".msg-content, .message-content")
            
            for elem in msg_elements:
                try:
                    # 判断是不是对方发来的消息
                    if 'other' in elem.get_attribute('class') or 'left' in elem.get_attribute('class'):
                        text = elem.text.strip()
                        if text:
                            messages.append(text)
                except Exception:
                    continue
                    
            return messages
            
        except Exception as e:
            logger.error(f"获取新消息失败：{e}")
            return []
    
    def send_reply(self, reply_text: str) -> bool:
        """发送回复"""
        try:
            # 找到输入框
            input_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, [contenteditable], .input-box"))
            )
            
            input_box.clear()
            input_box.send_keys(reply_text)
            time.sleep(0.5)
            
            # 点击发送按钮
            send_btn = self.driver.find_element(By.CSS_SELECTOR, ".send-btn, button[type=submit]")
            send_btn.click()
            time.sleep(1)
            
            logger.info(f"已发送回复：{reply_text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"发送回复失败：{e}")
            return False
    
    def process_chat(self, chat_item) -> bool:
        """处理一个未读聊天"""
        if not self.open_chat(chat_item):
            return False
            
        messages = self.get_new_messages()
        if not messages:
            logger.warning("打开聊天后没有找到消息内容")
            return False
            
        logger.info(f"收到 {len(messages)} 条新消息")
        
        # 处理每条消息
        replied = False
        for msg in messages:
            logger.info(f"用户消息：{msg}")
            
            # 使用自动回复器匹配
            reply = self.auto_responder.match_reply(msg)
            if reply:
                logger.info(f"匹配到自动回复，发送中...")
                if self.send_reply(reply):
                    replied = True
                # 如果发了链接，就记录一下
                if "网盘链接" in reply:
                    logger.info("已自动发送网盘链接")
                    
        return replied
    
    def register_product(self, product_name: str, share_url: str, share_code: str, price: str = ""):
        """注册商品，保存网盘信息用于下单后自动发送"""
        self.auto_responder.add_product(product_name, share_url, share_code, price)
        
    def start_monitoring(self):
        """开始监控循环"""
        logger.info("🚀 开始监控咸鱼聊天消息...")
        print("\n监控已启动，按 Ctrl+C 停止\n")
        
        try:
            while True:
                # 刷新聊天列表
                self.driver.refresh()
                time.sleep(2)
                
                # 获取未读聊天
                unread_chats = self.get_unread_chats()
                
                # 处理每个未读聊天
                for chat in unread_chats:
                    logger.info(f"处理未读聊天：{chat['title']}")
                    self.process_chat(chat)
                    time.sleep(1)
                
                # 等待下次检查
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("用户停止监控")
            print("\n监控已停止")
        except Exception as e:
            logger.error(f"监控异常：{e}")
            raise
    
    def add_auto_reply(self, keyword: str, reply: str):
        """添加自定义自动回复规则"""
        self.auto_responder.add_custom_rule(keyword, reply)
