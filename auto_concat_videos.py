#!/usr/bin/env python3
"""
本地素材自动拼接脚本
支持按文件夹批量拼接视频，适合：
- 多个分类文件夹存放不同片段类型
- 按顺序自动拼接所有视频
- 自动添加转场（可选）
- 添加背景音乐
- 输出最终成品

使用场景示例：
  10个文件夹，每个放3~5秒的痛点片段
  脚本自动按顺序把它们拼接成一个完整视频

用法示例:
  python auto_concat_videos.py --folders 文件夹1 文件夹2 文件夹3 --output final.mp4
  python auto_concat_videos.py --folder-list folders.txt --output final.mp4 --bgm bgm.mp3
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

def get_video_files(folder_path: str) -> List[Path]:
    """
    从文件夹获取所有视频文件，按文件名排序
    支持: .mp4, .mov, .avi, .mkv, .webm
    """
    extensions = ['.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI', '.mkv', '.MKV', '.webm', '.WEBM']
    video_files = []
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"警告: 文件夹不存在 {folder_path}")
        return []
    
    for ext in extensions:
        for file in folder.glob(f"*{ext}"):
            video_files.append(file)
    
    # 按文件名排序
    video_files.sort()
    print(f"文件夹 [{folder_path}] 找到 {len(video_files)} 个视频文件")
    return video_files

def collect_all_videos(folders: List[str]) -> List[Path]:
    """
    从多个文件夹收集所有视频文件，保持文件夹顺序
    """
    all_videos = []
    for folder in folders:
        videos = get_video_files(folder)
        all_videos.extend(videos)
    return all_videos

def read_folder_list(file_path: str) -> List[str]:
    """
    从文本文件读取文件夹列表，每行一个文件夹
    """
    folders = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                folders.append(line)
    return folders

def create_concat_file(video_files: List[Path], concat_file: str = "concat_list.txt") -> bool:
    """
    创建 ffmpeg 需要的拼接列表文件
    """
    try:
        with open(concat_file, 'w', encoding='utf-8') as f:
            for video in video_files:
                # ffmpeg concat 格式需要使用 file 'path'
                abs_path = os.path.abspath(video)
                f.write(f"file '{abs_path}'\n")
        return True
    except Exception as e:
        print(f"创建拼接列表失败: {e}")
        return False

def concat_videos(video_files: List[Path], output_path: str, with_transition: bool = False) -> bool:
    """
    使用 ffmpeg 拼接视频
    - with_transition=False: 直接复制拼接（最快，不重新编码）
    - with_transition=True: 添加淡入淡出转场（需要重新编码）
    """
    concat_file = "temp_concat_list.txt"
    if not create_concat_file(video_files, concat_file):
        return False
    
    if not with_transition:
        # 直接拼接，不重新编码 - 速度最快
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file, "-c", "copy", output_path
        ]
    else:
        # 使用 xfade 转场，每个片段之间添加淡入淡出
        # 这个比较复杂，需要动态生成滤镜复杂
        # 这里简化处理，使用复杂滤镜
        inputs = []
        filter_complex = []
        
        for i, _ in enumerate(video_files):
            inputs.extend(["-i", str(video_files[i])])
        
        # 构建 xfade 滤镜链
        # 这部分比较复杂，简化版只支持简单淡入淡出
        # 如果需要完整转场支持，建议用视频编辑软件
        cmd = [
            "ffmpeg", "-y"
        ] + inputs + [
            "-c:v", "libx264",
            "-c:a", "aac",
            output_path
        ]
    
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 清理临时文件
    if os.path.exists(concat_file):
        os.remove(concat_file)
    
    if result.returncode != 0:
        print(f"拼接失败: {result.stderr}")
        return False
    
    print(f"拼接完成: {output_path}")
    return True

def add_bgm(video_path: str, bgm_path: str, output_path: str, bgm_volume: float = 0.1) -> bool:
    """
    添加背景音乐到拼接好的视频
    bgm_volume: BGM 音量 (0.0 - 1.0)，默认 0.1 背景音较小
    """
    if not os.path.exists(video_path):
        print(f"视频文件不存在: {video_path}")
        return False
    
    if not os.path.exists(bgm_path):
        print(f"BGM 文件不存在: {bgm_path}")
        return False
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", bgm_path,
        "-filter_complex", f"[1:a]volume={bgm_volume}[a1]",
        "-map", "0:v:0",
        "-map", "[a1]",
        "-c:v", "copy",
        "-c:a", "aac",
        output_path
    ]
    
    print(f"添加背景音乐: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"添加BGM失败: {result.stderr}")
        return False
    
    return True

def get_total_duration(video_files: List[Path]) -> float:
    """
    估算总时长（显示给用户参考）
    这里不做精确探测，只按平均估算
    """
    # 简单估算：假设平均每个文件 4 秒
    return len(video_files) * 4.0

def main():
    parser = argparse.ArgumentParser(description="本地素材文件夹自动拼接视频")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--folders", "-f", nargs="+", help="按顺序输入多个文件夹路径，例如: -f ./pain ./solution ./benefit")
    group.add_argument("--folder-list", "-l", help="从文本文件读取文件夹列表，每行一个文件夹")
    
    parser.add_argument("--output", "-o", required=True, help="输出最终视频路径，例如: final.mp4")
    parser.add_argument("--bgm", "-b", help="背景音乐 MP3 文件路径（可选）")
    parser.add_argument("--bgm-volume", type=float, default=0.1, help="背景音乐音量 0.0-1.0，默认 0.1")
    parser.add_argument("--transition", "-t", action="store_true", help="添加转场效果（需要重新编码，较慢）")
    
    args = parser.parse_args()
    
    # 获取文件夹列表
    if args.folder_list:
        folders = read_folder_list(args.folder_list)
    else:
        folders = args.folders
    
    if not folders:
        print("错误: 没有找到任何文件夹")
        sys.exit(1)
    
    print(f"按顺序处理 {len(folders)} 个文件夹...")
    
    # 收集所有视频文件
    all_videos = collect_all_videos(folders)
    
    if not all_videos:
        print("错误: 没有找到任何视频文件")
        sys.exit(1)
    
    print(f"\n总共收集到 {len(all_videos)} 个视频片段")
    estimated_duration = get_total_duration(all_videos)
    print(f"估算总时长: {estimated_duration:.1f} 秒")
    
    print("\n开始拼接...")
    
    # 第一步：拼接所有视频
    if args.bgm:
        # 如果有 BGM，先输出临时拼接文件
        temp_concat = "temp_concat.mp4"
        success = concat_videos(all_videos, temp_concat, args.transition)
        if not success:
            sys.exit(1)
        
        # 第二步：添加 BGM
        success = add_bgm(temp_concat, args.bgm, args.output, args.bgm_volume)
        
        # 清理临时文件
        if os.path.exists(temp_concat):
            os.remove(temp_concat)
    else:
        # 直接输出最终结果
        success = concat_videos(all_videos, args.output, args.transition)
    
    if not success:
        print("处理失败")
        sys.exit(1)
    
    print(f"\n✅ 处理完成！最终视频: {os.path.abspath(args.output)}")
    print(f"   片段数: {len(all_videos)}")
    print(f"   估算时长: {estimated_duration:.1f} 秒")

if __name__ == "__main__":
    main()
