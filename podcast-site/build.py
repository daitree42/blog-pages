#!/usr/bin/env python3
"""
build.py — 播客转录站点生成器

从 shows.json 和 transcripts/ 生成静态 HTML 站点到 docs/。

用法:
    python build.py                    # 完整构建
    python build.py --serve            # 构建 + 本地预览
"""

import argparse
import json
import markdown as md_lib
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Windows 终端兼容：避免 emoji 编码错误
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # py3.7+

# ── 路径 ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR
SOURCE_DIRS = {"templates", "static", "transcripts", "transcripts_raw", ".git"}
SOURCE_FILES = {"build.py", "shows.json", ".gitignore"}
SHOWS_FILE = BASE_DIR / "shows.json"

# 站点前缀（部署到 GitHub Pages 子路径时使用）
SITE_PREFIX = "/podcast-site"

# ── 模板引擎 ──────────────────────────────────────────────────────
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)


def load_shows() -> list[dict]:
    """加载 shows.json"""
    if not SHOWS_FILE.exists():
        print("  ⚠  shows.json 不存在，返回空列表")
        return []

    with open(SHOWS_FILE, encoding="utf-8") as f:
        shows = json.load(f)

    # 统计每个节目已有几集转录
    for show in shows:
        slug = show["slug"]
        show_dir = TRANSCRIPTS_DIR / slug
        if show_dir.exists():
            episodes = sorted(show_dir.glob("*.md"), reverse=True)
            show["episode_count"] = len(episodes)
        else:
            show["episode_count"] = 0

    return shows


def parse_episode(filepath: Path, show_slug: str) -> dict | None:
    """
    解析单集转录 markdown 文件。

    格式：和 blog articles/draft.md 一致
      # 标题
      > 栏目：播客笔记
      > 日期：2026-07-25
      > 摘要：...

      正文……
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        print(f"  ⚠  读取失败: {filepath} — {e}")
        return None

    lines = raw.split("\n")

    # 标题
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    # 元数据
    metadata = {}
    in_meta = False
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("> "):
            in_meta = True
            content = stripped[2:]
            if "：" in content:
                key, value = content.split("：", 1)
                key = key.strip()
                value = value.strip()
                if key == "日期":
                    metadata["date"] = value
                elif key == "摘要":
                    metadata["summary"] = value
                elif key == "阅读时间":
                    try:
                        metadata["reading_time"] = int(value.replace("分钟", "").strip())
                    except ValueError:
                        pass
                elif key == "排序":
                    metadata["position"] = value
                    if key == "标签":
                        metadata["tags"] = value
        elif in_meta and stripped == "":
            continue
        elif in_meta:
            body_start = i
            break
        elif not stripped.startswith("#") and in_meta:
            body_start = i
            break

    # 正文（去掉 <div class="post-body"> 包装）
    body_raw = "\n".join(lines[body_start:]).strip()
    body_raw = re.sub(r'^<div\s+class="post-body">\s*', "", body_raw)
    body_raw = re.sub(r'\s*</div>\s*$', "", body_raw)

    # 转 HTML（或保留已有 HTML）
    if body_raw.strip().startswith("<") or "<p>" in body_raw[:200]:
        body_html = body_raw
    else:
        body_html = md_lib.markdown(body_raw, extensions=["fenced_code", "tables", "codehilite"])

    # slug 来自文件名
    slug = filepath.stem

    return {
        "title": title or slug,
        "slug": slug,
        "show_slug": show_slug,
        "date": metadata.get("date", ""),
        "summary": metadata.get("summary", ""),
        "reading_time": metadata.get("reading_time", 0),
        "body_html": body_html,
        "source_lang": metadata.get("source_lang", ""),
        "source_link": metadata.get("source_link", ""),
        "filepath": str(filepath),
    }


def load_episodes(show_slug: str) -> list[dict]:
    """加载某个节目的所有转录"""
    show_dir = TRANSCRIPTS_DIR / show_slug
    if not show_dir.exists():
        return []

    episodes = []
    for f in sorted(show_dir.glob("*.md"), reverse=True):
        ep = parse_episode(f, show_slug)
        if ep:
            episodes.append(ep)

    # 按日期降序
    episodes.sort(key=lambda e: e["date"], reverse=True)
    return episodes


def clean_output():
    """清空输出目录（保留源文件）"""
    if OUTPUT_DIR.exists():
        for item in OUTPUT_DIR.iterdir():
            # 保留源文件/目录
            if item.name in SOURCE_FILES:
                continue
            if item.name in SOURCE_DIRS:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_file(rel_path: str, content: str):
    """写入文件"""
    full_path = OUTPUT_DIR / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)


def build():
    print(f"🎙️  播客站点构建")
    print(f"   {'='*40}")

    # ── 加载数据 ────────────────────────────────────────
    shows = load_shows()
    print(f"   节目: {len(shows)} 个")

    all_episodes = []
    for show in shows:
        show_episodes = load_episodes(show["slug"])
        show["episodes"] = show_episodes
        all_episodes.extend(show_episodes)
        lang_tag = f" ({show['language']})" if show.get("language") else ""
        print(f"   {show['name']}: {len(show_episodes)} 集{lang_tag}")

    print(f"\n🧹 清理输出目录...")
    clean_output()

    # ── 复制静态文件 ─────────────────────────────────────
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static", dirs_exist_ok=True)
        print(f"   ✅ 静态文件已复制")

    # ── 上下文 ──────────────────────────────────────────
    ctx = {
        "site_prefix": SITE_PREFIX,
        "current_year": datetime.now().year,
    }

    # ── 首页 ────────────────────────────────────────────
    print(f"\n🏠 生成首页...")
    index_ctx = {**ctx, "shows": shows}
    html = jinja_env.get_template("index.html").render(**index_ctx)
    write_file("index.html", html)

    # ── 节目页 ──────────────────────────────────────────
    for show in shows:
        slug = show["slug"]
        print(f"   📂 {show['name']}...")
        show_ctx = {**ctx, "show": show, "episodes": show["episodes"]}
        html = jinja_env.get_template("show.html").render(**show_ctx)
        write_file(f"show/{slug}/index.html", html)

    # ── 单集页 ──────────────────────────────────────────
    print(f"   📝 单集页 ({len(all_episodes)} 篇)...")
    for ep in all_episodes:
        show = next((s for s in shows if s["slug"] == ep["show_slug"]), None)
        if not show:
            continue
        ep_ctx = {**ctx, "show": show, "episode": ep}
        html = jinja_env.get_template("episode.html").render(**ep_ctx)
        write_file(f"episode/{ep['slug']}/index.html", html)

    # ── 写入 .nojekyll ──────────────────────────────────
    (OUTPUT_DIR / ".nojekyll").touch()

    print(f"\n✅ 构建完成！共 {len(all_episodes)} 集，{len(shows)} 个节目")
    print(f"   输出: {OUTPUT_DIR}")


# ── 本地预览 ──────────────────────────────────────────────────────

def serve(port=8000):
    """启动本地预览"""
    import http.server

    os.chdir(str(BASE_DIR))

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    print(f"🌐 本地预览: http://localhost:{port}{SITE_PREFIX}/")
    print("   按 Ctrl+C 停止")
    http.server.HTTPServer(("", port), Handler).serve_forever()


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="播客转录站点生成器")
    parser.add_argument("--serve", action="store_true", help="构建后启动本地预览")
    parser.add_argument("--port", type=int, default=8000, help="预览端口")

    args = parser.parse_args()

    build()

    if args.serve:
        serve(args.port)


if __name__ == "__main__":
    main()
