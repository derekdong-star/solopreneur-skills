---
name: wechat-cover
description: Generate WeChat official account cover images with proper 2.35:1 aspect ratio. Creates visually striking, topic-appropriate cover images without text (WeChat adds its own title overlay).
---

# WeChat Cover Image Generator

Generate professional cover images for WeChat official account articles.

## What Makes a Good WeChat Cover?

- **Aspect ratio**: 2.35:1 (recommended: 900×383px or 1280×545px)
- **Time-prefixed filename**: Use `YYYY-MM-DD-wechat-cover-title.png` format.
- **No text**: WeChat overlays the article title
- **Visual focus**: One clear focal point, not cluttered
- **Topic match**: Image should hint at article content
- **High contrast**: Stands out in the subscription feed

## Usage

**Basic generation:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "Your Article Title" \
  --topic "AI tools" \
  --filename "cover.png"
```

**With specific style:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "5分钟上手 Nano Banana Pro" \
  --topic "AI art generation" \
  --style "futuristic digital art" \
  --filename "nano-banana-cover.png" \
  --api-key YOUR_KEY
```

## Parameters

| Parameter      | Required | Description                                              |
| -------------- | -------- | -------------------------------------------------------- |
| `--title`      | Yes      | Article title (used to understand context)               |
| `--topic`      | Yes      | Topic/category (e.g., "technology", "cooking", "travel") |
| `--style`      | No       | Visual style (defaults based on topic)                   |
| `--filename`   | No       | Output filename (auto-generated if omitted)              |
| `--resolution` | No       | 1K/2K/4K (default: 2K)                                   |
| `--api-key`    | Yes*     | Gemini API key or set GEMINI_API_KEY env                 |

## Examples

**Tech article:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "2024年最值得学习的编程语言" \
  --topic "technology programming" \
  --style "clean minimalist tech aesthetic"
```

**Lifestyle article:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "周末去哪儿：杭州小众咖啡馆推荐" \
  --topic "lifestyle coffee travel" \
  --style "warm cozy photography"
```

**Business article:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "小红书运营避坑指南" \
  --topic "social media business" \
  --style "modern professional corporate"
```

## Style Presets

If you don't specify `--style`, the skill picks based on topic:

| Topic Keywords          | Default Style                         |
| ----------------------- | ------------------------------------- |
| tech, AI, programming   | futuristic digital art, neon accents  |
| food, cooking, recipe   | warm food photography, rustic styling |
| travel, nature, outdoor | cinematic landscape, golden hour      |
| business, finance       | clean corporate, blue tones           |
| fashion, beauty         | elegant editorial, soft lighting      |
| health, fitness         | energetic vibrant, motion blur        |

## Output

- Saves to current directory
- Filename format: `YYYY-MM-DD-wechat-cover.png` (if not specified)
- Resolution: 2K by default (good balance of quality and size)

## Requirements

- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- `uv` installed for Python script execution
