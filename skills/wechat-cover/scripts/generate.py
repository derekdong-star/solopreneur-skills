#!/usr/bin/env python3
"""
WeChat Cover Image Generator
Generates cover images optimized for WeChat official accounts (2.35:1 aspect ratio)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Add nano-banana scripts to path
SCRIPT_DIR = Path(__file__).parent.resolve()
NANO_BANANA_SCRIPT = SCRIPT_DIR / "nano_banana.py"

STYLE_PRESETS = {
    "tech": "futuristic digital art, neon accents, glowing elements, modern technology aesthetic",
    "AI": "futuristic digital art, neural network visualization, holographic interfaces, glowing data streams",
    "programming": "clean code aesthetic, matrix-style elements, modern tech workspace, blue tones",
    "food": "warm food photography, rustic styling, natural lighting, appetizing presentation",
    "cooking": "warm kitchen atmosphere, steam rising, natural lighting, cozy rustic feel",
    "recipe": "overhead food shot, vibrant colors, clean styling, professional food photography",
    "travel": "cinematic landscape, golden hour lighting, breathtaking vista, wanderlust aesthetic",
    "nature": "stunning natural scenery, golden hour, peaceful atmosphere, vivid colors",
    "outdoor": "adventure photography, dramatic sky, wide open spaces, inspiring view",
    "business": "clean corporate aesthetic, professional blue tones, modern office, sleek design",
    "finance": "abstract financial visualization, gold and blue tones, data flowing, professional",
    "startup": "modern entrepreneurial vibe, city skyline, innovation aesthetic, energetic",
    "fashion": "elegant editorial photography, soft lighting, high fashion aesthetic, luxurious",
    "beauty": "soft glowing portrait aesthetic, pastel tones, dreamy lighting, elegant",
    "health": "energetic vibrant colors, motion blur, fitness aesthetic, motivating atmosphere",
    "fitness": "dynamic action shot, strong lighting, gym aesthetic, powerful composition",
    "lifestyle": "cozy lifestyle photography, warm tones, hygge aesthetic, comfortable scene",
    "education": "clean academic aesthetic, books and learning, warm library lighting, scholarly",
    "art": "creative artistic composition, bold colors, gallery aesthetic, inspiring",
    "design": "modern design aesthetic, geometric elements, clean lines, creative composition",
}

def get_default_style(topic: str) -> str:
    """Get default style based on topic keywords"""
    topic_lower = topic.lower()
    for keyword, style in STYLE_PRESETS.items():
        if keyword in topic_lower:
            return style
    return "professional photography, clean composition, visually striking, modern aesthetic"

def build_prompt(title: str, topic: str, style: str = None) -> str:
    """Build the image generation prompt for WeChat cover"""
    if style is None:
        style = get_default_style(topic)
    
    prompt = f"""Create a stunning WeChat article cover image for an article titled: "{title}"

Topic: {topic}
Style: {style}

Requirements:
- Wide cinematic composition suitable for 2.35:1 aspect ratio (cover image format)
- Visually striking and attention-grabbing for social media feed
- NO TEXT, NO WORDS, NO LETTERS, NO WATERMARKS (absolutely no typography)
- Image should hint at the article topic through visual metaphors and composition
- High contrast and vibrant colors to stand out in subscription feeds
- Professional quality, magazine cover level
- Single clear focal point, not cluttered
- Suitable for overlaying white or black text title on top

The image should evoke curiosity and make viewers want to click to read the article."""
    
    return prompt

def generate_filename(title: str) -> str:
    """Generate filename based on title and timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    # Extract key words from title (first 3-4 words)
    words = title.replace(":", "").replace("，", "-").replace("。", "").split()[:4]
    short_title = "-".join(words).lower()
    short_title = "".join(c for c in short_title if c.isalnum() or c == "-")[:30]
    return f"{timestamp}-wechat-cover-{short_title}.png"

def main():
    parser = argparse.ArgumentParser(description="Generate WeChat cover images")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--topic", required=True, help="Topic/category")
    parser.add_argument("--style", help="Visual style (auto-selected if not provided)")
    parser.add_argument("--filename", help="Output filename (auto-generated if not provided)")
    parser.add_argument("--resolution", default="2K", choices=["1K", "2K", "4K"], help="Image resolution")
    parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: No API key provided.")
        print("Please either:")
        print("  1. Provide --api-key argument")
        print("  2. Set GEMINI_API_KEY environment variable")
        sys.exit(1)
    
    # Check if nano_banana.py exists
    if not NANO_BANANA_SCRIPT.exists():
        print(f"Error: nano_banana.py not found at: {NANO_BANANA_SCRIPT}")
        print("Please ensure nano_banana.py is in the same directory as generate.py")
        sys.exit(1)
    
    # Generate filename if not provided
    filename = args.filename or generate_filename(args.title)
    
    # Build prompt
    prompt = build_prompt(args.title, args.topic, args.style)
    
    print(f"Generating WeChat cover for: {args.title}")
    print(f"Topic: {args.topic}")
    print(f"Style: {args.style or get_default_style(args.topic)}")
    print(f"Resolution: {args.resolution}")
    print(f"Output: {filename}")
    print()
    
    # Build and execute command
    cmd = [
        "uv", "run", str(NANO_BANANA_SCRIPT),
        "--prompt", prompt,
        "--filename", filename,
        "--resolution", args.resolution,
        "--api-key", api_key
    ]
    
    os.execvp("uv", cmd)

if __name__ == "__main__":
    main()
