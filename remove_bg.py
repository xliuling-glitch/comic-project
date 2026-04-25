from rembg import remove
from PIL import Image

# 输入图片路径
input_path = r"C:\Users\Administrator\.openclaw\media\inbound\640a79919250df10e9101d1865c4183d_compress---f1e052a2-a00b-47be-a784-b2a28d1ffe1c.jpg"
# 输出图片路径
output_path = r"C:\Users\Administrator\.openclaw\workspace\鼠妇_白底图.png"

# 读取图片
input_img = Image.open(input_path)

# 移除背景
output_img = remove(input_img)

# 创建纯白背景
white_bg = Image.new("RGB", output_img.size, (255, 255, 255))
white_bg.paste(output_img, mask=output_img.split()[3])  # 使用 alpha 通道作为蒙版

# 保存结果
white_bg.save(output_path, "PNG")
print(f"抠图完成，已保存到: {output_path}")
