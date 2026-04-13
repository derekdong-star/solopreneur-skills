# Image Hosting — GitHub 图床上传工具

将本地图片上传到 `derekdong-star/image-hosting` 仓库，返回公开的 `raw.githubusercontent.com` URL 和 Markdown 图片链接。

## 处理流程

![流程图](https://raw.githubusercontent.com/derekdong-star/image-hosting/main/diagrams/2026-04-13-174631-image-hosting-flowchart.png)

**4 个阶段：**

1. **输入与校验** — 检查文件是否存在、类型正确、大小 <50MB
2. **仓库准备** — 克隆/验证 remote、检查工作区干净、拉取最新代码
3. **路径规划** — 推断目标目录、生成时间戳文件名、确保文件名唯一
4. **确认与执行** — 交互确认（`--yes` 可跳过）后执行 copy → git add → commit → push

## 快速开始

```bash
# 上传图片（自动推断目录）
uv run scripts/upload.py "/path/to/image.png"

# 指定目录
uv run scripts/upload.py "/path/to/image.png" --directory wechat-covers

# 试运行（不实际上传）
uv run scripts/upload.py "/path/to/image.png" --dry-run
```

更多参数和配置说明见 [SKILL.md](SKILL.md)。
