#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 + MCP 工具集成
支持：创建文档、智能表格、发送消息等
"""

import asyncio
import json
import uuid
import os
import sys
import logging
import dashscope
from dashscope import Generation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wecom_bot import WeComBot

# 配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MCPBot')
dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')

# MCP 工具定义
MCP_TOOLS = {
    "create_doc": {
        "name": "create_doc",
        "description": "创建企业微信文档",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "文档标题"},
                "content": {"type": "string", "description": "文档内容"}
            },
            "required": ["title"]
        }
    },
    "create_sheet": {
        "name": "create_sheet",
        "description": "创建智能表格",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "表格名称"},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "列名列表"}
            },
            "required": ["name"]
        }
    },
    "send_message": {
        "name": "send_message",
        "description": "发送企业微信消息",
        "parameters": {
            "type": "object",
            "properties": {
                "userid": {"type": "string", "description": "接收者 userid"},
                "content": {"type": "string", "description": "消息内容"}
            },
            "required": ["userid", "content"]
        }
    }
}

# 系统提示词 - 让 AI 知道可以使用工具
SYSTEM_PROMPT = """你是一个智能助手，可以调用工具帮助用户完成任务。

可用工具：
1. create_doc(title, content) - 创建企业微信文档
2. create_sheet(name, columns) - 创建智能表格
3. send_message(userid, content) - 发送消息

当用户需要创建文档、表格或发送消息时，请使用对应的工具。
回复格式：
- 普通对话：直接回复
- 调用工具：使用 JSON 格式 {"tool": "工具名", "params": {参数}}

示例：
用户：帮我创建一个周报文档
你：{"tool": "create_doc", "params": {"title": "周报", "content": ""}}

用户：创建一个任务跟踪表格
你：{"tool": "create_sheet", "params": {"name": "任务跟踪", "columns": ["任务", "负责人", "状态", "截止日期"]}}
"""

bot = WeComBot('config.json')

# 模拟 MCP 工具执行（实际使用时替换为真实 API）
async def execute_tool(tool_name: str, params: dict) -> dict:
    """执行 MCP 工具"""
    logger.info(f"执行工具：{tool_name}, 参数：{params}")
    
    if tool_name == 'create_doc':
        # TODO: 调用企业微信文档 API
        # await call_wecom_doc_api(...)
        return {
            "success": True,
            "doc_id": "doc_" + str(uuid.uuid4())[:8],
            "url": f"https://doc.work.weixin.qq.com/doc/{uuid.uuid4()}"
        }
        
    elif tool_name == 'create_sheet':
        # TODO: 调用企业微信表格 API
        return {
            "success": True,
            "sheet_id": "sheet_" + str(uuid.uuid4())[:8],
            "url": f"https://sheet.work.weixin.qq.com/sheet/{uuid.uuid4()}"
        }
        
    elif tool_name == 'send_message':
        # TODO: 调用企业微信消息 API
        return {
            "success": True,
            "message": "消息已发送"
        }
    
    return {"success": False, "error": "未知工具"}

@bot.on_message
async def on_message(data):
    body = data.get('body', {})
    req_id = data.get('headers', {}).get('req_id')
    content = body.get('text', {}).get('content', '')
    from_userid = body.get('from', {}).get('userid', 'unknown')
    
    logger.info(f"收到消息 from {from_userid}: {content}")
    
    try:
        # 调用 AI（带工具定义）
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': content}
        ]
        
        logger.info("正在调用 AI...")
        response = Generation.call(
            model='qwen-plus',
            messages=messages
        )
        
        if response.status_code == 200:
            reply = response.output.get('text', '')
            logger.info(f"AI 回复：{reply[:100]}...")
            
            # 检查是否是工具调用
            if reply.strip().startswith('{'):
                try:
                    tool_call = json.loads(reply.strip())
                    if 'tool' in tool_call and 'params' in tool_call:
                        # 执行工具
                        result = await execute_tool(tool_call['tool'], tool_call['params'])
                        
                        # 回复用户工具执行结果
                        if result.get('success'):
                            final_reply = f"✅ {tool_call['tool']} 执行成功！\n\n结果：{json.dumps(result, indent=2, ensure_ascii=False)}"
                        else:
                            final_reply = f"❌ 工具执行失败：{result.get('error')}"
                        
                        await bot.respond_msg(req_id, {
                            "msgtype": "text",
                            "text": {"content": final_reply}
                        })
                        return
                except json.JSONDecodeError:
                    pass  # 不是 JSON，直接回复
            
            # 普通回复
            await bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": reply}
            })
        else:
            logger.error(f"API 错误：{response.code} - {response.message}")
            await bot.respond_msg(req_id, {
                "msgtype": "text",
                "text": {"content": f"API 错误：{response.code}"}
            })
    except Exception as e:
        logger.error(f"处理异常：{e}", exc_info=True)
        await bot.respond_msg(req_id, {
            "msgtype": "text",
            "text": {"content": f"错误：{str(e)}"}
        })

@bot.on_event
async def on_event(data):
    event_type = data.get('body', {}).get('event', {}).get('eventtype')
    req_id = data.get('headers', {}).get('req_id')
    logger.info(f"收到事件：{event_type}")
    
    if event_type == 'enter_chat':
        welcome = """👋 你好！我是智能助手～

我可以帮你：
- 📝 创建文档
- 📊 创建智能表格
- 💬 发送消息
- 🔧 执行各种工具

试试对我说：
"帮我创建一个周报文档"
"创建一个任务跟踪表格"
"""
        await bot.respond_welcome_msg(req_id, {
            "msgtype": "text",
            "text": {"content": welcome}
        })

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("企业微信机器人 + MCP 工具")
    logger.info("=" * 50)
    asyncio.run(bot.run())
