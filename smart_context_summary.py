#!/usr/bin/env python3
"""
智能上下文总结工具 - 深度分析最近N天的记忆文件
"""
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# 记忆文件夹路径
MEMORY_DIR = Path("C:/Users/Administrator/.openclaw/workspace/memory")

def get_recent_files(days: int = 7):
    """获取最近N天内的记忆文件"""
    if not MEMORY_DIR.exists():
        print(f"错误: 记忆文件夹不存在: {MEMORY_DIR}")
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_files = []
    
    for file in MEMORY_DIR.glob("*.md"):
        try:
            file_date = datetime.strptime(file.stem, "%Y-%m-%d")
            if file_date >= cutoff_date:
                recent_files.append((file, file_date))
        except ValueError:
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime >= cutoff_date:
                recent_files.append((file, mtime))
    
    recent_files.sort(key=lambda x: x[1], reverse=True)
    return recent_files

def read_file_content(file_path: Path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取文件出错: {str(e)}"

def extract_key_info(content):
    """提取关键信息"""
    info = {
        'projects': [],
        'todos': [],
        'completed': [],
        'decisions': [],
        'ideas': [],
        'people': [],
    }
    
    # 提取项目 (## 开头的标题
    projects = re.findall(r'##\s+(.+)', content)
    info['projects'] = [p.strip() for p in projects if 5 < len(p.strip()) < 50]
    
    # 提取已完成 (✅ 开头
    completed = re.findall(r'✅\s*(.+)', content)
    info['completed'] = [c.strip() for c in completed]
    
    # 提取待办事项
    info['todos'] = re.findall(r'(?:TODO|待办|需要|要做|计划)\s*[:：]\s*(.+)', content, re.IGNORECASE)
    
    # 提取决策和想法
    lines = content.split('\n')
    for line in lines:
        if any(keyword in line for keyword in ['决定', '选择', '方案', '建议', '想法', '思路']):
            if 10 < len(line.strip()) < 200:
                info['decisions'].append(line.strip())
    
    return info

def generate_smart_summary(files_with_dates, days: int):
    """生成智能总结"""
    if not files_with_dates:
        return f"# 最近 {days} 天智能上下文总结\n\n没有找到最近 {days} 天内的记忆文件。"
    
    all_content = []
    all_info = defaultdict(list)
    
    for file, file_date in files_with_dates:
        content = read_file_content(file)
        all_content.append((file.stem, content))
        info = extract_key_info(content)
        for key, value in info.items():
            for v in value:
                if v not in all_info[key]:
                    all_info[key].append(v)
    
    summary = [f"# 最近 {days} 天智能上下文总结\n\n"]
    summary.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    summary.append(f"**分析文件数**: {len(files_with_dates)} 个\n\n")
    
    # 核心项目
    if all_info['projects']:
        summary.append("## 📂 核心项目\n")
        for project in all_info['projects']:
            summary.append(f"- {project}\n")
        summary.append("\n")
    
    # 已完成事项
    if all_info['completed']:
        summary.append("## ✅ 已完成事项\n")
        for item in all_info['completed']:
            summary.append(f"- {item}\n")
        summary.append("\n")
    
    # 待办事项
    if all_info['todos']:
        summary.append("## 📋 待办事项\n")
        for todo in all_info['todos']:
            summary.append(f"- [ ] {todo}\n")
        summary.append("\n")
    
    # 决策与想法
    if all_info['decisions']:
        summary.append("## 💡 决策与想法\n")
        for decision in all_info['decisions']:
            summary.append(f"- {decision}\n")
        summary.append("\n")
    
    # 按日期的详细内容
    summary.append("## 📅 按日期详细记录\n\n")
    summary.append("---\n\n")
    
    for file, file_date in files_with_dates:
        content = read_file_content(file)
        summary.append(f"### {file.stem}\n\n")
        summary.append(content)
        summary.append("\n---\n\n")
    
    return "".join(summary)

def main():
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"用法: {sys.argv[0]} [天数]")
            sys.exit(1)
    
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"正在智能分析最近 {days} 天的记忆文件...\n")
    
    recent_files = get_recent_files(days)
    summary = generate_smart_summary(recent_files, days)
    
    print(summary)
    
    output_file = MEMORY_DIR / f"smart_summary_last_{days}_days.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"\n智能总结已保存到: {output_file}")

if __name__ == "__main__":
    main()
