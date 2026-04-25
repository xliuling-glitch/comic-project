#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动客服回复 + 下单自动发网盘链接
监控咸鱼聊天，自动回复常见问题，下单成功自动发提取链接
"""

import re
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger('AutoResponder')

@dataclass
class AutoReplyRule:
    """自动回复规则"""
    keyword: str  # 匹配关键词
    reply: str    # 回复内容
    regex: bool = False  # 是否使用正则匹配

@dataclass
class ProductOrder:
    """商品订单信息"""
    product_name: str
    share_url: str
    share_code: str
    price: str

class AutoResponder:
    """自动回复管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.reply_rules: List[AutoReplyRule] = []
        self.product_map: Dict[str, ProductOrder] = {}  # 商品名 -> 订单信息
        
        # 加载默认规则
        self._load_default_rules()
        # 加载配置中的规则
        self._load_config_rules()
        
    def _load_default_rules(self):
        """加载默认常见售后问题回复"""
        default_rules = [
            # 发货相关
            AutoReplyRule(
                keyword=r'(发货|什么时候发|多久发货|发了吗)',
                reply=(
                    "您好😊 我们是自动发货哦！\n"
                    "付款成功后系统会自动将百度网盘/夸克网盘链接发给您，请查看聊天消息。\n"
                    "如果您已经付款还没收到链接，请告诉我订单号，我马上重发！"
                ),
                regex=True
            ),
            # 链接相关
            AutoReplyRule(
                keyword=r'(链接|提取码|打不开|下载|资源)',
                reply=(
                    "您好！付款后链接和提取码会自动发送到这里，请耐心等待一下哦~\n"
                    "如果已经付款，请截图订单通知，我会立即为您重发~"
                ),
                regex=True
            ),
            # 解压密码
            AutoReplyRule(
                keyword=r'(密码|解压|解压密码|密码多少)',
                reply=(
                    "您好！如果压缩包需要密码，一般在描述文件里哦。\n"
                    "如果找不到请告诉我具体是哪个商品，我发给您~"
                ),
                regex=True
            ),
            # 文件打不开
            AutoReplyRule(
                keyword=r'(打不开|打不开|错误|损坏|解压失败)',
                reply=(
                    "您好！请检查一下：\n"
                    "1. 是否下载完整了\n"
                    "2. 解压时是不是密码输入错误\n"
                    "3. 建议使用WinRAR或者Bandizip解压\n"
                    "如果还是不行请告诉我您的文件格式，我帮您解决！"
                ),
                regex=True
            ),
            # 退款相关
            AutoReplyRule(
                keyword=r'(退款|退钱|退货|能不能退|申请退款)',
                reply=(
                    "您好！虚拟商品一旦发货后通常不予退款哦，\n"
                    "因为资源已经可以永久保存使用了，还请理解~\n"
                    "如果确实是文件有问题，请截图说明，我们核实后会给您处理的。"
                ),
                regex=True
            ),
            # 问好
            AutoReplyRule(
                keyword=r'(你好|您好|在吗|hi|hello)',
                reply=(
                    "您好！我是智能客服，有什么问题请随时问我😊\n"
                    "常见问题我都会自动回答您哦~"
                ),
                regex=True
            ),
        ]
        
        self.reply_rules.extend(default_rules)
        
    def _load_config_rules(self):
        """从配置加载自定义规则"""
        custom_rules = self.config.get('custom_rules', [])
        for rule in custom_rules:
            self.reply_rules.append(AutoReplyRule(
                keyword=rule.get('keyword', ''),
                reply=rule.get('reply', ''),
                regex=rule.get('regex', False)
            ))
            
    def add_product(self, product_name: str, share_url: str, share_code: str, price: str = ""):
        """添加商品，关联网盘链接（下单后自动发）"""
        product_key = product_name.lower().strip()
        self.product_map[product_key] = ProductOrder(
            product_name=product_name,
            share_url=share_url,
            share_code=share_code,
            price=price
        )
        logger.info(f"添加商品：{product_name} -> {share_url} 提取码：{share_code}")
        
    def get_product_link(self, product_name: str) -> Optional[ProductOrder]:
        """根据商品名获取网盘链接"""
        # 模糊匹配
        product_key = product_name.lower().strip()
        for key, order in self.product_map.items():
            if product_key in key or key in product_key:
                return order
        return None
    
    def match_reply(self, message: str) -> Optional[str]:
        """匹配用户消息，返回对应的自动回复"""
        message_lower = message.lower()
        
        # 先检查是否是订单确认消息（买家已付款）
        if self._is_payment_notification(message):
            product_name = self._extract_product_from_notification(message)
            if product_name:
                order = self.get_product_link(product_name)
                if order:
                    # 找到商品，自动发链接
                    reply = self._format_share_link(order)
                    logger.info(f"检测到付款，自动发送链接：{product_name}")
                    return reply
        
        # 匹配常规自动回复规则
        for rule in self.reply_rules:
            if rule.regex:
                if re.search(rule.keyword, message_lower, re.I):
                    return rule.reply
            else:
                if rule.keyword.lower() in message_lower:
                    return rule.reply
                    
        return None
    
    def _is_payment_notification(self, message: str) -> bool:
        """判断是否是付款通知"""
        keywords = [
            '买家已付款',
            '支付成功',
            '已付款',
            '下单成功',
            '付款成功'
        ]
        return any(k in message for k in keywords)
    
    def _extract_product_from_notification(self, message: str) -> Optional[str]:
        """从通知中提取商品名称"""
        # 咸鱼通知格式一般包含 "购买了 [商品名称]"
        patterns = [
            r'购买了[：:]?\s*"([^"]+)"',
            r'购买了[：:]?\s*(\S+.*)',
            r'商品[：:]?\s*([^，,]+)',
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, message)
            if matches:
                return matches.group(1).strip()
        
        return None
    
    def _format_share_link(self, order: ProductOrder) -> str:
        """格式化网盘链接回复"""
        return (
            f"🎉 感谢购买「{order.product_name}」！\n\n"
            f"🔗 网盘链接：{order.share_url}\n"
            f"📝 提取码：`{order.share_code}`\n\n"
            f"点击链接保存到自己网盘即可下载使用。\n"
            f"如果链接打不开请检查网络，或复制完整链接打开浏览器访问。\n"
            f"遇到问题随时问我哦😊"
        )
        
    def add_custom_rule(self, keyword: str, reply: str, regex: bool = False):
        """添加自定义回复规则"""
        self.reply_rules.append(AutoReplyRule(
            keyword=keyword,
            reply=reply,
            regex=regex
        ))
        
    def remove_rule(self, keyword: str) -> bool:
        """删除规则"""
        for i, rule in enumerate(self.reply_rules):
            if rule.keyword == keyword:
                del self.reply_rules[i]
                return True
        return False
