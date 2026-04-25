# 公众号自动发布 Skill

## 描述
自动将对话中收到的文章发布到公众号草稿箱，完整工作流自动化。遵循"公众号自动化发文全流程思路分享"的设计。

**触发关键词：** 发布到公众号、发文到公众号、保存公众号草稿、自动发布公众号文章

## 工作流程

1. **接收用户输入** - 用户发送文字+图片（可选）
2. **读取规范** - 读取 `E:\wechat-publisher\docs\markdown-rules.md` 和 `E:\wechat-publisher\docs\personal-style.md`
3. **格式化文章** - 根据 MD 规范和个人风格，为纯文本添加规范的 Markdown 语法
4. **保存文章** - 创建目录 `E:\wechat-publisher\posts\YYYY-MM-DD-{slug}\post.md` 保存
5. **处理配图** - 如果用户发送了图片，自动保存到文章目录并插入到文章对应位置
6. **发布草稿** - 通过 wechatsync CLI 发布到公众号草稿箱
7. **返回结果** - 告知用户发布结果

## 配置说明
- wechatsync 已安装在 `E:\wechat-publisher\Wechatsync`
- 需要先运行 `wechatsync config` 配置公众号 AppID 和 AppSecret
- MD 排版规范：`E:\wechat-publisher\docs\markdown-rules.md`
- 个人风格指南：`E:\wechat-publisher\docs\personal-style.md`
- 后续可以不断迭代更新个人风格文档，文章质量会越来越好

## 使用示例
> 用户：帮我把这篇文章发布到公众号草稿箱
> 
> （用户发送文章内容和图片）
> 
> 助手：自动完成格式整理、保存、发布，返回成功信息
