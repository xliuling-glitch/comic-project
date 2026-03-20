#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信智能机器人 - WebSocket 长连接客户端
支持消息接收、流式回复、主动推送等功能
"""

import asyncio
import json
import logging
import uuid
import time
from typing import Optional, Callable, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('WeComBot')


class WeComBot:
    """企业微信智能机器人长连接客户端"""
    
    def __init__(self, config_path: str = 'config.json'):
        """
        初始化机器人
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_callback: Optional[Callable] = None
        self._event_callback: Optional[Callable] = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    async def connect(self) -> bool:
        """
        建立 WebSocket 连接并订阅
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 建立 WebSocket 连接
            logger.info(f"正在连接到 {self.config['websocket_url']}...")
            self.ws = await websockets.connect(
                self.config['websocket_url'],
                ping_interval=None,  # 禁用自动 ping，使用自定义心跳
                ping_timeout=None
            )
            logger.info("WebSocket 连接已建立")
            
            # 发送订阅请求进行身份校验
            subscribe_success = await self._subscribe()
            if not subscribe_success:
                logger.error("订阅失败，关闭连接")
                await self.ws.close()
                return False
            
            self.connected = True
            logger.info("订阅成功，长连接已建立")
            return True
            
        except Exception as e:
            logger.error(f"连接失败：{e}")
            return False
    
    async def _subscribe(self) -> bool:
        """
        发送订阅请求
        
        Returns:
            bool: 订阅是否成功
        """
        req_id = str(uuid.uuid4())
        subscribe_msg = {
            "cmd": "aibot_subscribe",
            "headers": {
                "req_id": req_id
            },
            "body": {
                "bot_id": self.config['bot_id'],
                "secret": self.config['secret']
            }
        }
        
        await self.ws.send(json.dumps(subscribe_msg))
        logger.info("已发送订阅请求")
        
        # 等待订阅响应
        try:
            response = await asyncio.wait_for(self.ws.recv(), timeout=10)
            resp_data = json.loads(response)
            
            if resp_data.get('errcode') == 0:
                logger.info("订阅成功")
                return True
            else:
                logger.error(f"订阅失败：{resp_data.get('errmsg')}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("订阅响应超时")
            return False
    
    async def _heartbeat_loop(self):
        """心跳保活循环"""
        interval = self.config.get('heartbeat_interval', 30)
        while self._running and self.connected:
            try:
                await asyncio.sleep(interval)
                if self.connected and self.ws:
                    await self._send_heartbeat()
            except Exception as e:
                logger.error(f"心跳发送失败：{e}")
                break
    
    async def _send_heartbeat(self):
        """发送心跳"""
        req_id = str(uuid.uuid4())
        heartbeat_msg = {
            "cmd": "ping",
            "headers": {
                "req_id": req_id
            }
        }
        await self.ws.send(json.dumps(heartbeat_msg))
        logger.debug("心跳已发送")
    
    async def _receive_loop(self):
        """接收消息循环"""
        while self._running and self.connected:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                await self._handle_message(data)
            except ConnectionClosed:
                logger.warning("连接已关闭")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"接收消息异常：{e}")
                break
    
    async def _handle_message(self, data: Dict[str, Any]):
        """
        处理接收到的消息
        
        Args:
            data: 消息数据
        """
        cmd = data.get('cmd')
        
        if cmd == 'aibot_msg_callback':
            # 消息回调
            logger.info(f"收到消息回调：{data.get('body', {}).get('msgtype')}")
            if self._message_callback:
                await self._invoke_callback(self._message_callback, data)
                
        elif cmd == 'aibot_event_callback':
            # 事件回调
            event_type = data.get('body', {}).get('event', {}).get('eventtype')
            logger.info(f"收到事件回调：{event_type}")
            if self._event_callback:
                await self._invoke_callback(self._event_callback, data)
                
        elif cmd == 'ping':
            # 心跳响应，忽略
            pass
            
        else:
            logger.debug(f"收到未知命令：{cmd}")
    
    async def _invoke_callback(self, callback: Callable, data: Dict[str, Any]):
        """调用回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"回调执行异常：{e}")
    
    def on_message(self, callback: Callable):
        """
        注册消息回调
        
        Args:
            callback: 回调函数，接收消息数据
        """
        self._message_callback = callback
        logger.info("消息回调已注册")
    
    def on_event(self, callback: Callable):
        """
        注册事件回调
        
        Args:
            callback: 回调函数，接收事件数据
        """
        self._event_callback = callback
        logger.info("事件回调已注册")
    
    async def respond_msg(self, req_id: str, msg_data: Dict[str, Any]) -> bool:
        """
        回复消息
        
        Args:
            req_id: 消息回调中的 req_id
            msg_data: 消息内容，包含 msgtype 和对应内容
            
        Returns:
            bool: 发送是否成功
        """
        msg = {
            "cmd": "aibot_respond_msg",
            "headers": {
                "req_id": req_id
            },
            "body": msg_data
        }
        return await self._send_command(msg)
    
    async def respond_welcome_msg(self, req_id: str, msg_data: Dict[str, Any]) -> bool:
        """
        回复欢迎语（仅用于 enter_chat 事件）
        
        Args:
            req_id: 事件回调中的 req_id
            msg_data: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        msg = {
            "cmd": "aibot_respond_welcome_msg",
            "headers": {
                "req_id": req_id
            },
            "body": msg_data
        }
        return await self._send_command(msg)
    
    async def respond_update_msg(self, req_id: str, msg_data: Dict[str, Any]) -> bool:
        """
        更新模板卡片（仅用于 template_card_event 事件）
        
        Args:
            req_id: 事件回调中的 req_id
            msg_data: 卡片内容
            
        Returns:
            bool: 发送是否成功
        """
        msg = {
            "cmd": "aibot_respond_update_msg",
            "headers": {
                "req_id": req_id
            },
            "body": msg_data
        }
        return await self._send_command(msg)
    
    async def send_msg(self, chat_id: str, chat_type: int, msg_data: Dict[str, Any]) -> bool:
        """
        主动推送消息
        
        Args:
            chat_id: 会话 ID（单聊为用户 userid，群聊为 chatid）
            chat_type: 会话类型 1=单聊，2=群聊
            msg_data: 消息内容
            
        Returns:
            bool: 发送是否成功
        """
        msg = {
            "cmd": "aibot_send_msg",
            "headers": {
                "req_id": str(uuid.uuid4())
            },
            "body": {
                "chatid": chat_id,
                "chat_type": chat_type,
                **msg_data
            }
        }
        return await self._send_command(msg)
    
    async def upload_media_init(self, file_type: str, filename: str, 
                                 total_size: int, total_chunks: int,
                                 md5: Optional[str] = None) -> Optional[str]:
        """
        初始化素材上传
        
        Args:
            file_type: 文件类型 file/image/voice/video
            filename: 文件名
            total_size: 文件总大小
            total_chunks: 分片数量
            md5: 文件 MD5（可选）
            
        Returns:
            upload_id 或 None
        """
        msg = {
            "cmd": "aibot_upload_media_init",
            "headers": {
                "req_id": str(uuid.uuid4())
            },
            "body": {
                "type": file_type,
                "filename": filename,
                "total_size": total_size,
                "total_chunks": total_chunks
            }
        }
        if md5:
            msg["body"]["md5"] = md5
            
        response = await self._send_command_with_response(msg)
        if response and response.get('errcode') == 0:
            return response.get('body', {}).get('upload_id')
        return None
    
    async def upload_media_chunk(self, upload_id: str, chunk_index: int, 
                                  base64_data: str) -> bool:
        """
        上传分片
        
        Args:
            upload_id: 上传 ID
            chunk_index: 分片索引（从 0 开始）
            base64_data: Base64 编码的分片数据
            
        Returns:
            bool: 上传是否成功
        """
        msg = {
            "cmd": "aibot_upload_media_chunk",
            "headers": {
                "req_id": str(uuid.uuid4())
            },
            "body": {
                "upload_id": upload_id,
                "chunk_index": chunk_index,
                "base64_data": base64_data
            }
        }
        return await self._send_command(msg)
    
    async def upload_media_finish(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """
        完成上传
        
        Args:
            upload_id: 上传 ID
            
        Returns:
            包含 media_id 的响应数据或 None
        """
        msg = {
            "cmd": "aibot_upload_media_finish",
            "headers": {
                "req_id": str(uuid.uuid4())
            },
            "body": {
                "upload_id": upload_id
            }
        }
        response = await self._send_command_with_response(msg)
        if response and response.get('errcode') == 0:
            return response.get('body', {})
        return None
    
    async def _send_command(self, msg: Dict[str, Any]) -> bool:
        """发送命令（不等待响应）"""
        try:
            if self.ws and self.connected:
                await self.ws.send(json.dumps(msg))
                return True
        except Exception as e:
            logger.error(f"发送命令失败：{e}")
        return False
    
    async def _send_command_with_response(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送命令并等待响应"""
        try:
            if self.ws and self.connected:
                req_id = msg['headers']['req_id']
                await self.ws.send(json.dumps(msg))
                
                # 等待响应（带超时）
                response = await asyncio.wait_for(self.ws.recv(), timeout=10)
                resp_data = json.loads(response)
                
                # 验证 req_id 匹配
                if resp_data.get('headers', {}).get('req_id') == req_id:
                    return resp_data
                else:
                    logger.warning("响应 req_id 不匹配")
                    return resp_data
        except asyncio.TimeoutError:
            logger.error("命令响应超时")
        except Exception as e:
            logger.error(f"发送命令失败：{e}")
        return None
    
    async def run(self):
        """启动机器人主循环"""
        self._running = True
        
        while self._running:
            try:
                # 建立连接
                if not await self.connect():
                    logger.warning("连接失败，准备重连...")
                    await asyncio.sleep(self.config.get('reconnect_delay', 5))
                    continue
                
                # 启动心跳任务
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # 进入接收循环
                await self._receive_loop()
                
            except Exception as e:
                logger.error(f"运行异常：{e}")
                self.connected = False
                
            # 重连逻辑
            if self._running and not self.connected:
                logger.info(f"{self.config.get('reconnect_delay', 5)} 秒后尝试重连...")
                await asyncio.sleep(self.config.get('reconnect_delay', 5))
    
    async def stop(self):
        """停止机器人"""
        logger.info("正在停止机器人...")
        self._running = False
        self.connected = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self.ws:
            await self.ws.close()
        
        logger.info("机器人已停止")


# ============== 使用示例 ==============

async def main():
    """示例：如何使用 WeComBot"""
    
    # 创建机器人实例
    bot = WeComBot('config.json')
    
    # 注册消息回调
    @bot.on_message
    async def handle_message(data):
        body = data.get('body', {})
        msgtype = body.get('msgtype')
        req_id = data.get('headers', {}).get('req_id')
        
        if msgtype == 'text':
            content = body.get('text', {}).get('content', '')
            print(f"收到文本消息：{content}")
            
            # 流式回复示例
            stream_id = str(uuid.uuid4())
            
            # 第一段
            await bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": False,
                    "content": "正在为您处理..."
                }
            })
            
            # 第二段（完成）
            await bot.respond_msg(req_id, {
                "msgtype": "stream",
                "stream": {
                    "id": stream_id,
                    "finish": True,
                    "content": "处理完成！有什么可以帮您的吗？"
                }
            })
    
    # 注册事件回调
    @bot.on_event
    async def handle_event(data):
        body = data.get('body', {})
        event_type = body.get('event', {}).get('eventtype')
        req_id = data.get('headers', {}).get('req_id')
        
        if event_type == 'enter_chat':
            print("用户进入会话")
            # 回复欢迎语
            await bot.respond_welcome_msg(req_id, {
                "msgtype": "text",
                "text": {
                    "content": "您好！我是智能助手，有什么可以帮您的吗？"
                }
            })
    
    # 启动机器人
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
