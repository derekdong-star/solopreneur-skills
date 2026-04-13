#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai>=1.12.0",
#     "pillow>=10.0.0",
#     "google-genai>=0.8.0",
# ]
# ///
"""WeChat cover image generator with title-first prompt construction."""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Sequence


SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"


def load_settings() -> dict:
    """Load settings from settings.json if it exists."""
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


SETTINGS = load_settings()


from image_client import ImageClient, ImageGenerationError


@dataclass(frozen=True)
class VisualCue:
    """Visual building block matched from title or topic keywords."""

    keywords: tuple[str, ...]
    subject: str
    scene: str
    details: tuple[str, ...] = ()
    mood: str | None = None
    avoid: tuple[str, ...] = ()
    style: str | None = None


@dataclass(frozen=True)
class TitleAnalysis:
    """Structured interpretation of a title for prompt construction."""

    title: str
    pattern: str
    key_terms: tuple[str, ...]
    core_subject: str
    narrative: str
    focal_scene: str
    supporting_details: tuple[str, ...]
    mood: str
    title_safe_area: str
    avoid: tuple[str, ...]
    suggested_style: str | None = None


STYLE_VARIANTS: dict[str, str] = {
    "default": (
        "Warm minimalist editorial aesthetic. Color palette: cream white (#FAF9F6), warm beige (#F5F0EB), "
        "soft coral (#E8A87C), muted sage (#B5C4B1), warm gray (#C4C1BE). "
        "Clean organic shapes, soft natural light, generous negative space, smooth matte textures, "
        "and understated sophistication."
    ),
    "tech": (
        "Modern tech editorial aesthetic. Color palette: cool off-white (#F4F6F8), soft slate blue (#94A3B8), "
        "misty lavender (#C7D2FE), pale cyan (#A5F3FC), warm silver (#D1D5DB). "
        "Precise geometry, layered translucent surfaces, subtle glow, crisp hierarchy, and quiet innovation."
    ),
    "business": (
        "Professional editorial aesthetic. Color palette: warm white (#FEFDFB), navy accent (#1E3A5F), "
        "charcoal (#374151), amber accent (#D4A574), cool gray (#9CA3AF). "
        "Architectural lines, clear structure, calm authority, and premium print-ad restraint."
    ),
    "lifestyle": (
        "Warm lifestyle editorial aesthetic. Color palette: warm cream (#FFF8F0), blush pink (#F9E4D4), "
        "soft sage (#D4E2D0), golden hour (#F5D89A), terracotta (#D4956A). "
        "Natural textures, gentle curves, handcrafted warmth, and sunlit calm."
    ),
    "creative": (
        "Refined creative editorial aesthetic. Color palette: crisp white (#FFFFFF), coral red (#E06C5C), "
        "deep teal (#2D6A6A), golden yellow (#E9B44C), soft violet (#9B8EC2). "
        "Bold asymmetric composition, tactile paper-cut feeling, and surprising but controlled energy."
    ),
}


_TOPIC_VISUAL_HINTS: list[tuple[list[str], list[str]]] = [
    (
        ["ai", "artificial intelligence", "machine learning", "deep learning", "llm", "gpt", "claude", "agent"],
        [
            "a compact intelligence object unfolding with quiet internal logic",
            "a disciplined field of modular tiles exchanging soft signals",
            "a calm beam of structured light passing through nested translucent layers",
        ],
    ),
    (
        ["tech", "software", "programming", "code", "developer", "engineering", "api", "cloud"],
        [
            "an architectural build surface with rails, planes, and precise alignment",
            "stacked translucent system layers locking together in clean perspective",
            "a blueprint-like field with one decisive intervention that changes the whole system",
        ],
    ),
    (
        ["business", "startup", "entrepreneur", "growth", "revenue", "profit", "scale"],
        [
            "an elegant bridge or support structure under tension",
            "a path of deliberate stepping stones leading toward a brighter, more stable endpoint",
            "a structural frame that makes growth feel earned and load-bearing",
        ],
    ),
    (
        ["finance", "invest", "stock", "crypto", "blockchain", "defi", "trading"],
        [
            "a clean balance mechanism held in poised equilibrium",
            "a sharply defined boundary line between stability and volatility",
            "a branching structure whose geometry suggests risk and selection",
        ],
    ),
    (
        ["lifestyle", "food", "travel", "nature", "health", "fitness", "cooking"],
        [
            "warm natural textures with one hero object placed in generous breathing room",
            "a window-like opening into a calm, sunlit scene",
            "a tactile still life built from only a few seasonal elements",
        ],
    ),
    (
        ["design", "creative", "art", "aesthetic", "ui", "ux", "brand"],
        [
            "bold color fields cut into purposeful asymmetry",
            "one sculptural object casting a long, clean shadow on a pale ground",
            "a visible transition from rough sketch energy to refined final form",
        ],
    ),
]


_ACTION_CUES: tuple[VisualCue, ...] = (
    VisualCue(
        keywords=("蒸馏", "提炼", "浓缩", "压缩", "distill", "compress", "extract"),
        subject="a precise refinement chamber that separates noise from essence",
        scene="raw fragments passing through a clear refinement process and condensing into one compact high-value artifact",
        details=(
            "show at least one visible stage of filtering or condensation",
            "keep traces of discarded noise subtle and secondary",
        ),
        mood="focused, transformative, and quietly ambitious",
        avoid=("do not turn the image into a generic chemistry lab",),
        style="tech",
    ),
    VisualCue(
        keywords=("打包", "封装", "组装", "整合", "assemble", "package", "bundle"),
        subject="a deliberate assembly motion that turns scattered parts into one cohesive product",
        scene="discrete components locking into a finished object with satisfying precision",
        details=(
            "limit the scene to three to five components",
            "show the final assembled result as the clear hero",
        ),
        mood="organized, crisp, and purposeful",
        style="tech",
    ),
    VisualCue(
        keywords=("重构", "改造", "升级", "refactor", "rebuild", "upgrade"),
        subject="a restructuring mechanism that replaces fragile parts with stronger geometry",
        scene="an older form being rebuilt into a cleaner, sharper, more resilient structure",
        details=(
            "keep any scaffold or guide lines subtle",
            "the improved structure must dominate the frame",
        ),
        mood="decisive and constructive",
        style="business",
    ),
    VisualCue(
        keywords=("指南", "方法", "教程", "步骤", "攻略", "how", "guide", "method"),
        subject="a practical working surface that makes the promised method feel executable",
        scene="one main instrument and two supporting elements arranged as a clear process",
        details=(
            "make the sequence readable from left to right",
            "remove any decorative prop that does not support the method",
        ),
        mood="clear, actionable, and calm",
    ),
    VisualCue(
        keywords=("陷阱", "误区", "警惕", "不要", "别", "risk", "trap", "warning"),
        subject="a fragile threshold or false step that exposes hidden risk",
        scene="one confident path interrupted by a subtle but unmistakable hazard",
        details=(
            "the risky element should be readable at a glance",
            "the safer path should still be visible as a contrast",
        ),
        mood="grounded and cautionary",
        style="business",
    ),
    VisualCue(
        keywords=("为什么", "为何", "真相", "本质", "?", "？", "why"),
        subject="a reveal mechanism that shows the surface story and the hidden layer underneath",
        scene="one object opened, peeled back, or split to expose a more interesting inner structure",
        details=("the hidden layer should become the true focal point",),
        mood="curious and insightful",
    ),
    VisualCue(
        keywords=("写", "写作", "写出", "表达", "创作", "write", "writing"),
        subject="an authored editorial drafting scene",
        scene="draft material being refined into a more vivid and human final piece",
        details=(
            "show visible evolution from stiff draft to expressive finished form",
            "the final form should feel warmer and more alive than the initial draft",
        ),
        mood="crafted, human, and intelligent",
        style="creative",
    ),
    VisualCue(
        keywords=("坑", "踩坑", "误区", "陷阱", "错误", "踩的"),
        subject="a path or work surface interrupted by a few clear failure points",
        scene="three distinct weak spots or traps interrupting an otherwise orderly process",
        details=(
            "if the title mentions a number, make that count visible in the composition",
            "each trap should be simple and immediately legible",
        ),
        mood="warning-oriented but still editorial and controlled",
        style="business",
    ),
)


_SUBJECT_CUES: tuple[VisualCue, ...] = (
    VisualCue(
        keywords=("技能包", "toolkit", "工具包", "playbook", "系统", "system", "workflow"),
        subject="a premium toolkit case or modular set of capability tiles arranged with intent",
        scene="the result should look like a compact set of tools someone could immediately pick up and use",
        details=("three to five modules maximum", "slightly emphasize one hero module"),
        avoid=("no ecommerce packaging mockups", "no app-icon grids pretending to be a toolkit"),
        style="tech",
    ),
    VisualCue(
        keywords=("自己", "自我", "个人", "myself", "personal", "我"),
        subject="a faceless self-portrait built from layered paper or matte geometric forms",
        scene="the human element remains symbolic and universal, never portrait-like",
        details=("no facial features", "keep the silhouette simple and elegant"),
        avoid=("no realistic people",),
        style="creative",
    ),
    VisualCue(
        keywords=("ai", "人工智能", "智能体", "agent", "llm", "gpt", "claude"),
        subject="a compact intelligence object made of modular tiles, soft light, and precise internal logic",
        scene="the intelligence should feel tactile and designed rather than futuristic or sci-fi",
        details=("show quiet coordination between modules",),
        avoid=("no robots", "no holograms"),
        style="tech",
    ),
    VisualCue(
        keywords=("代码", "编程", "software", "code", "开发", "engineering", "api"),
        subject="an architectural blueprint or build surface translated into clean physical forms",
        scene="layers, rails, or plans should imply systems thinking without showing any screens",
        details=("keep the geometry crisp and load-bearing",),
        avoid=("no laptops", "no screenshots"),
        style="tech",
    ),
    VisualCue(
        keywords=("写作", "文章", "公众号", "title", "content", "内容"),
        subject="an editorial desk or publishing surface reduced to a few elegant forms",
        scene="the article should feel authored and shaped, not just decorated",
        details=(
            "protect a strong title-safe area",
            "show at least one authored page, card, or sheet-like form without any readable text",
        ),
        style="creative",
    ),
    VisualCue(
        keywords=("人", "像人", "human", "human-like", "真人"),
        subject="a warm human-authored artifact with subtle irregularity and tactile personality",
        scene="the human quality should appear through texture, rhythm, and crafted imperfection rather than through a face",
        details=(
            "avoid faces and body parts; communicate humanity through touch, rhythm, and analog warmth",
        ),
        avoid=("no portrait-style human figure",),
        style="creative",
    ),
    VisualCue(
        keywords=("自媒体", "公众号", "newsletter", "media", "publish"),
        subject="a publishing surface with layered cards, sheets, or editorial panels",
        scene="the media object should feel ready to publish, structured, and intentionally composed",
        details=(
            "keep the publishing forms abstract enough to avoid readable UI",
        ),
        avoid=("no social media app screenshots",),
        style="creative",
    ),
    VisualCue(
        keywords=("创业", "生意", "增长", "变现", "收入", "business", "startup", "growth"),
        subject="a bridge, path, or support structure that makes progress feel earned and structural",
        scene="progress should read as momentum built on sound support rather than hype",
        details=("show support and tension together",),
        style="business",
    ),
    VisualCue(
        keywords=("学习", "教程", "课程", "book", "reading", "study", "知识"),
        subject="an open book, learning apparatus, or stepping-stone structure with a clear direction",
        scene="learning should feel cumulative and directional rather than cluttered",
        details=("use one focal learning object, not a pile of books",),
        style="lifestyle",
    ),
    VisualCue(
        keywords=("时间", "效率", "productivity", "workflow", "日程"),
        subject="a planner, timeline, or time vessel reduced to one decisive form",
        scene="time should feel controlled and visible, never frantic",
        details=("show order replacing clutter",),
        style="business",
    ),
)


_TOPIC_STYLE_CHECKS: list[tuple[list[str], str]] = [
    (["tech", "ai", "software", "programming", "code", "computer", "digital", "data"], "tech"),
    (["business", "startup", "entrepreneur", "finance", "investment", "market"], "business"),
    (["life", "lifestyle", "food", "travel", "nature", "health", "fitness", "fashion"], "lifestyle"),
    (["creative", "art", "design", "photo", "video", "music"], "creative"),
]


_CLICHE_AVOID: dict[str, str] = {
    "ai": (
        "no neural network diagrams, no brain silhouettes, no node graphs, no glowing particle clouds, "
        "no matrix rain, no circuit-board AI metaphors"
    ),
    "tech": "no circuit board close-ups, no floating binary code, no screenshots, no generic laptop props",
    "finance": "no stock charts, no upward arrows, no currency symbols, no ticker overlays",
    "lifestyle": "no isolated coffee cup as the sole prop, no flat-lay phone-and-notebook cliches",
    "business": "no handshake imagery, no briefcase silhouettes, no motivational corporate stock-photo tropes",
    "toolkit": "no ecommerce packaging mockups, no app-icon grids pretending to be a toolkit",
}


COMPOSITION_TEMPLATES: dict[str, str] = {
    "thirds": (
        "Ultra-wide 2.35:1 aspect ratio. Put the hero subject on one third line, not in the middle. "
        "Keep the opposite side bright, quiet, and spacious for title overlay. One clear focal point only."
    ),
    "centered": (
        "Ultra-wide 2.35:1 aspect ratio. Use centered symmetry only when the title idea needs a singular icon-like statement. "
        "Surround the hero with generous empty space so the frame still feels editorial, not poster-like."
    ),
    "minimal": (
        "Ultra-wide 2.35:1 aspect ratio. Use extreme restraint: a single small-to-medium hero object against a pale field. "
        "Negative space must do real compositional work, not feel unfinished."
    ),
    "split": (
        "Ultra-wide 2.35:1 aspect ratio. Build a clear left-to-right transformation or contrast. "
        "One side should stay calmer and lighter to protect title readability, while the other side carries the scene."
    ),
}


_PATTERN_TO_COMPOSITION: dict[str, str] = {
    "transformation": "split",
    "contrast": "split",
    "journey": "split",
    "guide": "thirds",
    "framework": "thirds",
    "warning": "minimal",
    "question": "centered",
    "personal": "thirds",
    "statement": "thirds",
}


_MOOD_MAP: list[tuple[list[str], str]] = [
    (
        ["hope", "future", "breakthrough", "new", "opportunity", "新", "突破", "未来", "机遇", "崛起", "开始"],
        "optimistic, expansive, and filled with light",
    ),
    (
        ["risk", "warn", "danger", "trap", "fail", "注意", "警惕", "危机", "陷阱", "失败", "错误"],
        "cautionary, grounded, and slightly tense",
    ),
    (
        ["reflect", "think", "deep", "essence", "insight", "认知", "反思", "本质", "深度", "洞察", "理解"],
        "quiet, introspective, and layered",
    ),
    (
        ["how", "tool", "method", "practical", "guide", "实操", "技巧", "方法", "工具", "指南", "教程"],
        "clean, actionable, and structured",
    ),
    (
        ["earn", "money", "income", "monetize", "side", "赚", "变现", "收入", "副业", "盈利"],
        "aspirational but grounded in reality",
    ),
]


_TITLE_STOPWORDS = {
    "如何",
    "怎么",
    "怎样",
    "为什么",
    "为何",
    "一个",
    "一种",
    "一套",
    "真正的",
    "到底",
    "关于",
    "以及",
    "and",
    "the",
    "a",
    "an",
    "of",
    "to",
}


def stable_choice(options: Sequence[str], key: str) -> str:
    """Pick a stable option based on title/topic hash instead of randomness."""
    if not options:
        return ""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def normalize_text(text: str | None) -> str:
    """Normalize text for keyword matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def unique_strings(items: Sequence[str]) -> tuple[str, ...]:
    """Dedupe ordered strings while preserving first occurrence."""
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return tuple(result)


def cleanup_phrase(text: str) -> str:
    """Strip filler punctuation and common lead-in words from extracted phrases."""
    cleaned = re.sub(r"[\"'“”‘’《》【】()（）\[\]]", "", text)
    cleaned = re.sub(r"^(一个|一种|一套|一些|这篇|这套|如何|怎么|为什么|为何|到底|真正的|所谓的)\s*", "", cleaned)
    return cleaned.strip(" ：:，,。.!！？?；;\t\n")


def match_cues(text: str | None, cues: Sequence[VisualCue]) -> tuple[VisualCue, ...]:
    """Match ordered visual cues from a piece of text."""
    normalized = normalize_text(text)
    matches: list[VisualCue] = []
    for cue in cues:
        if any(keyword in normalized for keyword in cue.keywords):
            matches.append(cue)
    return tuple(matches)


def extract_transformation_terms(title: str) -> tuple[str, str] | None:
    """Extract source and target phrases from transformation-like titles."""
    patterns = (
        r"把(?P<source>.+?)(?:蒸馏|提炼|浓缩|压缩|打包|封装|改造|重构|变|做|炼)成(?:了)?(?P<target>.+)",
        r"(?P<source>.+?)变成(?:了)?(?P<target>.+)",
        r"从(?P<source>.+?)到(?P<target>.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            source = cleanup_phrase(match.group("source"))
            target = cleanup_phrase(match.group("target"))
            if source and target:
                return source, target
    return None


def extract_contrast_terms(title: str) -> tuple[str, str] | None:
    """Extract contrast pairs from titles like 'not X, but Y'."""
    patterns = (
        r"不是(?P<left>.+?)而是(?P<right>.+)",
        r"别再(?P<left>.+?)(?:了)?[，, ]+(?:要|而要)(?P<right>.+)",
    )
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            left = cleanup_phrase(match.group("left"))
            right = cleanup_phrase(match.group("right"))
            if left and right:
                return left, right
    return None


def infer_title_pattern(title: str) -> str:
    """Classify the title into a small set of scene patterns."""
    normalized = normalize_text(title)
    if extract_transformation_terms(title):
        return "transformation"
    if extract_contrast_terms(title):
        return "contrast"
    if re.search(r"从.+到.+", title):
        return "journey"
    if re.search(r"\d+\s*(个|种|步|条|招|原则|清单)", title) or any(word in normalized for word in ("清单", "框架", "模型")):
        return "framework"
    if any(word in normalized for word in ("如何", "怎么", "怎样", "指南", "教程", "方法", "攻略", "how")):
        return "guide"
    if any(word in normalized for word in ("陷阱", "误区", "警惕", "不要", "别", "risk", "trap", "warning")):
        return "warning"
    if "?" in title or "？" in title or any(word in normalized for word in ("为什么", "为何", "why", "真相", "本质")):
        return "question"
    if any(word in normalized for word in ("我", "自己", "我的", "我们", "personal")):
        return "personal"
    return "statement"


def extract_title_terms(title: str) -> tuple[str, ...]:
    """Extract a few explicit concepts from the title for prompt grounding."""
    normalized = normalize_text(title)
    collected: list[str] = []

    for cue in _ACTION_CUES + _SUBJECT_CUES:
        for keyword in cue.keywords:
            if len(keyword) == 1 and keyword not in {"我"}:
                continue
            if keyword and keyword in normalized:
                collected.append(keyword.upper() if keyword == "ai" else keyword)

    raw_chunks = re.split(r"[：:，,。.!！？?；;|/\\-]", title)
    for chunk in raw_chunks:
        cleaned = cleanup_phrase(chunk)
        if len(cleaned) < 2:
            continue
        if normalize_text(cleaned) in _TITLE_STOPWORDS:
            continue
        collected.append(cleaned)

    return unique_strings(collected)[:6]


def get_topic_visual_hint(topic: str | None, seed_key: str) -> str:
    """Pick a deterministic topic hint as a secondary background cue."""
    normalized = normalize_text(topic)
    if not normalized:
        return ""
    for keywords, hint_pool in _TOPIC_VISUAL_HINTS:
        if any(keyword in normalized for keyword in keywords):
            return stable_choice(hint_pool, f"{seed_key}:{keywords[0]}")
    return ""


def get_cliche_avoid(topic: str | None, title: str | None = None) -> str:
    """Return combined anti-cliche directives from title and topic signals."""
    combined = normalize_text(f"{title or ''} {topic or ''}")
    matched: list[str] = []
    for key, directive in _CLICHE_AVOID.items():
        if key in combined and directive not in matched:
            matched.append(directive)
    if any(keyword in combined for keyword in ("ai", "artificial intelligence", "machine learning", "llm", "gpt", "agent")):
        matched.append(_CLICHE_AVOID["ai"])
    if any(keyword in combined for keyword in ("tech", "software", "programming", "code", "developer", "api")):
        matched.append(_CLICHE_AVOID["tech"])
    if any(keyword in combined for keyword in ("finance", "invest", "stock", "crypto", "trading")):
        matched.append(_CLICHE_AVOID["finance"])
    if any(keyword in combined for keyword in ("skill", "toolkit", "技能包", "工具包")):
        matched.append(_CLICHE_AVOID["toolkit"])
    return "; ".join(unique_strings(matched))


def extract_title_mood(title: str) -> str:
    """Extract the emotional register implied by the title itself."""
    normalized = normalize_text(title)
    for keywords, mood in _MOOD_MAP:
        if any(keyword in normalized for keyword in keywords):
            return mood
    return ""


def resolve_mood(title: str, pattern: str, cues: Sequence[VisualCue]) -> str:
    """Resolve the final mood, preferring title keywords and cue defaults."""
    explicit = extract_title_mood(title)
    if explicit:
        return explicit
    for cue in cues:
        if cue.mood:
            return cue.mood
    pattern_defaults = {
        "transformation": "transformative, precise, and surprising",
        "contrast": "revealing and sharply differentiated",
        "journey": "forward-moving and deliberate",
        "guide": "practical and quietly confident",
        "framework": "structured, organized, and easy to parse",
        "warning": "tense but controlled",
        "question": "curious and layered",
        "personal": "personal yet editorial",
        "statement": "clear and authoritative",
    }
    return pattern_defaults.get(pattern, "calm and editorial")


def describe_phrase_as_object(phrase: str | None, topic: str | None = None) -> str:
    """Convert a title phrase into a concrete visual noun phrase."""
    cleaned = cleanup_phrase(phrase or "")
    if not cleaned:
        return get_topic_visual_hint(topic, topic or "general") or "a single clear editorial object"

    cue_matches = match_cues(cleaned, _SUBJECT_CUES)
    if cue_matches:
        primary = cue_matches[0].subject
        if len(cue_matches) > 1 and cue_matches[0].subject != cue_matches[1].subject:
            return f"{primary} infused with {cue_matches[1].subject}"
        return primary
    return f"a clean symbolic object that clearly represents {cleaned} without any text"


def build_title_analysis(title: str, topic: str | None) -> TitleAnalysis:
    """Turn a title into a structured visual brief."""
    pattern = infer_title_pattern(title)
    transformation = extract_transformation_terms(title)
    contrast = extract_contrast_terms(title)
    key_terms = extract_title_terms(title)
    action_cues = match_cues(title, _ACTION_CUES)
    subject_cues = list(match_cues(title, _SUBJECT_CUES))

    for cue in match_cues(topic, _SUBJECT_CUES):
        if cue not in subject_cues:
            subject_cues.append(cue)

    all_cues = tuple(list(action_cues) + subject_cues)
    supporting_details: list[str] = []
    avoid: list[str] = []

    for cue in all_cues[:4]:
        supporting_details.extend(cue.details)
        avoid.extend(cue.avoid)

    topic_hint = get_topic_visual_hint(topic, title)
    if topic_hint:
        supporting_details.append(f"secondary environment cue: {topic_hint}")

    mood = resolve_mood(title, pattern, all_cues)
    suggested_style = next((cue.style for cue in all_cues if cue.style), None)

    if transformation:
        source, target = transformation
        source_object = describe_phrase_as_object(source, topic)
        target_object = describe_phrase_as_object(target, topic)
        process_scene = action_cues[0].scene if action_cues else "a visible refinement or transformation mechanism"
        supporting_details.extend(
            [
                "both the source and the result must be visible in one frame",
                "the result should feel more compact, useful, and finished than the source",
            ]
        )
        avoid.extend(
            [
                "do not show only the processing device",
                "do not hide either the source state or the result state",
            ]
        )
        return TitleAnalysis(
            title=title,
            pattern=pattern,
            key_terms=key_terms,
            core_subject=target_object,
            narrative=(
                f"Show {source} being transformed into {target}. The viewer should grasp both the origin "
                f"and the distilled result before reading the article."
            ),
            focal_scene=(
                f"One elegant transformation scene: {source_object} enters {process_scene}, then resolves into "
                f"{target_object} as the hero outcome."
            ),
            supporting_details=unique_strings(supporting_details),
            mood=mood,
            title_safe_area="Reserve the left 35-40% as bright, uncluttered negative space for the title overlay.",
            avoid=unique_strings(avoid),
            suggested_style=suggested_style,
        )

    if contrast:
        left, right = contrast
        left_object = describe_phrase_as_object(left, topic)
        right_object = describe_phrase_as_object(right, topic)
        supporting_details.extend(
            [
                "the wrong answer should be visibly weaker and more faded",
                "the correct answer should own the sharpest contrast and clearest form",
            ]
        )
        return TitleAnalysis(
            title=title,
            pattern=pattern,
            key_terms=key_terms,
            core_subject=right_object,
            narrative=f"Stage a contrast between {left} and {right}, making {right} unmistakably stronger and clearer.",
            focal_scene=(
                f"A split but cohesive editorial scene where {left_object} recedes while {right_object} becomes "
                f"the decisive focal point."
            ),
            supporting_details=unique_strings(supporting_details),
            mood=mood,
            title_safe_area="Reserve the lighter side of the split composition as calm negative space for title overlay.",
            avoid=unique_strings(avoid),
            suggested_style=suggested_style,
        )

    if pattern == "guide" and any(term in normalize_text(title) for term in ("写", "写作", "写出", "文章", "公众号", "content")):
        supporting_details.extend(
            [
                "show a clear before-and-after editorial artifact, not just an abstract AI object",
                "the final artifact should feel more human through warmth, rhythm, and crafted imperfection",
                "avoid readable text while still making the object unmistakably editorial",
            ]
        )
        return TitleAnalysis(
            title=title,
            pattern=pattern,
            key_terms=key_terms,
            core_subject="a publishing artifact being transformed from machine-stiff draft into warm human-authored editorial form",
            narrative="Show AI assisting the writing process, but make the end result feel distinctly more human, authored, and publishable.",
            focal_scene=(
                "A refined editorial drafting scene: one stiff, over-regular draft card transitions into a warmer, more tactile publication card, "
                "with an AI system object acting only as a supporting tool rather than the hero."
            ),
            supporting_details=unique_strings(supporting_details),
            mood="crafted, intelligent, and human-centered",
            title_safe_area="Reserve the cleaner side of the frame for title overlay, keeping the drafted-to-published transition on the opposite side.",
            avoid=unique_strings(list(avoid) + ["do not let the AI object dominate more than the editorial artifact"]),
            suggested_style="creative",
        )

    if any(term in normalize_text(title) for term in ("坑", "踩坑", "误区", "陷阱", "错误")):
        trap_count_match = re.search(r"(\d+)", title)
        trap_count = trap_count_match.group(1) if trap_count_match else "multiple"
        supporting_details.extend(
            [
                f"make {trap_count} trap points visible as distinct interruptions or weak spots",
                "the safe path or correct structure should remain visible as contrast",
                "do not turn the composition into an infographic; keep it editorial and minimal",
            ]
        )
        return TitleAnalysis(
            title=title,
            pattern="warning",
            key_terms=key_terms,
            core_subject="an editorial process surface with clearly visible trap points",
            narrative="Visualize the most common failure points so the danger is obvious before the article is read.",
            focal_scene=(
                "A clean publishing or creator workflow path interrupted by clearly visible trap points, where the wrong steps feel fragile and the safe route stays readable."
            ),
            supporting_details=unique_strings(supporting_details),
            mood="cautionary, clear, and editorial",
            title_safe_area="Reserve bright negative space on one side for the title, while the trap sequence sits on the opposite side.",
            avoid=unique_strings(list(avoid) + ["do not use warning icons, exclamation marks, or infographic labels"]),
            suggested_style="business",
        )

    hero_subject = subject_cues[0].subject if subject_cues else describe_phrase_as_object(next(iter(key_terms), title), topic)
    pattern_narratives = {
        "journey": "Create a before-to-after scene that makes progress visible and directional.",
        "guide": "Translate the promise of the title into a concrete scene that feels immediately usable.",
        "framework": "Show a small structured set of elements that implies a framework, not a pile of unrelated props.",
        "warning": "Make the hidden risk obvious without turning the image melodramatic.",
        "question": "Build a scene that invites curiosity by exposing a hidden layer or surprising structure.",
        "personal": "Keep the image personal and specific, but still editorial and broadly legible.",
        "statement": "Make the title feel specific and consequential rather than generic.",
    }
    pattern_scene = {
        "journey": f"A directional scene built around {hero_subject}, with a visible start state and a more refined destination.",
        "guide": f"A practical editorial still life built around {hero_subject}, arranged as a clear process with one hero object and two supporting elements.",
        "framework": f"A structured set built around {hero_subject}, using only a few parts with obvious hierarchy and spacing.",
        "warning": f"A minimal but tense scene built around {hero_subject}, where one subtle hazard changes how the whole frame is read.",
        "question": f"A reveal-based scene built around {hero_subject}, with one opened or peeled-back element exposing the real idea underneath.",
        "personal": f"A symbolic self-authored scene built around {hero_subject}, with a crafted feel instead of a generic stock illustration.",
        "statement": f"One unmistakable hero scene built around {hero_subject}, designed so the title concepts feel inferable without text.",
    }
    supporting_details.append("make these title concepts inferable without text: " + ", ".join(key_terms[:4] or (title,)))

    return TitleAnalysis(
        title=title,
        pattern=pattern,
        key_terms=key_terms,
        core_subject=hero_subject,
        narrative=pattern_narratives.get(pattern, pattern_narratives["statement"]),
        focal_scene=pattern_scene.get(pattern, pattern_scene["statement"]),
        supporting_details=unique_strings(supporting_details),
        mood=mood,
        title_safe_area="Reserve one side of the frame as clean, bright breathing room for the title overlay.",
        avoid=unique_strings(avoid),
        suggested_style=suggested_style,
    )


def get_style(topic: str | None, style_arg: str | None, analysis: TitleAnalysis | None = None) -> str:
    """Resolve the style variant, preferring explicit choice and title-derived hints."""
    if style_arg is not None:
        if style_arg in STYLE_VARIANTS:
            return STYLE_VARIANTS[style_arg]
        return style_arg

    if analysis and analysis.suggested_style and analysis.suggested_style in STYLE_VARIANTS:
        return STYLE_VARIANTS[analysis.suggested_style]

    if topic:
        topic_lower = normalize_text(topic)
        for keywords, style_name in _TOPIC_STYLE_CHECKS:
            if any(keyword in topic_lower for keyword in keywords):
                return STYLE_VARIANTS[style_name]

    return STYLE_VARIANTS["default"]


def resolve_composition(pattern: str, composition: str | None) -> tuple[str, str]:
    """Choose a composition template from explicit arg or title pattern."""
    key = composition if composition in COMPOSITION_TEMPLATES else _PATTERN_TO_COMPOSITION.get(pattern, "thirds")
    return key, COMPOSITION_TEMPLATES[key]


def format_title_analysis(analysis: TitleAnalysis) -> str:
    """Readable debug output for dry-run mode."""
    details = "\n".join(f"- {detail}" for detail in analysis.supporting_details)
    avoids = "\n".join(f"- {item}" for item in analysis.avoid)
    return (
        f"Pattern: {analysis.pattern}\n"
        f"Key terms: {', '.join(analysis.key_terms) or '(none)'}\n"
        f"Core subject: {analysis.core_subject}\n"
        f"Narrative: {analysis.narrative}\n"
        f"Focal scene: {analysis.focal_scene}\n"
        f"Mood: {analysis.mood}\n"
        f"Title-safe area: {analysis.title_safe_area}\n"
        f"Supporting details:\n{details or '- none'}\n"
        f"Avoid:\n{avoids or '- none'}"
    )


def build_prompt(
    title: str,
    topic: str | None,
    style: str | None = None,
    composition: str | None = None,
) -> tuple[str, TitleAnalysis]:
    """Build a title-first image generation prompt and return the analysis used."""
    analysis = build_title_analysis(title, topic)
    resolved_style = get_style(topic, style, analysis)
    composition_key, composition_text = resolve_composition(analysis.pattern, composition)
    cliche_avoid = get_cliche_avoid(topic, title)

    detail_lines = "\n".join(f"- {detail}" for detail in analysis.supporting_details[:6])
    avoid_parts = [
        "No text, no letters, no numbers, no watermarks, no logos, no UI elements.",
        "No photorealism, no dark muddy backgrounds, no neon palettes, no clutter, no heavy shadows.",
        "No faces, no stock-photo posing, no decorative filler that does not help explain the title.",
        "Do not make a generic topic illustration; the title-specific idea must be obvious even without reading the text.",
    ]
    if analysis.avoid:
        avoid_parts.append("Title-specific avoid: " + "; ".join(analysis.avoid) + ".")
    if cliche_avoid:
        avoid_parts.append("Category-specific avoid: " + cliche_avoid + ".")

    prompt = f"""Article title: \"{title}\"
Topic: {topic or "general"}

MISSION:
Design a WeChat article cover that feels premium and surprising, but is unmistakably tied to the article title. The reader should infer the title's core idea from the image alone.

TITLE ANALYSIS:
Pattern: {analysis.pattern}
Key concepts: {', '.join(analysis.key_terms) or title}
Core subject: {analysis.core_subject}
Narrative goal: {analysis.narrative}
Focal scene: {analysis.focal_scene}
Emotional register: {analysis.mood}

STYLE:
{resolved_style}

COMPOSITION ({composition_key}):
{composition_text}
{analysis.title_safe_area}

VISUAL BUILD:
Render as a clean, stylized editorial illustration, not a photograph.
Use simplified geometric forms, tactile matte surfaces, and restrained gradients.
Maximum 2-4 visual elements with one dominant hero object.
Supporting details:
{detail_lines or '- none'}

LIGHTING AND FINISH:
Soft diffused light, premium print-ad feel, crisp edges, calm contrast, matte texture, bright overall value range.

AVOID:
{' '.join(avoid_parts)}"""

    return prompt.strip(), analysis


def generate_filename(title: str) -> str:
    """Generate a safe filename based on title and timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]", " ", title)
    words = cleaned.split()[:4]
    short_title = "-".join(words).lower()
    short_title = "".join(c for c in short_title if c.isalnum() or c in "-\u4e00-\u9fff")[:40]
    if not short_title:
        short_title = "untitled"
    return f"{timestamp}-wechat-cover-{short_title}.png"


def resolve_provider(
    provider: Literal["openai", "gemini"],
    base_url: str | None,
    model: str | None,
) -> ImageClient:
    """Resolve the image generation provider to a client instance."""
    provider_settings = SETTINGS.get(provider, {})

    if provider == "openai":
        from openai_client import OpenAIImageClient

        model_name = model or provider_settings.get("model", "dall-e-3")
        resolved_base_url = base_url or provider_settings.get("base_url")
        return OpenAIImageClient(model=model_name, base_url=resolved_base_url)
    if provider == "gemini":
        from gemini_client import GeminiImageClient

        model_name = model or provider_settings.get("model", "gemini-3-pro-image-preview")
        return GeminiImageClient(model=model_name)
    raise ValueError(f"Unknown provider: {provider}")


def get_api_key_for_provider(provider: Literal["openai", "gemini"], api_key: str | None) -> str:
    """Get the API key for the specified provider."""
    if api_key:
        return api_key

    provider_settings = SETTINGS.get(provider, {})
    if provider_settings.get("api_key"):
        return provider_settings["api_key"]

    env_vars = {
        "openai": ["OPENAI_API_KEY", "OPENAI_API_KEY_1"],
        "gemini": ["GEMINI_API_KEY", "GEMINI_API_KEY_1"],
    }

    for env_var in env_vars.get(provider, []):
        key = os.environ.get(env_var)
        if key:
            return key

    raise ValueError(
        f"No API key provided for {provider}. "
        f"Set it in settings.json, {env_vars[provider][0]} environment variable, or use --api-key argument."
    )


def retry_with_backoff(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> None:
    """Retry a function with exponential backoff."""
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= backoff_factor

    raise last_exception


def main() -> None:
    """CLI entry point."""
    default_provider = SETTINGS.get("default_provider", "openai")
    default_resolution = SETTINGS.get("default_resolution", "2K")
    default_style = SETTINGS.get("default_style")
    default_base_url = SETTINGS.get("openai", {}).get("base_url") or os.environ.get("OPENAI_BASE_URL")

    parser = argparse.ArgumentParser(
        description="Generate WeChat cover images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--topic", required=True, help="Topic/category")
    parser.add_argument(
        "--provider",
        default=default_provider,
        choices=["openai", "gemini"],
        help=f"Image generation provider (default: {default_provider})",
    )
    parser.add_argument(
        "--base-url",
        default=default_base_url,
        help="Base URL for OpenAI-compatible API (default: from settings.json or OPENAI_BASE_URL env var)",
    )
    parser.add_argument("--model", help="Model override")
    parser.add_argument(
        "--style",
        default=default_style,
        help="Style variant (default, tech, business, lifestyle, creative) or custom style string",
    )
    parser.add_argument("--filename", help="Output filename (auto-generated if not provided)")
    parser.add_argument(
        "--resolution",
        default=default_resolution,
        choices=["1K", "2K", "4K"],
        help=f"Image resolution (default: {default_resolution})",
    )
    parser.add_argument("--output-dir", default=".", help="Output directory (default: current directory)")
    parser.add_argument("--api-key", help="API key (or set in settings.json / environment variable)")
    parser.add_argument(
        "--composition",
        choices=list(COMPOSITION_TEMPLATES.keys()),
        help="Composition template override",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print title analysis and final prompt without calling the image model",
    )

    args = parser.parse_args()

    filename = args.filename or generate_filename(args.title)
    output_dir = Path(args.output_dir)
    output_path = output_dir / filename

    prompt, analysis = build_prompt(args.title, args.topic, args.style, args.composition)
    resolved_style = get_style(args.topic, args.style, analysis)

    print(f"Generating WeChat cover for: {args.title}")
    print(f"Topic: {args.topic}")
    print(f"Style: {resolved_style[:80]}...")
    print(f"Provider: {args.provider}")
    print(f"Resolution: {args.resolution}")
    print(f"Output: {output_path}")
    print()
    print("--- Title analysis ---")
    print(format_title_analysis(analysis))
    print("--- End analysis ---")
    print()
    print("--- Prompt preview ---")
    print(prompt)
    print("--- End prompt ---")
    print()

    if args.dry_run:
        return

    try:
        api_key = get_api_key_for_provider(args.provider, args.api_key)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        client = resolve_provider(args.provider, args.base_url, args.model)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    def generate_image() -> None:
        client.generate(
            prompt=prompt,
            filename=str(output_path),
            resolution=args.resolution,
            api_key=api_key,
        )

    try:
        retry_with_backoff(generate_image)
        print(f"Successfully generated: {output_path}")
    except ImageGenerationError as e:
        print(f"Error generating image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
