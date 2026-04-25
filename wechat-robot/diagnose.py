#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信机器人 - 快速诊断工具
检查配置、连接、权限等
"""

import json
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("企业微信机器人 - 诊断工具")
print("=" * 60)

# 1. 检查配置文件
print("\n[1] 检查配置文件...")
config_path = 'config.json'
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"   ✅ 配置文件存在")
    print(f"   BotID: {config.get('bot_id', '❌ 缺失')[:15]}...")
    print(f"   Secret: {config.get('secret', '❌ 缺失')[:15]}...")
    print(f"   WebSocket: {config.get('websocket_url', '❌ 缺失')}")
else:
    print(f"   ❌ 配置文件不存在：{config_path}")
    sys.exit(1)

# 2. 检查依赖
print("\n[2] 检查 Python 依赖...")
try:
    import websockets
    print(f"   ✅ websockets {websockets.__version__}")
except ImportError:
    print(f"   ❌ websockets 未安装")
    print(f"      运行：pip install websockets")

try:
    import dashscope
    print(f"   ✅ dashscope {dashscope.__version__}")
except ImportError:
    print(f"   ❌ dashscope 未安装")
    print(f"      运行：pip install dashscope")

# 3. 测试 API Key
print("\n[3] 测试 DashScope API...")
api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-7f7f842149384a0eb6d5b5b83bb682e0')
try:
    from dashscope import Generation
    response = Generation.call(
        model='qwen-turbo',
        messages=[{'role': 'user', 'content': 'hi'}],
        api_key=api_key
    )
    if response.status_code == 200:
        print(f"   ✅ API 调用成功")
    else:
        print(f"   ⚠️ API 返回错误：{response.code} - {response.message}")
except Exception as e:
    print(f"   ❌ API 调用失败：{e}")

# 4. 检查企业微信配置
print("\n[4] 企业微信后台配置检查清单")
print("""
   请登录 https://work.weixin.qq.com/ 检查：
   
   □ 1. 进入「应用管理」→「智能机器人」
   □ 2. 选择你的机器人
   □ 3. 开启「API 模式」
   □ 4. 选择「长连接」方式（不是「接收消息 URL」）
   □ 5. 确认 BotID 和 Secret 与 config.json 一致
   □ 6. 机器人已添加到群聊或已关注
   
   ⚠️ 常见问题：
   - 模式选错：必须选「长连接」，不能选「接收消息 URL」
   - 凭证错误：BotID 和 Secret 必须完全一致（区分大小写）
   - 权限问题：机器人需要被添加到群聊或用户关注
   - 多个连接：同一个机器人只能有一个长连接
""")

# 5. 网络测试
print("\n[5] 测试 WebSocket 连接...")
import asyncio
import websockets

async def test_ws():
    try:
        ws = await websockets.connect(
            config.get('websocket_url'),
            timeout=10
        )
        await ws.close()
        print(f"   ✅ WebSocket 连接成功")
        return True
    except Exception as e:
        print(f"   ❌ WebSocket 连接失败：{e}")
        return False

asyncio.run(test_ws())

# 6. 下一步操作
print("\n" + "=" * 60)
print("[6] 下一步操作")
print("=" * 60)
print("""
1. 确认企业微信后台配置正确（见第 4 步）

2. 重启机器人：
   python debug_bot.py

3. 在企业微信中：
   - 找到机器人所在的群聊
   - @机器人 或发送消息
   - 如果是单聊，先发送一条消息

4. 查看日志：
   如果还是没反应，查看 debug_bot.py 的输出

5. 检查机器人状态：
   - 机器人是否被禁用？
   - 机器人是否在正确的企业？
   - 用户是否有权限和机器人聊天？
""")

print("=" * 60)
