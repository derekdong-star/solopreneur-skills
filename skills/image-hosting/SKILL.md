---
name: image-hosting
description: |
  Upload images to Derek's GitHub image hosting repo (derekdong-star/image-hosting) through a dedicated uploader script, then return a public raw URL and Markdown image link. Use when: (1) user asks to upload or host an image, (2) a generated image needs a public link (e.g. wechat cover), (3) any image file needs to be accessible via URL. Triggers on phrases like "上传图片", "获取图片链接", "图床", "public link for image", "host this image", "upload to github".
---

# Image Hosting Skill

Upload images to `derekdong-star/image-hosting` on GitHub with `scripts/upload.py`, then return a public `raw.githubusercontent.com` URL and a ready-to-paste Markdown image link.

Prefer the script over manual `git` commands. It adds preflight checks, safer staging, filename normalization, and collision handling.

## Repo Structure

```
derekdong-star/image-hosting/
├── wechat-covers/     # WeChat article cover images (2.35:1)
├── screenshots/       # App or web screenshots
├── diagrams/          # Architecture or flow diagrams
├── photos/            # General photos
└── misc/              # Everything else
```

## Directory Selection

| Image type            | Directory       |
|-----------------------|-----------------|
| WeChat cover          | `wechat-covers` |
| Screenshot / UI       | `screenshots`   |
| Diagram / flowchart   | `diagrams`      |
| Photo                 | `photos`        |
| Other / unclear       | `misc`          |

## Naming Convention

Use the existing filename if it already follows a date-prefixed format (`YYYY-MM-DD-*` or `YYYY-MM-DD-HHMMSS-*`).
Otherwise rename to: `YYYY-MM-DD-HHMMSS-<short-slug>.<ext>`
- Use the current local date and time
- slug: lowercase, hyphens, no spaces, max ~40 chars
- Keep original extension (`.png`, `.jpg`, etc.)
- If the target filename already exists, append `-2`, `-3`, etc. instead of overwriting

## Recommended Usage

```bash
uv run skills/image-hosting/scripts/upload.py \
  "/absolute/path/to/image.png"
```

The script now asks for confirmation before it copies, commits, and pushes. Use `--yes` only in trusted or non-interactive flows.

### Common Variants

```bash
# Force target directory
uv run skills/image-hosting/scripts/upload.py \
  "/absolute/path/to/cover.png" \
  --directory wechat-covers

# Non-interactive upload when you have already verified the target
uv run skills/image-hosting/scripts/upload.py \
  "/absolute/path/to/cover.png" \
  --directory wechat-covers \
  --yes

# Dry run: inspect inferred repo path and public URL without changing anything
uv run skills/image-hosting/scripts/upload.py \
  "/absolute/path/to/screenshot.png" \
  --dry-run

# Custom target filename (must keep original extension)
uv run skills/image-hosting/scripts/upload.py \
  "/absolute/path/to/diagram.png" \
  --directory diagrams \
  --filename 2026-04-13-system-overview.png
```

## What The Script Handles

- Clones the repo to `/tmp/image-hosting` if needed
- Verifies the local repo is actually `derekdong-star/image-hosting`
- Refuses to continue if the local repo has uncommitted changes
- Fast-forwards `main` before uploading
- Auto-infers the directory when `--directory` is omitted
- Preserves date-prefixed filenames, otherwise generates a timestamped slug
- Stages only the uploaded file instead of using `git add .`
- Requires an explicit confirmation unless `--yes` is passed
- Returns the repo path, raw URL, Markdown image link, and commit SHA

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `source` | Yes | Local image path |
| `--directory` | No | One of `wechat-covers`, `screenshots`, `diagrams`, `photos`, `misc` |
| `--filename` | No | Explicit target filename; must keep original extension |
| `--repo-dir` | No | Override local clone path (default: `/tmp/image-hosting`) |
| `--repo-url` | No | Override git remote URL |
| `--dry-run` | No | Print inferred result without copy / commit / push |
| `--yes` | No | Skip confirmation prompt and upload immediately |

## Preflight Rules

- Only upload files that already exist locally
- Allowed extensions: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.svg`
- Never upload files larger than 50MB
- Do not proceed if `/tmp/image-hosting` contains unrelated uncommitted changes
- Do not overwrite an existing file with the same name
- Default to prompting before upload so the final target path is visible

## Output

After a successful push, return:

- Public raw URL
- Markdown image link
- Repo relative path
- Commit SHA

Example raw URL:

```
https://raw.githubusercontent.com/derekdong-star/image-hosting/main/<directory>/<filename>
```

## Notes

- If directory inference is ambiguous, pass `--directory` explicitly
- The script currently prefers ASCII slugs for generated filenames; date-prefixed source filenames are kept as-is
- In CI or other non-interactive flows, pass `--yes` or the prompt will fail closed
- If GitHub authentication is not available locally, `git push` will fail and must be fixed outside the skill
