#!/usr/bin/env python3
"""
上下文自动总结工具 - 读取最近N天的记忆文件并生成总结
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

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
            # 从文件名解析日期 (格式: YYYY-MM-DD.md)
            file_date = datetime.strptime(file.stem, "%Y-%m-%d")
            if file_date >= cutoff_date:
                recent_files.append((file, file_date))
        except ValueError:
            # 如果文件名不是日期格式，使用文件修改时间
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            if mtime >= cutoff_date:
                recent_files.append((file, mtime))
    
    # 按日期排序
    recent_files.sort(key=lambda x: x[1], reverse=True)
    return recent_files

def read_file_content(file_path: Path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取文件出错: {str(e)}"

def generate_summary(files_with_dates, days: int):
    """生成总结"""
    if not files_with_dates:
        return f"## 最近 {days} 天上下文总结\n\n没有找到最近 {days} 天内的记忆文件。"
    
    summary = [f"## 最近 {days} 天上下文总结\n"]
    summary.append(f"**总结时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    summary.append(f"**找到文件数**: {len(files_with_dates)} 个\n\n")
    summary.append("---\n\n")
    
    all_content = []
    
    for file, file_date in files_with_dates:
        content = read_file_content(file)
        all_content.append((file.stem, content))
        
        summary.append(f"### 📅 {file.stem}\n")
        summary.append(f"**文件**: `{file.name}`\n\n")
        # 显示前200字符作为预览
        preview = content[:200] + "..." if len(content) > 200 else content
        summary.append(f"**内容预览**:\n{preview}\n\n")
        summary.append("---\n\n")
    
    # 生成完整内容
    full_content = "\n\n".join([f"=== {date} ===\n{content}" for date, content in all_content])
    
    return "".join(summary), full_content

def main():
    # 解析命令行参数
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"用法: {sys.argv[0]} [天数]")
            sys.exit(1)
    
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"正在读取最近 {days} 天的记忆文件...\n")
    
    # 获取最近的文件
    recent_files = get_recent_files(days)
    
    # 生成总结
    summary, full_content = generate_summary(recent_files, days)
    
    # 打印总结
    print(summary)
    
    # 保存总结到文件
    output_file = MEMORY_DIR / f"summary_last_{days}_days.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(summary)
        f.write("\n\n## 完整内容\n\n")
        f.write(full_content)
    
    print(f"\n总结已保存到: {output_file}")

if __name__ == "__main__":
    main()
