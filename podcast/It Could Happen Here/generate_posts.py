#!/usr/bin/env python3
"""
generate_posts.py — 从整理版中文稿生成博客文章 + 播客站文稿

输入: season1/中文/整理版/*.md（含 # 标题、摘要：、## 小标题、分段正文）
      season1/{num}.md（英文稿，取英文原标题）
输出:
  - C:/cc/blog-pages/articles/{DATE}-It_Could_Happen_Here-{EpSlug}/draft.md
  - .../podcast-site-src/content/it-could-happen-here/{DATE}-It_Could_Happen_Here-{EpSlug}.md

用法: python generate_posts.py
"""

import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
SEASON = BASE / "season1"
FORMATTED = SEASON / "中文" / "整理版"

BLOG_ARTICLES = Path(r"C:\cc\blog-pages\articles")
PODCAST_SRC = Path(r"C:\Users\张小树\Downloads\podcast-site-generator\podcast-site-src")
PODCAST_CONTENT = PODCAST_SRC / "content" / "it-could-happen-here"

DATE = "2026-08-03"
SHOW_SLUG = "it-could-happen-here"
SOURCE_URL = "https://www.iheart.com/podcast/it-could-happen-here"


def slugify(title: str) -> str:
    slug = title.strip()
    for ch in '/\\:?*"<>|':
        slug = slug.replace(ch, "")
    slug = slug.replace(" ", "_")
    return slug.strip("_")


def parse_formatted(text: str):
    """解析整理稿 → (zh_title, summary, body)"""
    lines = text.split("\n")
    zh_title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    summary, body_start = "", 0
    for i, line in enumerate(lines):
        m = re.match(r"^摘要[：:]\s*(.+)$", line.strip())
        if m:
            summary = m.group(1).strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    return zh_title, summary, body


def safe_frontmatter(s: str) -> str:
    """frontmatter 值转义（引号/冒号等）"""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def main():
    if not FORMATTED.exists():
        print(f"❌ 整理版目录不存在: {FORMATTED}（先运行 format_zh.py）")
        return

    PODCAST_CONTENT.mkdir(parents=True, exist_ok=True)

    files = sorted(FORMATTED.glob("*.md"))
    if not files:
        print("❌ 整理版目录为空")
        return

    for i, f in enumerate(files, 1):
        num = f.stem  # 001, 002...
        en_title = ""
        en = SEASON / f"{num}.md"
        if en.exists():
            first = en.read_text(encoding="utf-8").splitlines()[0]
            if first.startswith("#"):
                en_title = first.lstrip("# ").strip()
        if not en_title:
            en_title = f"Episode {num}"

        zh_title, summary, body = parse_formatted(f.read_text(encoding="utf-8"))
        ep_slug = slugify(en_title)
        slug = f"{DATE}-It_Could_Happen_Here-{ep_slug}"

        # ── 博客文章 draft.md ──
        blog_dir = BLOG_ARTICLES / slug
        blog_dir.mkdir(parents=True, exist_ok=True)
        draft = (
            f"# {zh_title}\n\n"
            f"> 栏目：播客笔记\n"
            f"> 日期：{DATE}\n"
            f"> 排序：{i}\n"
            f"> 标签：It Could Happen Here，播客\n"
            f"> 摘要：{summary}\n\n"
            f"{body}\n"
        )
        (blog_dir / "draft.md").write_text(draft, encoding="utf-8")

        # ── 播客站文稿 ──
        pf = PODCAST_CONTENT / f"{DATE}-It_Could_Happen_Here-{ep_slug}.md"
        pm = (
            "---\n"
            f'title: "{safe_frontmatter(zh_title)}"\n'
            f"date: {DATE}\n"
            f"show: {SHOW_SLUG}\n"
            f'summary: "{safe_frontmatter(summary)}"\n'
            f'tags: ["It Could Happen Here", "播客"]\n'
            f'source_episode: "{safe_frontmatter(en_title)}"\n'
            f"source_url: {SOURCE_URL}\n"
            f"processed_date: {DATE}\n"
            f"original_language: EN\n"
            "---\n\n"
            f"{body}\n"
        )
        pf.write_text(pm, encoding="utf-8")

        print(f"[{num}] 《{zh_title}》 | {slug}")
        print(f"    博客 → {blog_dir / 'draft.md'}")
        print(f"    播客站 → {pf.name}")

    print("\n全部生成完成。")


if __name__ == "__main__":
    main()
