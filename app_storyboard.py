# -*- coding: utf-8 -*-
"""
AI 分镜头视频创作工具
功能：
1. 导入文案/音频/字幕
2. 智能生成分镜头脚本
3. 单镜头模式：从素材库挑选视频片段匹配分镜头
4. 多镜头模式：多镜头匹配同一时间戳，自动切换
"""

import gradio as gr
import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

# ============== 数据模型 ==============

@dataclass
class StoryboardShot:
    """分镜头数据"""
    id: int
    start_time: float  # 秒
    end_time: float    # 秒
    duration: float    # 秒
    text: str          # 文案/字幕
    audio_path: str = ""
    video_clips: List[Dict] = None  # 视频片段列表
    
    def __post_init__(self):
        if self.video_clips is None:
            self.video_clips = []
    
    @property
    def duration_str(self):
        m, s = divmod(int(self.duration), 60)
        return f"{m:02d}:{s:02d}"

@dataclass
class VideoClip:
    """视频片段"""
    id: str
    path: str
    name: str
    duration: float
    start_trim: float = 0.0
    end_trim: float = 0.0
    
    @property
    def trimmed_duration(self):
        return self.end_trim - self.start_trim if self.end_trim > self.start_trim else self.duration

# ============== 全局状态 ==============

temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
output_dir = os.path.join(os.path.dirname(__file__), 'output')
assets_dir = os.path.join(os.path.dirname(__file__), 'assets')

for d in [temp_dir, output_dir, assets_dir]:
    os.makedirs(d, exist_ok=True)

# 会话状态
session_state = {
    'storyboard': [],
    'video_library': [],
    'audio_path': None,
    'script_text': '',
    'mode': 'single',  # 'single' or 'multi'
}

# ============== 核心功能 ==============

def parse_script_to_storyboard(script_text: str, audio_path: str = None) -> List[Dict]:
    """解析文案生成分镜头"""
    if not script_text:
        return []
    
    shots = []
    lines = [l.strip() for l in script_text.split('\n') if l.strip()]
    
    # 估算每行时长（按中文每秒 4 字计算）
    for i, line in enumerate(lines):
        duration = max(2.0, len(line) / 4.0)  # 至少 2 秒
        shots.append({
            'id': i + 1,
            'start_time': sum(s['duration'] for s in shots),
            'end_time': sum(s['duration'] for s in shots) + duration,
            'duration': duration,
            'text': line,
            'audio_path': audio_path or '',
            'video_clips': []
        })
    
    return shots

def upload_audio(audio_file) -> str:
    """上传音频文件"""
    if not audio_file:
        return None
    
    if isinstance(audio_file, str):
        return audio_file
    
    # 复制音频到临时目录
    src = audio_file if isinstance(audio_file, str) else audio_file.name
    dst = os.path.join(temp_dir, f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    shutil.copy2(src, dst)
    return dst

def upload_video_library(files) -> List[Dict]:
    """上传视频素材库"""
    if not files:
        return []
    
    clips = []
    file_list = files if isinstance(files, list) else [files]
    
    for i, f in enumerate(file_list):
        src = f if isinstance(f, str) else f.name
        name = os.path.basename(src)
        dst = os.path.join(assets_dir, f"clip_{i}_{name}")
        
        try:
            shutil.copy2(src, dst)
            # 简单估算时长（实际应使用 moviepy 获取真实时长）
            duration = 30.0  # 默认 30 秒
            
            clips.append({
                'id': f"clip_{i}",
                'path': dst,
                'name': name,
                'duration': duration,
                'start_trim': 0.0,
                'end_trim': duration
            })
        except Exception as e:
            print(f"复制视频失败：{e}")
    
    return clips

def generate_storyboard(script: str, audio: str) -> str:
    """生成分镜头脚本"""
    shots = parse_script_to_storyboard(script, audio)
    session_state['storyboard'] = shots
    
    if not shots:
        return "❌ 请输入文案内容"
    
    # 生成预览文本
    preview = f"✅ 已生成 {len(shots)} 个分镜头\n\n"
    preview += "=" * 50 + "\n"
    
    for shot in shots:
        preview += f"📷 镜头 {shot['id']:02d} | ⏱ {shot['duration']:.1f}s | 📝 {shot['text'][:30]}...\n"
    
    preview += "=" * 50
    return preview

def get_storyboard_table(shots: List[Dict]) -> List[List]:
    """分镜头表格数据"""
    table = []
    for shot in shots:
        clip_count = len(shot.get('video_clips', []))
        table.append([
            shot['id'],
            f"{shot['duration']:.1f}s",
            shot['text'],
            f"🎬 {clip_count}个片段" if clip_count > 0 else "⚠️ 未匹配"
        ])
    return table

def assign_video_to_shot(shot_id: int, video_clip: Dict, mode: str) -> List[Dict]:
    """为分镜头分配视频片段"""
    shots = session_state['storyboard']
    
    for shot in shots:
        if shot['id'] == shot_id:
            if mode == 'single':
                # 单镜头模式：替换
                shot['video_clips'] = [video_clip] if video_clip else []
            else:
                # 多镜头模式：添加
                if video_clip and video_clip not in shot['video_clips']:
                    shot['video_clips'].append(video_clip)
            break
    
    session_state['storyboard'] = shots
    return shots

def render_final_video() -> str:
    """渲染最终视频"""
    shots = session_state['storyboard']
    
    if not shots:
        return "❌ 请先生成分镜头"
    
    # 检查所有镜头是否都有视频
    unassigned = [s['id'] for s in shots if not s.get('video_clips')]
    if unassigned:
        return f"❌ 以下镜头未分配视频：{', '.join(map(str, unassigned))}"
    
    # 生成输出路径
    output_path = os.path.join(output_dir, f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
    
    # 这里应该使用 moviepy 进行实际的视频处理
    # 简化版本：返回成功消息
    total_duration = sum(s['duration'] for s in shots)
    
    return f"""✅ 渲染完成！

📊 统计信息:
├─ 分镜头数量：{len(shots)}
├─ 总时长：{total_duration:.1f}秒
├─ 输出路径：{output_path}
└─ 模式：{'多镜头' if session_state['mode'] == 'multi' else '单镜头'}

⚠️ 注意：这是演示版本，实际视频合成需要 moviepy 处理。
"""

def clear_project():
    """清空项目"""
    session_state.update({
        'storyboard': [],
        'video_library': [],
        'audio_path': None,
        'script_text': '',
        'mode': 'single'
    })
    return None, None, "", "", [], None

# ============== UI 构建 ==============

def create_app():
    """创建应用界面"""
    
    with gr.Blocks(title="AI 分镜头视频创作工具", ) as demo:
        gr.Markdown("""
        # 🎬 AI 分镜头视频创作工具
        
        智能分镜头生成 | 单/多镜头模式 | 自动裁剪拼接
        """)
        
        # 顶部状态栏
        with gr.Row():
            status_box = gr.Textbox(label="📢 状态", interactive=False, scale=2)
            mode_radio = gr.Radio(
                choices=[('🎯 单镜头模式', 'single'), ('🎪 多镜头模式', 'multi')],
                value='single',
                label="拍摄模式",
                scale=1
            )
        
        with gr.Tabs():
            # ===== Tab 1: 素材导入 =====
            with gr.TabItem("📥 素材导入", id="tab_import"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📝 文案输入")
                        script_input = gr.Textbox(
                            label="文案内容",
                            placeholder="请输入视频文案，每行一个分镜头...",
                            lines=8
                        )
                        
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔊 音频上传")
                        audio_input = gr.Audio(
                            label="上传配音音频",
                            type="filepath"
                        )
                
                with gr.Row():
                    gr.Markdown("### 🎬 视频素材库")
                    video_library = gr.File(
                        label="上传视频素材（支持多选）",
                        file_count="multiple",
                        file_types=["video"]
                    )
                
                with gr.Row():
                    generate_btn = gr.Button("🚀 生成分镜头脚本", variant="primary", scale=1)
                    import_status = gr.Textbox(label="导入状态", interactive=False, scale=2)
            
            # ===== Tab 2: 分镜头编辑 =====
            with gr.TabItem("📋 分镜头编辑", id="tab_storyboard"):
                with gr.Row():
                    with gr.Column(scale=2):
                        storyboard_preview = gr.Textbox(
                            label="分镜头预览",
                            lines=6,
                            interactive=False
                        )
                        
                        storyboard_table = gr.Dataframe(
                            headers=["镜头 ID", "时长", "文案内容", "视频匹配"],
                            label="分镜头列表",
                            interactive=False
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 🎯 视频分配")
                        shot_id_input = gr.Number(label="镜头 ID", value=1, precision=0)
                        video_select = gr.Dropdown(
                            label="选择视频片段",
                            choices=[]
                        )
                        assign_btn = gr.Button("分配视频到镜头", variant="primary")
            
            # ===== Tab 3: 预览与渲染 =====
            with gr.TabItem("🎬 预览与渲染", id="tab_render"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 项目统计")
                        stats_box = gr.Textbox(
                            label="统计信息",
                            lines=8,
                            interactive=False
                        )
                        
                        render_btn = gr.Button("🎬 渲染最终视频", variant="primary")
                        clear_btn = gr.Button("🗑️ 清空项目", variant="stop")
                    
                    with gr.Column(scale=1):
                        render_status = gr.Textbox(
                            label="渲染状态",
                            lines=10,
                            interactive=False
                        )
                        final_video = gr.Video(label="最终视频预览")
        
        # ===== 事件绑定 =====
        
        # 生成分镜头
        generate_btn.click(
            fn=lambda s, a: (generate_storyboard(s, a), 
                            parse_script_to_storyboard(s, a),
                            f"✅ 文案：{len(s.split(chr(10)))}行 | 音频：{'已上传' if a else '未上传'}"),
            inputs=[script_input, audio_input],
            outputs=[storyboard_preview, storyboard_table, import_status]
        )
        
        # 上传视频库
        video_library.change(
            fn=lambda files: (upload_video_library(files), 
                             [f"{c['name']} ({c['duration']:.1f}s)" for c in upload_video_library(files)] if files else []),
            inputs=[video_library],
            outputs=[gr.State(), video_select]
        )
        
        # 分配视频
        assign_btn.click(
            fn=lambda sid, vid, mode: (assign_video_to_shot(int(sid), {'id': vid}, mode),
                                      get_storyboard_table(assign_video_to_shot(int(sid), {'id': vid}, mode))),
            inputs=[shot_id_input, video_select, mode_radio],
            outputs=[gr.State(), storyboard_table]
        )
        
        # 渲染
        render_btn.click(
            fn=render_final_video,
            outputs=[render_status]
        )
        
        # 清空
        clear_btn.click(
            fn=clear_project,
            outputs=[script_input, audio_input, storyboard_preview, import_status, storyboard_table, final_video]
        )
        
        # 模式切换更新
        mode_radio.change(
            fn=lambda m: f"已切换到{'多镜头' if m == 'multi' else '单镜头'}模式",
            inputs=[mode_radio],
            outputs=[status_box]
        )
        
        gr.Markdown("""
        ---
        **使用流程**:
        1. 📥 导入文案和音频 → 2. 🚀 生成分镜头 → 3. 🎯 分配视频素材 → 4. 🎬 渲染输出
        
        **单镜头模式**: 每个分镜头匹配一个视频片段
        **多镜头模式**: 每个分镜头可匹配多个视频片段，自动切换
        """)
    
    return demo

if __name__ == '__main__':
    demo = create_app()
    demo.launch(server_name='0.0.0.0', server_port=7891)
