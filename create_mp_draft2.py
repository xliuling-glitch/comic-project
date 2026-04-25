#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json

# 直接写入配置
appid = "wx7f1a4b8074e9d5bd"
appsecret = "b852f7275fb5d4dff6b2ce00472ee637"

# 获取access_token
token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={appsecret}"
token_res = requests.get(token_url)
token_data = token_res.json()

if 'access_token' not in token_data:
    print(f"ERROR getting token: {json.dumps(token_data, indent=2, ensure_ascii=False)}")
    exit(1)

access_token = token_data['access_token']
print(f"Got access_token: {access_token[:8]}...")

# 文章内容
content = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>人人都在用AI，但有人越用越强，有人越用越废</title>
</head>
<body>

<h1>人人都在用AI，但有人越用越强，有人越用越废</h1>

<p>2026年，AI早就是基础设施了。</p>

<p>别再沉迷一键生成的虚幻快感里。现实业务的修罗场里，工具链平权带来了极其残酷的两极分化，<strong>同样是调用同一个模型，有人彻底解放双手，一个人活成一支全栈团队；有人却沦为低级提示词打字员，每天被不可控的生成结果反复折磨。</strong></p>

<p>为什么会越用越废？</p>

<p>因为弱者把AI当老虎机，靠投币（模糊提示词）赌概率；而强者把AI当编译器，用结构化的工程思维锁定确定性。</p>

<p>放弃对AI的浪漫主义幻想吧，这篇文章不讲趋势，只讲实战。以下是真正拉开差距的三个核心工作流，以及底层逻辑。</p>

<br>
<hr>
<br>

<h2>一、 放弃开盲盒，建立绝对的控制权</h2>

<p>越用越废的典型症状是什么？把极其模糊的需求扔给大模型，比如帮我写个爆款脚本，画个小男孩，然后疯狂点击重新生成，祈祷奇迹出现。</p>

<p>这不叫工作，这叫求神拜佛。</p>

<p>高手的核心能力，是<strong>降维与锁定</strong>。AI的本质是概率模型，你要做的，就是通过工程化的指令，把概率坍缩为百分之百的确定性。</p>

<p>说到这里，举个实操拆解，视觉资产的一致性锁定。</p>

<p>在影视分镜、电商视觉或者IP孵化里，角色和画面的连贯性是生死线。不要用自然语言去描述感觉，要用参数化的Trigger Words，也就是触发词，建立底层视觉框架。</p>

<p>错误示范，</p>

<blockquote><p>"画一个聪明的10岁小男孩，像个小侦探，有点黑客的感觉。"</p></blockquote>

<p>废话太多，变量完全不可控，你拿到十次会有十个完全不同的人。</p>

<p>正确示范，这是开箱即用的底层逻辑代码块，</p>

<pre>
// 全局一致性特征词 (Trigger Words) 必须置于Prompt首部
same character, consistent face, 10-year-old Chinese boy, round face, bright intelligent eyes, slightly messy black short hair, black thin rectangular glasses, small and thin body, thoughtful expression
</pre>

<p>通过这种标准化前置，无论是生成日常场景（Casual T-shirt）还是特定业务形态（Detective vest），底层的面部与体型骨架都将高度统一。</p>

<p>这种能力，才是你的业务护城河。</p>

<br>

<h2>二、 复杂系统的降维打击：模块化拆解</h2>

<p>不要让AI直接干造房子的活，它大概率会给你一个外表华丽但会漏水的纸板房。面对复杂系统搭建，比如剧情策划、商业闭环、代码架构，必须按模块进行拆解。</p>

<p>外行看热闹，内行看门道。外行扔给AI的需求是写个好故事；内行的操作是构建<strong>世界观 → 角色卡 → 规则逻辑 → 场景渲染</strong>的数据库。</p>

<p>我给你看一个业务文案或脚本的工程化生成SOP，你拿去就能用。</p>

<p>不要让AI做开放式续写，必须给它输入带有极强限制条件的JSON或Markdown结构。</p>

<p><strong>第一步：注入角色基础参数与价值观，限制AI的发散边界</strong></p>

<p>把业务背景转化为角色卡。比如，你需要生成一篇针对职场人的AI工具推广软文，你得先设定对话实体的颗粒度：</p>

<pre>
# 角色卡设定：阿杰
- **身份**：电商视觉设计师 / 企业AI落地负责人
- **核心价值观**：技术改变生活，坚信AI能解放打工人的双手，用最低的能量消耗换取最高效的产出，高效摸鱼。
- **行为逻辑**：极简、务实、拒绝形式主义。
</pre>

<p><strong>第二步：注入领域知识</strong></p>

<p>AI没有审美，只有算力。你的审美和行业认知才是真正的门槛。在生成分镜头脚本时，必须强制AI遵循你的专业规则：</p>

<blockquote>
<p>执行指令：<br>
基于上述角色卡，生成一段产品演示分镜。<br>
强制约束：<br>
1. 画面节奏必须遵循快慢对比、动静结合。<br>
2. 严禁使用全景到底，必须包含特写，比如老白敲击键盘的局部特写、屏幕代码运行的高对比度反光。<br>
3. 用画面讲故事，严禁在旁白中出现多余的解释性废话。</p>
</blockquote>

<p>通过参数化设定加强约束规则，你拿到的才是可以直接落地的商业级交付物，而不是充满AI味的机械套话。</p>

<br>

<h2>三、 从手工作坊，到自动化流水线</h2>

<p>如果你还在网页端一次次复制粘贴提示词，你的效率天花板其实已经注定了。真正的越用越强，是剥离重复劳动，将AI能力深度绑定到本地的API工作流中。</p>

<p>说个最常见的实战，Python + API 的批量处理脚本。面对海量的数据清洗、文案批量生成或多语种翻译，直接上代码。这是一个标准的并发处理框架，贴合现代AI辅助编程工具的最佳实践。</p>

<pre>
import asyncio
import aiohttp
import json

# 配置项：极简配置，开箱即用
API_KEY = "your_api_key_here"
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4-turbo"

# 你的标准化Prompt模板
SYSTEM_PROMPT = """
你是一个实战驱动的技术与业务效率搭档。
保持极简、务实。彻底省略所有客套话。
直接输出最终的Markdown格式结果，不要解释。
"""

async def fetch_ai_response(session, task_data):
 # 单次API调用模块
 headers = {
 "Authorization": f"Bearer {API_KEY}",
 "Content-Type": "application/json"
 }
 payload = {
 "model": MODEL,
 "messages": [
 {"role": "system", "content": SYSTEM_PROMPT},
 {"role": "user", "content": task_data}
 ],
 "temperature": 0.2 # 极低温度，保证业务逻辑的确定性
 }
 
 try:
 async with session.post(API_URL, headers=headers, json=payload) as response:
 res = await response.json()
 return res['choices'][0]['message']['content']
 except Exception as e:
 return f"Error: {str(e)}"

async def main(task_list):
 # 并发执行工作流
 async with aiohttp.ClientSession() as session:
 tasks = [fetch_ai_response(session, task) for task in task_list]
 # 并发执行，解放双手
 results = await asyncio.gather(*tasks)
 
 for idx, res in enumerate(results):
 print(f"--- Task {idx+1} Result ---")
 print(res)

if __name__ == "__main__":
 # 业务数据源
 business_tasks = [
 "提取竞品分析报告A的核心转化逻辑",
 "提取竞品分析报告B的核心转化逻辑",
 "提取竞品分析报告C的核心转化逻辑"
 ]
 # 异步执行
 asyncio.run(main(business_tasks))
</pre>

<p>说到这里，顺便给你一套系统排查指南，这都是API调用常见的坑：</p>

<ol>
<li><strong>并发限制</strong>：大批量请求极易触发HTTP 429错误。排查方案，在 <code>fetch_ai_response</code> 中引入 <code>asyncio.sleep()</code> 或使用指数退避算法。</li>
<li><strong>上下文溢出</strong>：处理长文本前，必须在本地先用分词库，比如 <code>tiktoken</code>，计算长度。超过限制需要按Token切割，分段输入。</li>
<li><strong>网络阻断</strong>：国内环境直连API常遇超时。排查方案，确保执行环境的全局代理配置正确，或修改代码注入 <code>proxy="http://127.0.0.1:port"</code>。</li>
</ol>

<br>
<hr>
<br>

<h2>终局：你的不可替代性究竟在哪？</h2>

<p>AI是一个无底洞，它能轻易抹平初级执行者的技能差异。当你发现你的同事只用五分钟就能产出一篇看似严谨的报告、一段完整的代码、一套炫酷的UI设计时，不要恐慌。</p>

<p>因为一个项目越没有障碍，越容易变成红海。在所有人都拥有生成能力的时代，竞争的维度已经发生了转移。</p>

<p><strong>强者越强的秘密，在于构建超我生意和深层壁垒：</strong></p>

<ol>
<li><p><strong>认知与审美的壁垒</strong>：AI可以生成代码和图像，但它无法判断什么是赛博朋克极简风，什么是高对比度带来的视觉压迫感。你的品味，你对画面节奏，就是快慢对比、音效粘合这些东西的精准把控，是你指挥AI的最高准则。内行叫好的东西不一定赚钱，但能让你建立起降维打击的审美高地。</p></li>

<li><p><strong>行业第一性原理</strong>：不管是编剧里的支付体系与转交系统，还是商业中的流量逻辑，你不懂底层规律，AI就只能给你一堆正确的废话。</p></li>

<li><p><strong>架构能力</strong>：你不再是一个具体的程序员、剪辑师或文案，你是一个系统的架构师。你负责定义问题、设定规则、拆解模块、把控最终的交付质量。</p></li>
</ol>

<p>扔掉那些每天教你一百个神级Prompt的速成垃圾。不要去记套路，去建立你的工作流。把AI当作你的外接大脑，和无休止运转的执行服务器。</p>

<p>掌握它，控制它，然后，去享受你应得的高阶效率与自由。</p>

<br>

<p>---</p>

<p>以上，既然看到这里了，如果觉得不错，随手点个赞、在看、转发三连吧，如果想第一时间收到推送，也可以给我个星标⭐～</p>

<p>谢谢你看我的文章，我们，下次再见。</p>

</body>
</html>
'''

draft_data = {
    "articles": [
        {
            "title": "人人都在用AI，但有人越用越强，有人越用越废",
            "author": "卡兹克",
            "digest": "别再沉迷一键生成的虚幻快感。同样是AI，有人彻底解放双手，有人沦为提示词打字员。拉开差距的三个核心工作流。",
            "content": content,
            "thumb_media_id": None,
        }
    ]
}

create_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
headers = {"Content-Type": "application/json"}
create_res = requests.post(create_url, json=draft_data, headers=headers)
create_data = create_res.json()

print(f"Response: {json.dumps(create_data, indent=2, ensure_ascii=False)}")

if create_data.get('errcode', 0) != 0:
    print(f"ERROR: {create_data.get('errmsg')}")
    exit(1)

media_id = create_data.get('media_id')
print(f"\n✅ Draft created successfully!")
print(f"media_id: {media_id}")
