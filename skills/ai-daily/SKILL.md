---
name: ai-daily
description: AI-powered RSS digest from 90 top tech blogs curated by Andrej Karpathy. Fetches, scores, and summarizes articles automatically using OpenAI-compatible APIs.
---

# AI Daily Digest

自动抓取 90 个顶级技术博客 RSS，使用 AI 评分、筛选并生成每日精选摘要。

## 数据源

来自 **Hacker News Popularity Contest 2025** 的 90 个高质量技术博客，由 Andrej Karpathy (@karpathy) 推荐：

- Simon Willison, Jeff Geerling, Mitchell Hashimoto, Paul Graham
- krebsonsecurity, Daring Fireball, Margaret's Hideous Glitz
- 优秀独立开发者、系统工程师、AI 研究者博客

覆盖：AI/ML、安全、工程架构、工具开源、行业观点

## 功能特点

- **智能评分** — 从相关性、质量、时效性三个维度 1-10 分评分
- **自动分类** — AI/ML、安全、工程、工具、观点、其他
- **中文摘要** — 4-6 句结构化摘要 + 1 句推荐理由
- **关键词提取** — 每篇文章 2-4 个英文关键词
- **今日看点** — AI 生成当日技术趋势总结
- **Markdown 输出** — 直接用于公众号排版

## 使用方法

**基础用法：**
```bash
python scripts/ai_daily.py --hours 24 --top-n 15 --lang zh
```

**指定输出文件：**
```bash
python scripts/ai_daily.py --hours 48 --top-n 20 -o ./digest.md
```

**英文输出：**
```bash
python scripts/ai_daily.py --hours 72 --top-n 10 --lang en
```

## 参数说明

| 参数      | 说明                                                         | 默认值 |
| --------- | ------------------------------------------------------------ | ------ |
| `--hours` | 时间范围（小时）                                             | 24     |
| `--top-n` | 选取文章数量                                                 | 15     |
| `--lang`  | 输出语言：`zh` 中文 / `en` 英文                              | zh     |
| `--output` | 输出文件路径（默认：`./ai-daily-YYYYMMDD.md`）              | -      |

## 环境变量

| 变量             | 必需 | 说明                                                         |
| ---------------- | ---- | ------------------------------------------------------------ |
| `OPENAI_API_KEY` | 是   | OpenAI 兼容 API Key                                          |
| `OPENAI_API_BASE` | 否   | API Base URL（默认：`https://open.bigmodel.cn/api/paas/v4/`） |
| `OPENAI_MODEL`   | 否   | 模型名称（默认：`glm-4.7`）                                  |

### 支持的 API 提供商

- **智谱 AI** (默认)：`https://open.bigmodel.cn/api/paas/v4/`
- **DeepSeek**：`https://api.deepseek.com` (自动使用 `deepseek-chat`)
- **OpenAI**：`https://api.openai.com/v1`
- 其他兼容 OpenAI 格式的 API

## 依赖安装

```bash
pip install -r requirements.txt
```

需要 `aiohttp` 用于异步 HTTP 请求。

## 输出示例

```markdown
# 📰 AI 博客每日精选 — 2026-02-21

## 📝 今日看点

今天技术圈聚焦于 AI 工程实践 — Claude 发布了新的 MCP 协议让 AI Agent 与工具集成更简单，多个开源项目快速适配...

## 🏆 今日必读

🥇 **MCP 协议发布：AI Agent 的"USB接口"来了**

[MCP: Model Context Protocol](https://...) — Anthropic · 2 小时前 · 🤖 AI / ML

> Model Context Protocol (MCP) 是一个开放标准，让 AI 应用能够无缝连接外部数据源和工具...

💡 **为什么值得读**: 这是 AI Agent 领域的重要基础设施，类似 USB 对硬件的意义

🏷️ MCP, AI Agent, Anthropic, protocol
```

## 评分标准

AI 对每篇文章从三个维度评分（1-10 分）：

### 相关性 (relevance)
- 10: 所有技术人都应该知道的重大事件/突破
- 7-9: 对大部分技术从业者有价值
- 4-6: 对特定技术领域有价值
- 1-3: 与技术行业关联不大

### 质量 (quality)
- 10: 深度分析，原创洞见，引用丰富
- 7-9: 有深度，观点独到
- 4-6: 信息准确，表达清晰
- 1-3: 浅尝辄止或纯转述

### 时效性 (timeliness)
- 10: 正在发生的重大事件/刚发布的重要工具
- 7-9: 近期热点相关
- 4-6: 常青内容，不过时
- 1-3: 过时或无时效价值

## 分类标签

| 标签    | 说明           |
| ------- | -------------- |
| ai-ml   | AI / ML        |
| security | 安全          |
| engineering | 工程       |
| tools   | 工具 / 开源    |
| opinion | 观点 / 杂谈    |
| other   | 其他           |

## 性能参数

- **并发抓取**: 10 个 RSS 源同时请求
- **超时设置**: 15 秒/源
- **批处理**: 每次 10 篇文章一起评分
- **AI 并发**: 最多 2 个批处理同时进行

## 故障处理

脚本会自动跳过失败的 RSS 源，对 AI 调用失败返回默认分数（5/5/5）。部分源不可用不会影响整体运行。

## 输出位置

默认生成在当前目录：`./ai-daily-YYYYMMDD.md`

## 适用场景

- 公众号每日技术内容
- 团队技术资讯同步
- 个人技术信息筛选
- 行业趋势跟踪
