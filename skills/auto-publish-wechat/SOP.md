# 公众号自动发布标准操作流程

## 触发条件
当用户说以下任意一句话时触发：
- "帮我发布到公众号"
- "发布到公众号草稿箱"
- "发文到公众号"
- "自动发布这篇文章到公众号"

## 详细步骤

### 第一步：提取文章内容和标题
- 从对话中提取用户提供的完整文章内容
- 如果用户没有明确给出标题，从文章第一段提取标题
- 如果用户提供了多张图片，按顺序记录

### 第二步：读取排版规范和个人风格
- **必须读取**：`E:\wechat-publisher\docs\markdown-rules.md` - Markdown 排版规范
- **必须读取**：`E:\wechat-publisher\docs\personal-style.md` - 个人写作风格
- 整理文章时严格遵循这两个文档的要求

### 第三步：生成 slug 和创建目录
- 当前日期格式：`YYYY-MM-DD`
- 从标题生成 slug：小写字母，单词用 `-` 连接，去掉特殊字符
- 创建目录：`E:\wechat-publisher\posts\YYYY-MM-DD-{slug}\`
- 示例：`E:\wechat-publisher\posts\2026-03-27-my-first-post\`

### 第四步：整理为 Markdown 格式
- 根据 MD 规范添加合适的标题层级
- 根据个人风格调整语气和段落结构
- 配图占位格式：`![配图X]({filename})`，其中 X 是图片序号
- 保持原文核心内容不变，只优化格式和表达
- 将整理好的文章写入 `post.md`

### 第五步：保存图片（如果有）
- 将用户发送的图片保存到文章目录：`E:\wechat-publisher\posts\YYYY-MM-DD-{slug}\img-{index}.jpg`
- 在文中对应位置引用图片

### 第六步：调用 wechatsync 发布
- 执行命令：`wechatsync publish --platform wechat --file "E:\wechat-publisher\posts\YYYY-MM-DD-{slug}\post.md" --title "文章标题"`
- 等待命令执行完成
- 捕获输出结果

### 第七步：返回结果给用户
- 如果发布成功：告知成功，并显示文章保存位置和草稿状态
- 如果发布失败：显示错误信息，并给出排查建议（通常是配置问题）

## 注意事项
- 用户只需要发送文章内容和图片，说一声"发布到公众号"，剩下的全自动
- 如果 wechatsync 提示需要配置，引导用户运行 `wechatsync config`
- 所有文章都保存在 E 盘，方便整理和多平台复用
- 当某篇文章发布后效果特别好，可以后续单独触发 Skill 迭代更新个人风格文档
