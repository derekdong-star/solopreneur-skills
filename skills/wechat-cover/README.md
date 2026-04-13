# 微信公众号封面图生成器

基于文章标题语义的 AI 封面图生成工具，支持 OpenAI 和 Gemini 多模型。

## 处理流程

```
文章标题 + 话题 → 标题模式识别 → 视觉线索匹配 → Prompt 构建 → 图像生成 → 裁剪输出
```

![处理流程图](https://github.com/derekdong-star/image-hosting/blob/main/wechat-covers/2026-04-13-wechat-cover-%E6%88%91%E6%8A%8A%E8%87%AA%E5%B7%B1%E8%92%B8%E9%A6%8F%E6%88%90%E4%BA%86%E4%B8%80%E4%B8%AA-ai-%E6%8A%80%E8%83%BD%E5%8C%85.png)

**4 个阶段：**

1. **输入与配置** — 解析 CLI 参数，加载 `settings.json`，选择图像提供商
2. **标题分析引擎** — 识别 9 种标题模式（transform / contrast / guide / warning 等），提取视觉线索和情绪关键词
3. **Prompt 构建** — 组合标题分析结果、风格变体、构图模板、反陈词列表，生成最终提示词
4. **图像生成与输出** — 调用模型 API，Pillow 裁剪为 900x383 (2.35:1) PNG

核心设计原则：**标题优先**（title-first），图像概念由标题语义驱动，而非仅仅依赖话题标签。

## 快速开始

```bash
cp settings.json.example settings.json  # 填入 API Key

# 基础用法
uv run scripts/generate.py --title "你的文章标题" --topic "AI tools"

# 试运行（只看 prompt，不生成图片）
uv run scripts/generate.py --title "你的文章标题" --topic "AI tools" --dry-run
```

更多参数和配置说明见 [SKILL.md](SKILL.md)。
