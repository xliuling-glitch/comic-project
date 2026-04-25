#!/usr/bin/env python3
"""
视频自动拼接脚本
基于 MiniMax Hailuo 视频生成 + ffmpeg 尾帧接续技术

功能：
- 批量生成多个视频片段
- 自动提取每个片段的最后一帧作为下一个片段的首帧
- 使用 ffmpeg 拼接所有视频片段
- 添加背景音乐合并输出

工作流程：
1. 准备好分镜列表，每个镜头包含描述和首帧图片（第一个镜头需要手动准备）
2. 调用 MiniMax API 生成视频
3. 提取最后一帧保存
4. 用最后一帧作为下一个镜头的首帧，重复
5. 最后拼接所有视频 + 添加背景音乐
"""

import os
import sys
import json
import requests
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

# ============ 配置 ============
MINIMAX_API_HOST = "https://api.minimax.chat"
# 如果是国际版，改用 https://api.minimax.io

def get_api_key() -> str:
    """从环境变量或配置文件获取 API Key"""
    api_key = os.environ.get("MINIMAX_API_KEY")
    if api_key:
        return api_key
    
    config_path = Path.home() / ".minimax" / "api_key.txt"
    if config_path.exists():
        with open(config_path, "r") as f:
            return f.read().strip()
    
    raise ValueError(
        "请设置 MINIMAX_API_KEY 环境变量，"
        "或将 API Key 保存到 ~/.minimax/api_key.txt"
    )

def get_access_token(api_key: str) -> str:
    """获取 access token（MMX CLI 方式）"""
    # 实际上我们直接使用 API Key 方式调用，这里简化处理
    return api_key

def extract_lastframe(video_path: str, output_path: str) -> bool:
    """
    使用 ffmpeg 提取视频最后一帧
    """
    cmd = [
        "ffmpeg", "-y", "-sseof", "-1", "-i", str(video_path),
        "-vframes", "1", "-q:v", "2", str(output_path)
    ]
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"提取尾帧失败: {result.stderr}")
        return False
    return True

def upload_to_catbox(file_path: str) -> Optional[str]:
    """
    上传文件到 catbox.moe 获取公网 URL
    MiniMax 需要公网可访问的 URL 作为首帧图片
    """
    url = "https://catbox.moe/user/api.php"
    
    with open(file_path, "rb") as f:
        files = {"fileToUpload": f}
        data = {"reqtype": "fileupload"}
        response = requests.post(url, files=data, data=data)
    
    if response.status_code == 200 and response.text.startswith("https://"):
        return response.text.strip()
    else:
        print(f"上传失败: {response.text}")
        return None

def generate_video(
    api_key: str,
    prompt: str,
    first_frame_url: str,
    output_path: str,
    duration: int = 6,
    resolution: str = "768P"
) -> bool:
    """
    调用 MiniMax Hailuo-2.3 生成视频
    文档: https://docs.minimax.chat/video/video-gen
    """
    url = f"{MINIMAX_API_HOST}/v1/video/generation"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "MiniMax-Hailuo-2.3",
        "prompt": prompt,
        "first_frame_image": first_frame_url,
        "duration": duration,
        "resolution": resolution
    }
    
    print(f"正在生成视频: {prompt[:50]}...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"生成失败: {response.status_code} {response.text}")
        return False
    
    data = response.json()
    job_id = data.get("job_id")
    
    if not job_id:
        print(f"未获取到 job_id: {data}")
        return False
    
    # 轮询等待生成完成
    print(f"任务已提交，job_id: {job_id}，等待生成...")
    import time
    for i in range(60):  # 最多等待 5 分钟
        time.sleep(5)
        status_url = f"{MINIMAX_API_HOST}/v1/video/get_job"
        status_response = requests.get(
            status_url, 
            headers=headers,
            params={"job_id": job_id}
        )
        status_data = status_response.json()
        
        if status_data.get("status") == "finished":
            video_url = status_data.get("video_url")
            print(f"生成完成，下载视频: {video_url}")
            # 下载视频
            video_response = requests.get(video_url)
            with open(output_path, "wb") as f:
                f.write(video_response.content)
            return True
        elif status_data.get("status") == "failed":
            print(f"生成失败: {status_data}")
            return False
        else:
            print(f"当前状态: {status_data.get('status')}，继续等待...")
    
    print("生成超时")
    return False

def concat_videos(video_list: List[str], output_path: str) -> bool:
    """
    使用 ffmpeg 拼接多个视频
    """
    # 创建文件列表
    with open("concat_list.txt", "w") as f:
        for video in video_list:
            f.write(f"file '{os.path.abspath(video)}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "concat_list.txt", "-c", "copy", output_path
    ]
    print(f"拼接视频: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 清理临时文件
    if os.path.exists("concat_list.txt"):
        os.remove("concat_list.txt")
    
    if result.returncode != 0:
        print(f"拼接失败: {result.stderr}")
        return False
    return True

def add_bgm(video_path: str, bgm_path: str, output_path: str) -> bool:
    """
    添加背景音乐到视频
    """
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", bgm_path,
        "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0",
        "-map", "1:a:0", output_path
    ]
    print(f"添加背景音乐: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"添加BGM失败: {result.stderr}")
        return False
    return True

def process_shot_list(shot_list: List[Dict], output_dir: str, api_key: str) -> List[str]:
    """
    按顺序处理整个分镜列表
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    generated_videos = []
    
    last_frame_url = None
    for i, shot in enumerate(shot_list):
        clip_name = f"clip{i+1:02d}"
        video_path = os.path.join(output_dir, f"{clip_name}.mp4")
        last_frame_path = os.path.join(output_dir, f"{clip_name}_lastframe.png")
        
        # 获取首帧
        if i == 0:
            # 第一个镜头使用用户提供的首帧
            if "first_frame_path" in shot:
                first_frame_path = shot["first_frame_path"]
            else:
                print(f"错误：第一个镜头必须提供 first_frame_path")
                continue
        else:
            # 使用上一个镜头的尾帧
            first_frame_path = last_frame_path
        
        # 上传首帧到公网获取 URL
        print(f"上传第 {i+1} 个镜头首帧...")
        first_frame_url = upload_to_catbox(first_frame_path)
        if not first_frame_url:
            print(f"上传首帧失败，跳过此镜头")
            continue
        
        # 生成视频
        prompt = shot["prompt"]
        if "camera_movement" in shot and shot["camera_movement"]:
            prompt = f"{prompt} {shot['camera_movement']}"
        
        success = generate_video(
            api_key=api_key,
            prompt=prompt,
            first_frame_url=first_frame_url,
            output_path=video_path,
            duration=shot.get("duration", 6),
            resolution=shot.get("resolution", "768P")
        )
        
        if not success:
            print(f"生成视频 {clip_name} 失败，继续下一个")
            continue
        
        generated_videos.append(video_path)
        
        # 提取尾帧
        success = extract_lastframe(video_path, last_frame_path)
        if not success:
            print(f"提取尾帧失败，后续镜头无法接续")
            break
        
        print(f"完成第 {i+1} 个镜头: {video_path}")
        print(f"尾帧已保存: {last_frame_path}")
    
    return generated_videos

def main():
    parser = argparse.ArgumentParser(description="MiniMax 视频自动拼接脚本")
    parser.add_argument("--config", "-c", required=True, help="分镜配置 JSON 文件")
    parser.add_argument("--output-dir", "-o", default="output", help="输出目录")
    parser.add_argument("--bgm", help="背景音乐 MP3 文件路径")
    args = parser.parse_args()
    
    # 读取配置
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    shot_list = config.get("shots", [])
    if not shot_list:
        print("错误：配置文件中没有找到 shots 数组")
        sys.exit(1)
    
    # 获取 API Key
    try:
        api_key = get_api_key()
    except ValueError as e:
        print(e)
        sys.exit(1)
    
    # 处理所有镜头
    print(f"开始处理 {len(shot_list)} 个镜头...")
    generated_videos = process_shot_list(shot_list, args.output_dir, api_key)
    
    if not generated_videos:
        print("没有成功生成任何视频")
        sys.exit(1)
    
    # 拼接视频
    final_concat = os.path.join(args.output_dir, "concat.mp4")
    print(f"拼接 {len(generated_videos)} 个视频...")
    success = concat_videos(generated_videos, final_concat)
    
    if not success:
        print("拼接失败")
        sys.exit(1)
    
    # 添加背景音乐
    if args.bgm and os.path.exists(args.bgm):
        final_output = os.path.join(args.output_dir, "final_with_bgm.mp4")
        success = add_bgm(final_concat, args.bgm, final_output)
        if success:
            print(f"\n✅ 完成！最终视频: {final_output}")
        else:
            print(f"\n✅ 完成拼接（无BGM）: {final_concat}")
    else:
        print(f"\n✅ 完成！拼接视频: {final_concat}")
    
    print(f"\n所有片段保存在: {args.output_dir}")

if __name__ == "__main__":
    main()
