#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Upload an image into the GitHub-backed image hosting repository."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_REPO_URL = "https://github.com/derekdong-star/image-hosting.git"
DEFAULT_REPO_DIR = Path("/tmp/image-hosting")
DEFAULT_BRANCH = "main"
RAW_BASE_URL = "https://raw.githubusercontent.com/derekdong-star/image-hosting/main"
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:-\d{6})?-")
SAFE_SLUG_RE = re.compile(r"[^a-z0-9]+")


DIRECTORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wechat-covers", ("wechat", "cover", "公众号", "封面")),
    ("screenshots", ("screenshot", "screen", "ui", "界面", "截图")),
    ("diagrams", ("diagram", "flow", "architecture", "架构", "流程", "图")),
    ("photos", ("photo", "image", "picture", "照片", "拍摄")),
)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
MAX_FILE_BYTES = 50 * 1024 * 1024


class UploadError(RuntimeError):
    """Raised when the upload flow cannot continue safely."""


@dataclass(frozen=True)
class UploadResult:
    repo_path: str
    raw_url: str
    markdown: str
    commit: str


@dataclass(frozen=True)
class UploadPlan:
    source: Path
    repo_dir: Path
    selected_dir: str
    target_path: Path
    repo_relative: str
    raw_url: str


def run_git(args: list[str], repo_dir: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_repo(repo_dir: Path, repo_url: str) -> None:
    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", repo_url, str(repo_dir)],
            text=True,
            check=True,
        )

    if not (repo_dir / ".git").exists():
        raise UploadError(f"Target repo dir is not a git repository: {repo_dir}")

    remote = run_git(["remote", "get-url", "origin"], repo_dir).stdout.strip()
    if normalize_git_url(remote) != normalize_git_url(repo_url):
        raise UploadError(
            f"Repo remote mismatch: expected {repo_url}, got {remote}. "
            "Use --repo-dir with a clean clone or fix origin first."
        )

    status = run_git(["status", "--porcelain"], repo_dir).stdout.strip()
    if status:
        raise UploadError(
            f"Repo has uncommitted changes in {repo_dir}. "
            "Commit/stash them first to avoid mixing uploads."
        )

    run_git(["fetch", "origin", DEFAULT_BRANCH], repo_dir)

    current_branch = run_git(["branch", "--show-current"], repo_dir).stdout.strip()
    if current_branch != DEFAULT_BRANCH:
        run_git(["checkout", DEFAULT_BRANCH], repo_dir)

    run_git(["pull", "--ff-only", "origin", DEFAULT_BRANCH], repo_dir)


def normalize_git_url(url: str) -> str:
    if url.startswith("git@github.com:"):
        return url.removeprefix("git@github.com:").removesuffix(".git")
    parsed = urlparse(url)
    if parsed.netloc == "github.com":
        return parsed.path.strip("/").removesuffix(".git")
    return url.removesuffix(".git")


def infer_directory(source: Path) -> str:
    hint = source.name.lower()
    for directory, keywords in DIRECTORY_RULES:
        if any(keyword in hint for keyword in keywords):
            return directory
    return "misc"


def build_raw_base_url(repo_url: str, branch: str) -> str:
    normalized = normalize_git_url(repo_url)
    if "/" not in normalized:
        return RAW_BASE_URL
    return f"https://raw.githubusercontent.com/{normalized}/{branch}"


def slugify(value: str) -> str:
    ascii_text = value.encode("ascii", "ignore").decode("ascii").lower()
    slug = SAFE_SLUG_RE.sub("-", ascii_text).strip("-")
    return slug[:40].strip("-") or "image"


def build_filename(source: Path, requested_name: str | None) -> str:
    ext = source.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError(
            f"Unsupported extension: {ext or '(none)'}. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if requested_name:
        target_name = requested_name
    elif DATE_PREFIX_RE.match(source.name):
        return source.name
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        target_name = f"{timestamp}-{slugify(source.stem)}{ext}"

    target_path = Path(target_name)
    if target_path.suffix.lower() != ext:
        raise UploadError("Requested filename must keep the original extension.")
    return target_path.name


def ensure_unique_path(target_dir: Path, filename: str) -> Path:
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    ext = candidate.suffix
    for index in range(2, 1000):
        retry = target_dir / f"{stem}-{index}{ext}"
        if not retry.exists():
            return retry
    raise UploadError("Failed to derive a unique filename after many attempts.")


def validate_source(source: Path) -> None:
    if not source.exists():
        raise UploadError(f"Source file does not exist: {source}")
    if not source.is_file():
        raise UploadError(f"Source path is not a file: {source}")
    size = source.stat().st_size
    if size > MAX_FILE_BYTES:
        raise UploadError(f"File is too large: {size / (1024 * 1024):.1f}MB > 50MB")


def build_upload_plan(
    source: Path,
    repo_dir: Path,
    repo_url: str,
    directory: str | None,
    filename: str | None,
) -> UploadPlan:
    validate_source(source)
    ensure_repo(repo_dir, repo_url)

    selected_dir = directory or infer_directory(source)
    target_dir = repo_dir / selected_dir
    if not target_dir.exists():
        raise UploadError(f"Target directory does not exist in repo: {selected_dir}")

    computed_name = build_filename(source, filename)
    target_path = ensure_unique_path(target_dir, computed_name)
    repo_relative = f"{selected_dir}/{target_path.name}"
    raw_url = f"{build_raw_base_url(repo_url, DEFAULT_BRANCH)}/{repo_relative}"

    return UploadPlan(
        source=source,
        repo_dir=repo_dir,
        selected_dir=selected_dir,
        target_path=target_path,
        repo_relative=repo_relative,
        raw_url=raw_url,
    )


def confirm_upload(plan: UploadPlan, assume_yes: bool) -> None:
    if assume_yes:
        return

    print("Upload plan:")
    print(f"  Source: {plan.source}")
    print(f"  Target: {plan.repo_relative}")
    print(f"  Repo dir: {plan.repo_dir}")
    print(f"  Raw URL: {plan.raw_url}")
    reply = input("Proceed with upload? [y/N]: ").strip().lower()
    if reply not in {"y", "yes"}:
        raise UploadError("Upload cancelled.")


def perform_upload(plan: UploadPlan, dry_run: bool) -> UploadResult:
    target_path = plan.target_path

    if dry_run:
        return UploadResult(
            repo_path=plan.repo_relative,
            raw_url=plan.raw_url,
            markdown=f"![{target_path.stem}]({plan.raw_url})",
            commit="DRY_RUN",
        )

    shutil.copy2(plan.source, target_path)
    run_git(["add", plan.repo_relative], plan.repo_dir)

    commit_message = f"add: {plan.repo_relative}"
    run_git(["commit", "-m", commit_message], plan.repo_dir)
    run_git(["push", "origin", DEFAULT_BRANCH], plan.repo_dir)
    commit = run_git(["rev-parse", "HEAD"], plan.repo_dir).stdout.strip()

    return UploadResult(
        repo_path=plan.repo_relative,
        raw_url=plan.raw_url,
        markdown=f"![{target_path.stem}]({plan.raw_url})",
        commit=commit,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload an image to the GitHub image-hosting repo")
    parser.add_argument("source", help="Path to the local image file")
    parser.add_argument(
        "--directory",
        choices=["wechat-covers", "screenshots", "diagrams", "photos", "misc"],
        help="Target directory in the hosting repo. Auto-inferred if omitted.",
    )
    parser.add_argument(
        "--filename",
        help="Optional target filename. Must keep the source extension.",
    )
    parser.add_argument(
        "--repo-dir",
        default=os.environ.get("IMAGE_HOSTING_REPO_DIR", str(DEFAULT_REPO_DIR)),
        help=f"Local clone path (default: {DEFAULT_REPO_DIR})",
    )
    parser.add_argument(
        "--repo-url",
        default=os.environ.get("IMAGE_HOSTING_REPO_URL", DEFAULT_REPO_URL),
        help=f"Git remote URL (default: {DEFAULT_REPO_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the inferred upload target and URL without copying, committing, or pushing.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt and upload immediately.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = build_upload_plan(
            source=Path(args.source).expanduser().resolve(),
            repo_dir=Path(args.repo_dir).expanduser(),
            repo_url=args.repo_url,
            directory=args.directory,
            filename=args.filename,
        )
        if args.dry_run:
            print("Upload plan:")
            print(f"  Source: {plan.source}")
            print(f"  Target: {plan.repo_relative}")
            print(f"  Repo dir: {plan.repo_dir}")
            print(f"  Raw URL: {plan.raw_url}")
        else:
            confirm_upload(plan, assume_yes=args.yes)
        result = perform_upload(plan, dry_run=args.dry_run)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout or str(exc)
        print(f"Error: git command failed: {detail}", file=sys.stderr)
        return 1
    except EOFError:
        print("Error: confirmation prompt could not read input. Re-run with --yes for non-interactive use.", file=sys.stderr)
        return 1
    except UploadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Repo path: {result.repo_path}")
    print(f"Raw URL: {result.raw_url}")
    print(f"Markdown: {result.markdown}")
    print(f"Commit: {result.commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
