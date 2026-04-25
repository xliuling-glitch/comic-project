import pandas as pd
import os

folder_path = r"F:\每日收支可视化"
os.chdir(folder_path)

# 列出所有文件
files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
print("找到的Excel文件:")
for f in files:
    print(f"  - {f}")
print()

# 读取每个文件并显示结构
for f in files:
    print("=" * 60)
    print(f"文件: {f}")
    try:
        df = pd.read_excel(f)
        print(f"形状: {df.shape[0]} 行 × {df.shape[1]} 列")
        print(f"列名: {list(df.columns)}")
        print("\n前3行数据:")
        print(df.head(3))
        print()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        print()
