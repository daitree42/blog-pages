#!/usr/bin/env python3
"""
publish.py — 树 (blog-pages) 静态博客构建系统

用法:
    python publish.py build          # 完整构建
    python publish.py migrate        # 从 posts/ 迁移现有文章到 articles/
    python publish.py new <title>    # 创建新文章
    python publish.py serve          # 本地预览
"""

import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Windows 终端兼容：避免 emoji 编码错误
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # py3.7+

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    AUTHOR_EMAIL,
    CATEGORY_EMOJI,
    CATEGORY_MAP,
    CATEGORY_SLUG_MAP,
    GITHUB_URL,
    POSTS_PER_PAGE,
    READING_SPEED_ZH,
    SITE_PREFIX,
    SITE_TAGLINE,
    SITE_TITLE,
    SITE_URL,
)

# ── 路径 ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"
POSTS_DIR = BASE_DIR / "posts"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
CATEGORY_DIR = BASE_DIR / "category"
TAG_DIR = BASE_DIR / "tag"
PAGE_DIR = BASE_DIR / "page"
ARCHIVE_DIR = BASE_DIR / "archive"

# 构建系统源文件 — clean 时不删除
SOURCE_PATHS = {
    ".git", ".gitignore", ".nojekyll", "articles", "templates",
    "publish.py", "config.py", "requirements.txt",
    "static", ".github",
}

# ── 模板引擎 ───────────────────────────────────────────────────────
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(default=False),
)


def format_date_display(date_str):
    """2026-05-25 → 2026年5月25日"""
    parts = date_str.split("-")
    return f"{parts[0]}年{int(parts[1])}月{int(parts[2])}日"


def format_date_archive(date_str):
    """2026-05-25 → 05-25"""
    return date_str[5:]


def format_rss_date(date_str):
    """2026-05-25 → Tue, 25 May 2026 00:00:00 +0000"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{weekdays[dt.weekday()]}, {dt.day:02d} {months[dt.month-1]} {dt.year} 00:00:00 +0000"


def calc_reading_time(text):
    """估算中文阅读时间（分钟）"""
    zh_chars = len(re.findall(r'[一-鿿]', text))
    minutes = round(zh_chars / READING_SPEED_ZH)
    return max(1, minutes)


def slugify(title):
    """将标题转为文件路径安全的 slug"""
    slug = title.strip()
    for ch in '/\\:?*"<>|':
        slug = slug.replace(ch, '')
    slug = slug.replace(' ', '_')
    return slug


def get_category_slug(category_name):
    """分类名 → URL slug"""
    return CATEGORY_MAP.get(category_name, "uncategorized")


# ── 文章解析 ──────────────────────────────────────────────────────

def parse_draft(filepath):
    """
    解析 draft.md 文件，提取元数据和正文。

    格式:
        # 文章标题

        > 栏目：Ai技术
        > 日期：2026-05-25
        > 标签：标签1，标签2
        > 摘要：一段简短的描述

        正文从这里开始……
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    lines = raw.split("\n")
    title = ""
    metadata = {}
    body_start = 0

    # 第1行: # 标题
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    # 解析 blockquote 元数据
    in_meta = False
    meta_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("> "):
            in_meta = True
            meta_lines.append(stripped[2:])
        elif in_meta and stripped == "":
            # blockquote 结束后的空行
            continue
        elif in_meta:
            body_start = i
            break
        elif stripped == "":
            continue
        elif not stripped.startswith("#") and not in_meta:
            body_start = i
            break

    for ml in meta_lines:
        if "：" in ml:
            key, value = ml.split("：", 1)
            key = key.strip()
            value = value.strip()
            if key == "栏目":
                metadata["category"] = value
            elif key == "日期":
                metadata["date"] = value
            elif key == "标签":
                metadata["tags"] = [t.strip() for t in value.replace("，", ",").split(",") if t.strip()]
            elif key == "摘要":
                metadata["excerpt"] = value
            elif key == "排序":
                try:
                    metadata["position"] = int(value)
                except ValueError:
                    metadata["position"] = 0
            elif key == "阅读时间":
                try:
                    metadata["reading_time"] = int(value.replace("分钟", "").strip())
                except ValueError:
                    pass

    # 正文
    body_raw = "\n".join(lines[body_start:]).strip()

    # 判断正文是 Markdown 还是原始 HTML
    if body_raw.startswith("<") or "<p>" in body_raw[:200] or "<h" in body_raw[:200] or "<div" in body_raw[:200]:
        body_html = body_raw  # 已是 HTML，原样传递
    else:
        body_html = md_lib.markdown(body_raw, extensions=["fenced_code", "tables", "codehilite"])

    # 去除 body_html 外层 <div class="post-body"> 包装（迁移引入的）
    body_html = re.sub(r'^<div\s+class="post-body">\s*', '', body_html)
    body_html = re.sub(r'\s*</div>\s*$', '', body_html)

    # 统计纯文本字数（去 HTML 标签）
    word_count = len(re.findall(r'[一-鿿]', re.sub(r'<[^>]+>', '', body_raw)))

    category = metadata.get("category", "未分类")
    tags = metadata.get("tags", [])
    excerpt = metadata.get("excerpt", "")
    date_str = metadata.get("date", datetime.now().strftime("%Y-%m-%d"))
    position = metadata.get("position", 0)
    # 优先使用元数据中的阅读时间，否则自动计算
    reading_time = metadata.get("reading_time", calc_reading_time(body_raw))
    # 从文件名提取 slug（父目录名）
    slug = filepath.parent.name

    return {
        "title": title,
        "slug": slug,
        "date": date_str,
        "date_iso": date_str,
        "date_display": format_date_display(date_str),
        "date_archive": format_date_archive(date_str),
        "category": category,
        "category_slug": get_category_slug(category),
        "tags": tags,
        "excerpt": excerpt,
        "body_html": body_html,
        "word_count": word_count,
        "reading_time": reading_time,
        "rss_date": format_rss_date(date_str),
        "emoji": CATEGORY_EMOJI.get(category, "\U0001F4DD"),
        "position": position,
    }


def load_all_articles():
    """加载所有文章，按日期降序排列"""
    if not ARTICLES_DIR.exists():
        return []

    articles = []
    for slug_dir in sorted(ARTICLES_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        draft_path = slug_dir / "draft.md"
        if not draft_path.exists():
            continue
        try:
            article = parse_draft(draft_path)
            articles.append(article)
        except Exception as e:
            print(f"  [WARN] 解析失败: {draft_path} — {e}")

    # 先按 position 升序（同日期内保持原始顺序）
    articles.sort(key=lambda a: a["position"])
    # 再按日期降序（稳定排序，同日期内保持 position 顺序）
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


# ── 清理 ──────────────────────────────────────────────────────────

def clean_output():
    """删除所有自动生成的文件，保留源文件"""
    dirs_to_clean = ["posts", "category", "tag", "page", "archive"]

    for dname in dirs_to_clean:
        dpath = BASE_DIR / dname
        if dpath.exists():
            shutil.rmtree(dpath)

    # 删除根目录的生成文件
    for fname in ["index.html", "search.json", "rss.xml", "sitemap.xml"]:
        fpath = BASE_DIR / fname
        if fpath.exists():
            fpath.unlink()

    # 确保 articles/ 和 templates/ 存在
    ARTICLES_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)


# ── 分页工具 ──────────────────────────────────────────────────────

def paginate(items, per_page=POSTS_PER_PAGE):
    """将列表分成每页 per_page 个"""
    pages = []
    for i in range(0, len(items), per_page):
        pages.append(items[i:i + per_page])
    return pages


def page_url_for(page_num, base_path=""):
    """生成分页 URL（不含 site_prefix）"""
    if page_num == 1:
        return f"{base_path}/index.html" if base_path else "index.html"
    else:
        return f"{base_path}/page/{page_num}/index.html" if base_path else f"page/{page_num}/index.html"


def page_href_for(page_num, base=""):
    """生成分页链接 href（不含 site_prefix，不含 index.html）"""
    if page_num <= 1:
        return f"{base}/" if base else ""
    else:
        return f"{base}/page/{page_num}/" if base else f"page/{page_num}/"


# ── 渲染与写入 ────────────────────────────────────────────────────

def render(template_name, **context):
    """渲染模板"""
    tpl = jinja_env.get_template(template_name)
    return tpl.render(**context)


def write_file(rel_path, content):
    """写入文件（相对 BASE_DIR）"""
    full_path = BASE_DIR / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)


def get_base_context():
    """所有页面共用的模板上下文"""
    return {
        "site_title": SITE_TITLE,
        "site_tagline": SITE_TAGLINE,
        "site_prefix": SITE_PREFIX,
        "github_url": GITHUB_URL,
        "author_email": AUTHOR_EMAIL,
        "categories": list(CATEGORY_MAP.items()),
        "current_year": datetime.now().year,
    }


# ── 页面生成 ──────────────────────────────────────────────────────

def generate_post_pages(articles):
    """生成每篇文章的 posts/{slug}/index.html"""
    for i, article in enumerate(articles):
        prev_article = articles[i + 1] if i + 1 < len(articles) else None
        next_article = articles[i - 1] if i - 1 >= 0 else None

        ctx = get_base_context()
        ctx.update({
            "article": article,
            "prev_article": prev_article,
            "next_article": next_article,
            "current_page_type": "post",
        })
        html = render("post.html", **ctx)
        write_file(f"posts/{article['slug']}/index.html", html)


def generate_homepage(articles):
    """生成首页 index.html 和 page/{n}/index.html"""
    pages = paginate(articles)
    total_pages = len(pages)

    for i, page_articles in enumerate(pages):
        page_num = i + 1
        is_first = page_num == 1
        is_last = page_num == total_pages

        ctx = get_base_context()
        ctx.update({
            "articles": page_articles,
            "current_page": page_num,
            "total_pages": total_pages,
            "is_first_page": is_first,
            "is_last_page": is_last,
            "current_page_type": "home",
            "recommended_article": articles[0] if is_first else None,
            "page_title": None,
            "page_prev_url": page_href_for(page_num - 1) if page_num > 1 else "",
            "page_next_url": page_href_for(page_num + 1) if not is_last else "",
        })
        html = render("index.html", **ctx)

        if is_first:
            write_file("index.html", html)
        else:
            write_file(f"page/{page_num}/index.html", html)


def generate_category_pages(articles):
    """生成分类页 category/{slug}/index.html 及分页"""
    by_category = defaultdict(list)
    for a in articles:
        by_category[a["category"]].append(a)

    for cat_name, cat_slug in CATEGORY_MAP.items():
        cat_articles = by_category.get(cat_name, [])
        pages = paginate(cat_articles)
        total_pages = max(len(pages), 1)

        for i, page_articles in enumerate(pages if pages else [[]]):
            page_num = i + 1
            is_first = page_num == 1
            is_last = page_num == total_pages

            ctx = get_base_context()
            ctx.update({
                "articles": page_articles,
                "current_page": page_num,
                "total_pages": total_pages,
                "is_first_page": is_first,
                "is_last_page": is_last,
                "page_title": cat_name,
                "current_category_slug": cat_slug,
                "current_page_type": "category",
                "recommended_article": cat_articles[0] if is_first and cat_articles else None,
                "page_prev_url": page_href_for(page_num - 1, f"category/{cat_slug}"),
                "page_next_url": page_href_for(page_num + 1, f"category/{cat_slug}"),
            })
            html = render("index.html", **ctx)

            if is_first:
                write_file(f"category/{cat_slug}/index.html", html)
            else:
                write_file(f"category/{cat_slug}/page/{page_num}/index.html", html)


def generate_tag_pages(articles):
    """生成标签页 tag/{tag}/index.html 及分页"""
    by_tag = defaultdict(list)
    for a in articles:
        for tag in a["tags"]:
            by_tag[tag].append(a)

    for tag_name, tag_articles in by_tag.items():
        pages = paginate(tag_articles)
        total_pages = len(pages)

        for i, page_articles in enumerate(pages):
            page_num = i + 1
            is_first = page_num == 1
            is_last = page_num == total_pages

            ctx = get_base_context()
            ctx.update({
                "articles": page_articles,
                "current_page": page_num,
                "total_pages": total_pages,
                "is_first_page": is_first,
                "is_last_page": is_last,
                "page_title": tag_name,
                "current_page_type": "tag",
                "current_tag": tag_name,
                "recommended_article": None,
                "page_prev_url": page_href_for(page_num - 1, f"tag/{tag_name}"),
                "page_next_url": page_href_for(page_num + 1, f"tag/{tag_name}"),
            })
            html = render("index.html", **ctx)

            if is_first:
                write_file(f"tag/{tag_name}/index.html", html)
            else:
                write_file(f"tag/{tag_name}/page/{page_num}/index.html", html)


def generate_archive(articles):
    """生成存档页 archive/index.html"""
    # 按年 > 月分组
    archive_data = []
    by_year = defaultdict(list)
    for a in articles:
        year = a["date"][:4]
        by_year[year].append(a)

    for year in sorted(by_year.keys(), reverse=True):
        by_month = defaultdict(list)
        for a in by_year[year]:
            month = int(a["date"][5:7])
            by_month[month].append(a)

        months = []
        for month in sorted(by_month.keys(), reverse=True):
            months.append({
                "month": month,
                "articles": by_month[month],
            })
        archive_data.append({"year": year, "months": months})

    ctx = get_base_context()
    ctx.update({
        "archive_data": archive_data,
        "current_page_type": "archive",
    })
    html = render("archive.html", **ctx)
    write_file("archive/index.html", html)


def generate_search_json(articles):
    """生成 search.json"""
    index = []
    for a in articles:
        index.append({
            "title": a["title"],
            "url": f"posts/{a['slug']}/",
            "date": a["date_display"],
            "tags": a["tags"],
            "category": a["category"],
            "excerpt": a["excerpt"],
        })
    write_file("search.json", json.dumps(index, ensure_ascii=False, indent=2))


def generate_rss(articles):
    """生成 rss.xml"""
    ctx = get_base_context()
    ctx.update({"articles": articles})
    xml = render("rss.xml", **ctx)
    write_file("rss.xml", xml)


def generate_sitemap(articles):
    """生成 sitemap.xml"""
    urls = []

    # 首页
    pages = paginate(articles)
    urls.append(("", "1.0"))
    for i in range(1, len(pages)):
        urls.append((f"page/{i + 1}/", "0.6"))

    # 文章页
    for a in articles:
        urls.append((f"posts/{a['slug']}/", "0.8"))

    # 分类页
    by_category = defaultdict(list)
    for a in articles:
        by_category[a["category"]].append(a)
    for cat_name, cat_slug in CATEGORY_MAP.items():
        cat_pages = paginate(by_category.get(cat_name, []))
        urls.append((f"category/{cat_slug}/", "0.7"))
        for i in range(1, len(cat_pages)):
            urls.append((f"category/{cat_slug}/page/{i + 1}/", "0.6"))

    # 标签页
    by_tag = defaultdict(list)
    for a in articles:
        for tag in a["tags"]:
            by_tag[tag].append(a)
    for tag_name, tag_articles in by_tag.items():
        tag_pages = paginate(tag_articles)
        urls.append((f"tag/{tag_name}/", "0.6"))
        for i in range(1, len(tag_pages)):
            urls.append((f"tag/{tag_name}/page/{i + 1}/", "0.6"))

    # 存档页
    urls.append(("archive/", "0.6"))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, priority in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE_URL}/{path}</loc>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    write_file("sitemap.xml", "\n".join(lines))


# ── 构建主流程 ────────────────────────────────────────────────────

def build():
    """完整构建站点"""
    print("📦 加载文章...")
    articles = load_all_articles()
    print(f"   共 {len(articles)} 篇文章")

    if not articles:
        print("⚠  没有找到文章，生成空站点")
    else:
        print(f"   最新: {articles[0]['title']}")
        print(f"   最早: {articles[-1]['title']}")

    print("\n🧹 清理输出目录...")
    clean_output()

    print("\n📝 生成文章页...")
    generate_post_pages(articles)

    print("🏠 生成首页...")
    generate_homepage(articles)

    print("📂 生成分类页...")
    generate_category_pages(articles)

    print("🏷️ 生成标签页...")
    generate_tag_pages(articles)

    print("📚 生成存档页...")
    generate_archive(articles)

    print("🔍 生成搜索索引...")
    generate_search_json(articles)

    print("📡 生成 RSS...")
    generate_rss(articles)

    print("🗺️ 生成站点地图...")
    generate_sitemap(articles)

    print("\n✅ 构建完成！")


# ── 迁移 ──────────────────────────────────────────────────────────

def migrate():
    """从 posts/ 现有 HTML 迁移到 articles/{slug}/draft.md"""
    from bs4 import BeautifulSoup

    if not POSTS_DIR.exists():
        print("❌ posts/ 目录不存在，没有可迁移的文章")
        return

    post_dirs = sorted([d for d in POSTS_DIR.iterdir() if d.is_dir()])
    print(f"📦 发现 {len(post_dirs)} 篇文章待迁移\n")

    for i, slug_dir in enumerate(post_dirs, 1):
        slug = slug_dir.name
        html_path = slug_dir / "index.html"

        if not html_path.exists():
            print(f"  [{i:2d}/{len(post_dirs)}] ⏭  {slug} — 无 index.html")
            continue

        try:
            with open(html_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            # 提取元数据
            title_el = soup.select_one(".post-title")
            title = title_el.get_text(strip=True) if title_el else slug

            breadcrumb_el = soup.select_one(".post-breadcrumb")
            category = breadcrumb_el.get_text(strip=True) if breadcrumb_el else "未分类"

            time_el = soup.select_one(".post-meta time")
            date_str = time_el["datetime"] if time_el and time_el.has_attr("datetime") else ""

            tag_els = soup.select(".post-tags .tag")
            tags = [t.get_text(strip=True) for t in tag_els]

            # 提取正文
            body_el = soup.select_one(".post-body")
            body_html = ""
            if body_el:
                body_html = str(body_el)

            # 生成 excerpt（取正文前 150 字）
            body_text = body_el.get_text(strip=True) if body_el else ""
            excerpt = body_text[:150] if body_text else ""

            # 写入 draft.md
            articles_dir = ARTICLES_DIR / slug
            articles_dir.mkdir(parents=True, exist_ok=True)
            draft_path = articles_dir / "draft.md"

            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"> 栏目：{category}\n")
                f.write(f"> 日期：{date_str}\n")
                if tags:
                    f.write(f"> 标签：{'，'.join(tags)}\n")
                f.write(f"> 摘要：{excerpt}\n")
                f.write(f"\n")
                # 正文以原始 HTML 保存（markdown 库遇到 HTML 会原样传递）
                f.write(body_html)

            print(f"  [{i:2d}/{len(post_dirs)}] ✅ {slug}")

        except Exception as e:
            print(f"  [{i:2d}/{len(post_dirs)}] ❌ {slug} — {e}")

    print(f"\n✅ 迁移完成！共处理 {len(post_dirs)} 篇文章")


# ── 新建文章 ──────────────────────────────────────────────────────

def new_post(title, category="未分类", tags=None):
    """创建新文章模板"""
    slug = slugify(title)
    draft_path = ARTICLES_DIR / slug / "draft.md"
    draft_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    tags_str = "，".join(tags) if tags else ""

    content = f"# {title}\n\n"
    content += f"> 栏目：{category}\n"
    content += f"> 日期：{today}\n"
    if tags_str:
        content += f"> 标签：{tags_str}\n"
    content += f"> 摘要：\n"
    content += f"\n"
    content += f"正文……\n"

    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 新文章创建: {draft_path}")
    return draft_path


# ── 本地预览 ──────────────────────────────────────────────────────

def serve(port=8000):
    """启动本地 HTTP 服务器预览"""
    import http.server

    os.chdir(str(BASE_DIR))

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    print(f"🌐 本地预览: http://localhost:{port}{SITE_PREFIX}/")
    print("   按 Ctrl+C 停止")
    http.server.HTTPServer(("", port), Handler).serve_forever()


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="树 博客构建系统")
    parser.add_argument("command", nargs="?", default="build",
                        choices=["build", "migrate", "new", "serve"],
                        help="操作: build=构建, migrate=迁移, new=新建, serve=预览")
    parser.add_argument("title", nargs="?",
                        help="新文章标题 (new 命令)")
    parser.add_argument("--category", default="未分类",
                        help="分类 (new 命令)")
    parser.add_argument("--tags", default="",
                        help="标签，逗号分隔 (new 命令)")
    parser.add_argument("--port", type=int, default=8000,
                        help="预览端口 (serve 命令)")

    args = parser.parse_args()

    if args.command == "build":
        build()
    elif args.command == "migrate":
        migrate()
    elif args.command == "new":
        if not args.title:
            print("❌ 请指定文章标题: python publish.py new \"文章标题\"")
            sys.exit(1)
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        new_post(args.title, args.category, tags)
    elif args.command == "serve":
        serve(args.port)


if __name__ == "__main__":
    main()
