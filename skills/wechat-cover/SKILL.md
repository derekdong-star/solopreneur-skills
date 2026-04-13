---
name: wechat-cover
description: Generate WeChat official account cover images with proper 2.35:1 aspect ratio. Uses title-first prompt construction so the image concept matches the article title, with OpenAI- and Gemini-based generation.
---

# WeChat Cover Image Generator

Generate WeChat official account cover images with multi-provider support (OpenAI-compatible APIs or Gemini).

The generator is now **title-first**: it analyzes the article title before building the prompt, so the image concept is driven primarily by the title's subject, action, contrast, or transformation, while `--topic` acts as a secondary context signal.

## What Makes a Good WeChat Cover?

- **Aspect ratio**: 2.35:1 (wide cinematic format)
- **Time-prefixed filename**: Use `YYYY-MM-DD-wechat-cover-title.png` format.
- **No text**: WeChat overlays the article title
- **Visual focus**: One clear focal point, not cluttered
- **Clean & bright**: Modern aesthetic suitable for WeChat subscription feeds
- **Title relevance**: The scene should visualize the title's core idea, not just the broad topic

## Prompting Strategy

- **Title-first semantics**: The script parses the title to identify visual patterns such as transformation, contrast, guide/tutorial, warning/traps, or personal narrative.
- **Topic as secondary signal**: `--topic` still matters, but mainly for visual environment, style bias, and anti-cliche constraints.
- **Deterministic prompt selection**: Secondary visual hints are chosen deterministically from the title/topic, reducing random drift between runs.
- **Editorial composition**: The prompt reserves clean title-safe space and limits the image to a small number of meaningful elements.

Use this skill when the title itself contains a strong idea such as:

- `我把自己蒸馏成了一个 AI 技能包`
- `如何用 AI 写出更像人的公众号文章`
- `普通人做自媒体最容易踩的 3 个坑`

## Usage

**Basic generation:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "Your Article Title" \
  --topic "AI tools"
```

**With Gemini provider:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "Your Article Title" \
  --topic "AI tools" \
  --provider gemini
```

**With custom base URL (OpenAI-compatible proxy):**
```bash
export OPENAI_BASE_URL="https://your-proxy.com/v1"
export OPENAI_API_KEY="sk-..."

uv run skills/wechat-cover/scripts/generate.py \
  --title "Your Article Title" \
  --topic "AI tools" \
  --provider openai
```

**Inspect title analysis and final prompt without generating an image:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "我把自己蒸馏成了一个 AI 技能包" \
  --topic "AI tools" \
  --dry-run
```

**Override composition when you want a specific layout:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "普通人做自媒体最容易踩的 3 个坑" \
  --topic "content business" \
  --composition minimal
```

## Parameters

| Parameter       | Required | Description                                              |
| ---------------| -------- | -------------------------------------------------------- |
| `--title`      | Yes      | Article title. This is the primary semantic driver of the image concept |
| `--topic`      | Yes      | Topic/category. Secondary context used for style bias, environment, and anti-cliche constraints |
| `--provider`   | No       | `openai` (default) or `gemini`                         |
| `--base-url`   | No       | OpenAI-compatible base URL (env: OPENAI_BASE_URL)        |
| `--model`      | No       | Model name override                                      |
| `--style`      | No       | Style override: `default`, `tech`, `business`, `lifestyle`, `creative`, or a custom style string |
| `--composition`| No       | Composition override: `thirds`, `centered`, `minimal`, `split` |
| `--filename`   | No       | Output filename (auto-generated if omitted)               |
| `--resolution` | No       | 1K/2K/4K (default: 2K)                                |
| `--output-dir` | No       | Output directory (default: current directory)             |
| `--api-key`    | No       | API key (settings.json > env var)                        |
| `--dry-run`    | No       | Print title analysis and final prompt without calling the model |

## Interpreting `--dry-run`

`--dry-run` is the fastest way to judge whether title relevance is improving before you spend tokens on generation.

Look for these fields in the output:

- `Pattern`: whether the title is being recognized as transformation / guide / warning / etc.
- `Core subject`: whether the main object actually matches the title's key noun
- `Focal scene`: whether the image describes the title's action or contrast, not just its topic
- `Avoid`: whether the script is blocking obvious visual cliches for that category

## Configuration File (settings.json)

Copy the template and fill in your API keys:

```bash
cp skills/wechat-cover/settings.json.example skills/wechat-cover/settings.json
```

```json
{
  "openai": {
    "api_key": "sk-...",
    "base_url": "https://your-proxy.com/v1",
    "model": "dall-e-3"
  },
  "gemini": {
    "api_key": "your-gemini-key",
    "model": "gemini-3-pro-image-preview"
  },
  "default_provider": "openai",
  "default_resolution": "2K",
  "default_style": "default"
}
```

**OpenAI-compatible proxies** (e.g. palebluedot, new-api) that use `/v1/chat/completions` for image generation are auto-detected and supported. Set `base_url` and `model` accordingly.

**Priority order:** CLI argument > settings.json > environment variable

## Style Variants

These are editorial style biases, not replacements for title semantics. In most cases, the title analysis matters more than the style preset.

| Variant   | Description                                              |
|-----------|----------------------------------------------------------|
| `default` | Warm minimalist editorial look with soft natural light and generous negative space |
| `tech`    | Precise geometry, layered translucent surfaces, quiet innovation |
| `business`| Structured, architectural, calm authority |
| `lifestyle`| Natural textures, warmth, handcrafted calm |
| `creative`| Bold editorial asymmetry, tactile paper-cut energy |

## Composition Templates

| Template    | Use Case |
|-------------|----------|
| `thirds`    | Default editorial layout with safe title area on one side |
| `centered`  | Singular icon-like concept with strong symmetry |
| `minimal`   | Warning, trap, or extremely restrained concepts |
| `split`     | Transformation, contrast, before/after scenes |

## Environment Variables

| Variable           | Provider  | Description                              |
|-------------------|-----------|------------------------------------------|
| `OPENAI_API_KEY`  | openai    | OpenAI API key                           |
| `OPENAI_BASE_URL` | openai    | OpenAI-compatible proxy URL (optional)    |
| `GEMINI_API_KEY`  | gemini    | Gemini API key                           |

## Resolution Guide

| Resolution | Dimensions (OpenAI) | Dimensions (Gemini) | Use Case        |
|------------|---------------------|---------------------|-----------------|
| `1K`       | 1024×1024           | 1024×1024           | Preview/thumbnail |
| `2K`       | 1792×1024           | 2048×2048           | Standard cover   |
| `4K`       | 1792×1024           | 4096×4096           | High quality     |

Note: regardless of upstream provider size, the final output is normalized to **900×383 PNG** for WeChat cover use.

## Examples

**Tech article with OpenAI:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "2024年最值得学习的编程语言" \
  --topic "technology" \
  --style tech \
  --resolution 2K
```

**Business article with Gemini:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "职场沟通技巧" \
  --topic "business" \
  --style business \
  --provider gemini
```

**Lifestyle article:**
```bash
uv run skills/wechat-cover/scripts/generate.py \
  --title "周末去哪儿：杭州小众咖啡馆推荐" \
  --topic "lifestyle" \
  --style lifestyle \
  --output-dir ./covers
```

## Output

- Auto-cropped and resized to **900×383** (2.35:1 WeChat cover format)
- Both OpenAI and Gemini outputs are normalized to the same final WeChat cover dimensions
- Saves to specified directory (default: current directory)
- Filename format: `YYYY-MM-DD-wechat-cover-{title-slug}.png`
- Format: PNG for best quality

## Optimization Notes

- If the image feels generic, inspect `--dry-run` first and check whether the `Core subject` and `Focal scene` actually reflect the title.
- Prefer more specific titles over generic ones. `如何提高效率` will always be weaker than `我把周报流程压缩成了一个 10 分钟系统`.
- Use `--composition split` for titles with obvious before/after or transformation logic.
- Use `--composition minimal` for warning, risk, and trap-oriented titles.
- Use explicit `--style creative` or `--style business` only when you want to bias the visual language; do not rely on style alone to fix weak title relevance.

## Requirements

- `uv` installed for Python script execution
- `Pillow` (`pip install Pillow`) for image cropping/resizing
- **For OpenAI provider**: OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- **For Gemini provider**: Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
