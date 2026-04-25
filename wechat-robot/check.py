#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io, json, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("企业微信机器人诊断")
print("=" * 60)

# 配置
config_path = 'config.json'
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"[OK] 配置文件存在")
    print(f"BotID: {config.get('bot_id', 'MISSING')[:15]}...")
    print(f"Secret: {config.get('secret', 'MISSING')[:15]}...")
else:
    print(f"[FAIL] 配置文件不存在")
    sys.exit(1)

# 依赖
try:
    import websockets
    print(f"[OK] websockets 已安装")
except:
    print(f"[FAIL] websockets 未安装")

try:
    import dashscope
    print(f"[OK] dashscope 已安装")
except:
    print(f"[FAIL] dashscope 未安装")

# API 测试
try:
    from dashscope import Generation
    r = Generation.call(model='qwen-turbo', messages=[{'role':'user','content':'hi'}])
    if r.status_code == 200:
        print(f"[OK] DashScope API 正常")
    else:
        print(f"[WARN] API 返回：{r.code}")
except Exception as e:
    print(f"[FAIL] API 错误：{e}")

# WebSocket 测试
import asyncio
async def test():
    try:
        ws = await websockets.connect(config.get('websocket_url'), timeout=10)
        await ws.close()
        print(f"[OK] WebSocket 可连接")
    except Exception as e:
        print(f"[FAIL] WebSocket: {e}")
asyncio.run(test())

print("\n" + "=" * 60)
print("检查清单:")
print("1. 企业微信后台 -> 智能机器人 -> API 模式 -> 长连接")
print("2. BotID 和 Secret 必须完全匹配")
print("3. 机器人必须被添加到群聊或用户关注")
print("4. 同一个机器人只能有一个长连接")
print("=" * 60)
