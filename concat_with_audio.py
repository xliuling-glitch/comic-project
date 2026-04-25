#!/usr/bin/env python3
"""
素材视频 + 口播音频 合成脚本
支持:
1. 按文件夹顺序拼接视频素材
2. 将口播音频（多个片段）合并到视频中
3. 自动对齐，输出最终成品

使用场景:
  先拍好各分类素材视频 → 录好口播音频 → 脚本自动合成
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

def get_video_files(folder_path: str) -> List[Path]:
    """从文件夹获取所有视频文件，按文件名排序"""
    extensions = ['.mp4', '.MP4', '.mov', '.MOV', '.avi', '.AVI', '.mkv', '.MKV', '.webm', '.WEBM']
    video_files = []
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"警告: 文件夹不存在 {folder_path}")
        return []
    
    for ext in extensions:
        for file in folder.glob(f"*{ext}"):
            video_files.append(file)
    
    video_files.sort()
    print(f"文件夹 [{folder_path}] 找到 {len(video_files)} 个视频")
    return video_files

def get_audio_files(folder_path: str) -> List[Path]:
    """从文件夹获取所有音频文件，按文件名排序"""
    extensions = ['.mp3', '.mp3', '.wav', '.wav', '.m4a', '.m4a', '.aac', '.AAC']
    audio_files = []
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"警告: 文件夹不存在 {folder_path}")
        return []
    
    for ext in extensions:
        for file in folder.glob(f"*{ext}"):
            audio_files.append(file)
    
    audio_files.sort()
    print(f"文件夹 [{folder_path}] 找到 {len(audio_files)} 个音频")
    return audio_files

def collect_all_videos(folders: List[str]) -> List[Path]:
    """从多个文件夹收集所有视频"""
    all_videos = []
    for folder in folders:
        videos = get_video_files(folder)
        all_videos.extend(videos)
    return all_videos

def concat_videos_only(video_files: List[Path], temp_output: str) -> bool:
    """先拼接所有视频得到纯视频文件（无音频或保留原音）"""
    concat_file = "temp_video_concat.txt"
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for video in video_files:
            abs_path = os.path.abspath(video)
            f.write(f"file '{abs_path}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c", "copy", temp_output
    ]
    
    print(f"拼接视频: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if os.path.exists(concat_file):
        os.remove(concat_file)
    
    if result.returncode != 0:
        print(f"拼接视频失败: {result.stderr}")
        return False
    return True

def concat_audios(audio_files: List[Path], temp_output: str) -> bool:
    """拼接所有口播音频"""
    concat_file = "temp_audio_concat.txt"
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for audio in audio_files:
            abs_path = os.path.abspath(audio)
            f.write(f"file '{abs_path}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c", "copy", temp_output
    ]
    
    print(f"拼接音频: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if os.path.exists(concat_file):
        os.remove(concat_file)
    
    if result.returncode != 0:
        print(f"拼接音频失败: {result.stderr}")
        return False
    return True

def merge_video_audio(video_path: str, audio_path: str, output_path: str, 
                     keep_original_audio: bool = False, original_volume: float = 0.1) -> bool:
    """
    合并视频和音频
    - keep_original_audio: 是否保留视频原音（比如环境音），原音会降低音量
    """
    if keep_original_audio:
        # 保留原音 + 口播，原音音量降低
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[0:a]volume={original_volume}[a0]; [a0][1:a]amerge[aout]",
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            output_path
        ]
    else:
        # 只保留口播，替换原音
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_path
        ]
    
    print(f"合并视频音频: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"合并失败: {result.stderr}")
        return False
    return True

def add_bgm_overlay(final_video: str, bgm_path: str, output_path: str, bgm_volume: float = 0.1) -> bool:
    """在已有视频+口播基础上，再叠加背景音乐"""
    cmd = [
        "ffmpeg", "-y",
        "-i", final_video,
        "-i", bgm_path,
        "-filter_complex", f"[1:a]volume={bgm_volume}[a1]",
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-map", "[a1]",
        "-c:v", "copy",
        "-c:a", "aac",
        output_path
    ]
    
    print(f"叠加背景音乐: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"添加BGM失败: {result.stderr}")
        return False
    return True

def read_folder_list(file_path: str) -> List[str]:
    """从文本文件读取文件夹列表"""
    folders = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                folders.append(line)
    return folders

def main():
    parser = argparse.ArgumentParser(description="素材视频 + 口播音频 自动合成")
    parser.add_argument("--video-folders", "-v", nargs="+", help="视频文件夹顺序，例如: -v 封口展示 机器外观 面板")
    parser.add_argument("--video-folder-list", "-vl", help="从文本文件读取视频文件夹顺序")
    
    parser.add_argument("--audio-folders", "-a", nargs="+", help="音频文件夹顺序，例如: -a 01开场 02痛点 03介绍")
    parser.add_argument("--audio-folder-list", "-al", help="从文本文件读取音频文件夹顺序")
    
    parser.add_argument("--output", "-o", required=True, help="输出最终视频路径")
    parser.add_argument("--keep-original-audio", "-k", action="store_true", 
                        help="保留视频原音（如环境音），会降低原音音量")
    parser.add_argument("--original-volume", type=float, default=0.1, 
                        help="原音音量，默认 0.1")
    parser.add_argument("--bgm", help="额外叠加背景音乐（可选）")
    parser.add_argument("--bgm-volume", type=float, default=0.1, 
                        help="背景音乐音量，默认 0.1")
    
    args = parser.parse_args()
    
    # 获取视频文件夹
    if args.video_folder_list:
        video_folders = read_folder_list(args.video_folder_list)
    else:
        video_folders = args.video_folders
    
    if not video_folders:
        print("错误: 请指定视频文件夹")
        sys.exit(1)
    
    # 获取音频文件夹
    if args.audio_folder_list:
        audio_folders = read_folder_list(args.audio_folder_list)
    else:
        audio_folders = args.audio_folders
    
    if not audio_folders:
        print("错误: 请指定音频文件夹")
        sys.exit(1)
    
    # 收集所有视频
    print(f"[1/5] 收集视频素材...")
    all_videos = collect_all_videos(video_folders)
    if not all_videos:
        print("错误: 没有找到任何视频文件")
        sys.exit(1)
    print(f"    共 {len(all_videos)} 个视频片段")
    
    # 收集所有音频
    print(f"[2/5] 收集口播音频...")
    all_audios = []
    for folder in audio_folders:
        audios = get_audio_files(folder)
        all_audios.extend(audios)
    if not all_audios:
        print("错误: 没有找到任何音频文件")
        sys.exit(1)
    print(f"    共 {len(all_audios)} 个音频片段")
    
    # 1. 拼接视频
    print(f"[3/5] 拼接所有视频...")
    temp_video = "temp_concat_video.mp4"
    success = concat_videos_only(all_videos, temp_video)
    if not success:
        sys.exit(1)
    
    # 2. 拼接音频
    print(f"[4/5] 拼接口播音频...")
    temp_audio = "temp_concat_audio.mp3"
    success = concat_audios(all_audios, temp_audio)
    if not success:
        sys.exit(1)
    
    # 3. 合并视频音频
    print(f"[5/5] 合并视频和音频...")
    if args.bgm:
        # 如果有 BGM，先输出中间文件
        temp_with_audio = "temp_with_audio.mp4"
        success = merge_video_audio(
            temp_video, temp_audio, temp_with_audio,
            args.keep_original_audio, args.original_volume
        )
        if not success:
            sys.exit(1)
        
        # 叠加 BGM
        success = add_bgm_overlay(temp_with_audio, args.bgm, args.output, args.bgm_volume)
        
        # 清理临时文件
        for f in [temp_video, temp_audio, temp_with_audio]:
            if os.path.exists(f):
                os.remove(f)
    else:
        # 直接输出最终结果
        success = merge_video_audio(
            temp_video, temp_audio, args.output,
            args.keep_original_audio, args.original_volume
        )
        
        # 清理临时文件
        for f in [temp_video, temp_audio]:
            if os.path.exists(f):
                os.remove(f)
    
    if success:
        print(f"\n✅ 合成完成！最终视频: {os.path.abspath(args.output)}")
        print(f"   视频片段数: {len(all_videos)}")
        print(f"   口播片段数: {len(all_audios)}")
    else:
        print("\n❌ 合成失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
