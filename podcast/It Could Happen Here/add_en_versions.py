#!/usr/bin/env python3
"""
add_en_versions.py — 生成英文版文章（博客+播客站），并更新中文版为交错排列+互链

输入:
  - season1/English/整理版/{num}.md（英文整理稿：# 英文原标题 + Summary: xxx + ## 小标题 + 段落）
  - season1/{num}.md（英文原稿，取标题）
输出:
  - 博客 articles/{slug}-EN/draft.md（标题「Episode X · 原标题」，排序 2X，含中文对照链接）
  - 播客站 content/it-could-happen-here/{slug}-EN.md（含中文对照链接）
并更新已有中文版:
  - 博客 articles/{slug}/draft.md：排序 1-11 → 奇数 1,3,5..21；末尾追加英文对照链接
  - 播客站 content/it-could-happen-here/{slug}.md：末尾追加英文对照链接

用法: python add_en_versions.py
"""

import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
SEASON = BASE / "season1"
EN_FORMATTED = SEASON / "English" / "整理版"

BLOG_ARTICLES = Path(r"C:\cc\blog-pages\articles")
PODCAST_SRC = Path(r"C:\Users\张小树\Downloads\podcast-site-generator\podcast-site-src")
PODCAST_CONTENT = PODCAST_SRC / "content" / "it-could-happen-here"

DATE = "2026-08-03"
SHOW_SLUG = "it-could-happen-here"
SOURCE_URL = "https://www.iheart.com/podcast/it-could-happen-here"

BLOG_PREFIX = "/blog-pages"
PODCAST_PREFIX = "/podcast-site"


def slugify(title: str) -> str:
    slug = title.strip()
    for ch in '/\\:?*"<>|':
        slug = slug.replace(ch, "")
    slug = slug.replace(" ", "_")
    return slug.strip("_")


def parse_en_formatted(text: str):
    """解析英文整理稿 → (en_title, summary, body)"""
    lines = text.split("\n")
    en_title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    summary, body_start = "", 0
    for i, line in enumerate(lines):
        m = re.match(r"^Summary[：:]\s*(.+)$", line.strip())
        if m:
            summary = m.group(1).strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    return en_title, summary, body


def safe_frontmatter(s: str) -> str:
    """frontmatter 值转义"""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def add_cross_link_if_missing(path: Path, marker: str, link: str):
    """若文件末尾尚无 marker 链接，则追加"""
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    text = text.rstrip() + "\n\n---\n\n" + link + "\n"
    path.write_text(text, encoding="utf-8")
    return True


def update_blog_zh(draft_path: Path, ep_slug: str):
    """中文博客 draft.md：排序改奇数 + 末尾加英文对照链接"""
    if not draft_path.exists():
        return False, 0
    text = draft_path.read_text(encoding="utf-8")
    old_pos = None
    m = re.search(r"^> 排序：(\d+)\s*$", text, re.M)
    if m:
        old_pos = int(m.group(1))
        new_pos = old_pos * 2 - 1
        text = re.sub(r"^> 排序：\d+\s*$", f"> 排序：{new_pos}", text, count=1, flags=re.M)
    link = f"📄 **英文原文对照**：[English version]({BLOG_PREFIX}/posts/{DATE}-It_Could_Happen_Here-{ep_slug}-EN/)"
    if "英文原文对照" not in text:
        text = text.rstrip() + "\n\n---\n\n" + link + "\n"
    draft_path.write_text(text, encoding="utf-8")
    return True, (old_pos or 0)


def main():
    if not EN_FORMATTED.exists():
        print(f"❌ 英文整理版目录不存在: {EN_FORMATTED}（先运行 format_en.py）")
        return

    files = sorted(EN_FORMATTED.glob("*.md"))
    if not files:
        print("❌ 英文整理版目录为空")
        return

    for f in files:
        num = f.stem  # 001, 002...
        ep_num = int(num)

        # 英文标题（从 season1 英文原稿取）
        en_title = ""
        en_src = SEASON / f"{num}.md"
        if en_src.exists():
            first = en_src.read_text(encoding="utf-8").splitlines()[0]
            if first.startswith("#"):
                en_title = first.lstrip("# ").strip()
        if not en_title:
            en_title = f"Episode {ep_num}"

        zh_title, summary, body = parse_en_formatted(f.read_text(encoding="utf-8"))
        en_title = zh_title or en_title  # 整理稿标题为准
        ep_slug = slugify(en_title)
        slug = f"{DATE}-It_Could_Happen_Here-{ep_slug}"
        slug_en = f"{slug}-EN"

        # ── 博客英文文章 ──
        blog_dir = BLOG_ARTICLES / slug_en
        blog_dir.mkdir(parents=True, exist_ok=True)
        draft = (
            f"# Episode {ep_num} · {en_title}\n\n"
            f"> 栏目：播客笔记\n"
            f"> 日期：{DATE}\n"
            f"> 排序：{ep_num * 2}\n"
            f"> 标签：It Could Happen Here，播客，英文\n"
            f"> 摘要：{summary}\n\n"
            f"{body}\n\n"
            f"---\n\n"
            f"📄 **中文翻译**：[中文翻译]({BLOG_PREFIX}/posts/{slug}/)\n"
        )
        (blog_dir / "draft.md").write_text(draft, encoding="utf-8")

        # ── 播客站英文文稿 ──
        pf = PODCAST_CONTENT / f"{slug_en}.md"
        pm = (
            "---\n"
            f'title: "Episode {ep_num} · {safe_frontmatter(en_title)}"\n'
            f"date: {DATE}\n"
            f"show: {SHOW_SLUG}\n"
            f'summary: "{safe_frontmatter(summary)}"\n'
            f'tags: ["It Could Happen Here", "播客", "英文版"]\n'
            f'source_episode: "{safe_frontmatter(en_title)}"\n'
            f"source_url: {SOURCE_URL}\n"
            f"processed_date: {DATE}\n"
            f"original_language: EN\n"
            "---\n\n"
            f"{body}\n\n"
            "---\n\n"
            f"📄 **中文翻译**：[中文翻译]({PODCAST_PREFIX}/episode/it-could-happen-here/{slug}/)\n"
        )
        pf.write_text(pm, encoding="utf-8")

        # ── 更新中文博客文章（排序奇数 + 英文链接）──
        zh_draft = BLOG_ARTICLES / slug / "draft.md"
        updated, old_pos = update_blog_zh(zh_draft, ep_slug)

        # ── 更新播客站中文文稿（英文链接）──
        zh_pf = PODCAST_CONTENT / f"{slug}.md"
        added_zh = add_cross_link_if_missing(
            zh_pf,
            "English version",
            f"📄 **English version**: [English]({PODCAST_PREFIX}/episode/it-could-happen-here/{slug_en}/)",
        )

        print(f"[{num}] Episode {ep_num} · {en_title}")
        print(f"    英文博客 → {blog_dir / 'draft.md'}")
        print(f"    英文播客站 → {pf.name}")
        print(f"    中文博客排序 {old_pos}→{old_pos*2-1}（{'已更新' if updated else '无变化'}），中文播客站链接{'已加' if added_zh else '已存在'}")

    print("\n全部完成。")


if __name__ == "__main__":
    main()
