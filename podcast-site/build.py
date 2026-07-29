#!/usr/bin/env python3
"""
播客笔记 - 网站生成脚本
======================
用法：
  python build.py

会读取：
  data/shows.yaml      节目列表（名称/简介/分类等）
  content/<show>/*.md  每一集的文字稿（YAML front matter + Markdown 正文）

生成到：
  public/               整个静态网站，把这个文件夹的内容原样推送 / 拷贝到你的
                         GitHub Pages 仓库即可（覆盖 index.html / show/ / episode/ / static/）

新增一集：在 content/<show-slug>/ 下新建一个 .md 文件（文件名随意，建议
  "日期-短标题.md"），按下面的字段格式填写头部信息即可，然后重新运行本脚本。
"""

import json
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import frontmatter
import markdown as md
import yaml
from jinja2 import Environment, FileSystemLoader

# ── 配置 ──────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
DATA_FILE = ROOT_DIR / "data" / "shows.yaml"
CONTENT_DIR = ROOT_DIR / "content"
TEMPLATE_DIR = ROOT_DIR / "templates"
STATIC_SRC_DIR = ROOT_DIR / "static"
OUTPUT_DIR = ROOT_DIR / "public"

# 部署到 GitHub Pages 项目页时的子路径，例如你的仓库是
# daitree42.github.io/podcast-site/ 就填 "/podcast-site/"；
# 如果部署在自己的根域名（例如 example.com/）就填 "/"
BASE_PATH = "/podcast-site/"

# 首页"最近更新"区块显示几条
RECENT_COUNT = 6
# 多少天内算"NEW"
NEW_DAYS = 7
# 大约多少个字算 1 分钟阅读
CHARS_PER_MINUTE = 400


# ── 工具函数 ──────────────────────────────────────────────────────
def to_date(value):
    """把 yaml/frontmatter 里可能是 str 或 date 的字段统一转成 date 对象"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def slugify(text):
    text = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", text.strip())
    return text.strip("-")


def read_minutes(raw_text):
    char_count = len(re.sub(r"\s", "", raw_text))
    return max(1, round(char_count / CHARS_PER_MINUTE))


def load_shows():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        shows = yaml.safe_load(f) or []
    return {s["slug"]: s for s in shows}, shows


def load_episodes(shows_by_slug):
    """遍历 content/ 下所有 .md 文件，返回按 show 分组的 episode 列表"""
    episodes_by_show = {slug: [] for slug in shows_by_slug}
    all_episodes = []
    today = date.today()

    if not CONTENT_DIR.exists():
        return episodes_by_show, all_episodes

    for show_dir in sorted(CONTENT_DIR.iterdir()):
        if not show_dir.is_dir():
            continue
        show_slug = show_dir.name
        if show_slug not in shows_by_slug:
            print(f"⚠️  警告：content/{show_slug}/ 在 shows.yaml 里找不到对应节目，已跳过")
            continue

        show = shows_by_slug[show_slug]

        for md_file in sorted(show_dir.glob("*.md")):
            post = frontmatter.load(md_file)
            meta = post.metadata
            ep_date = to_date(meta["date"])
            body_html = md.markdown(post.content, extensions=["tables", "fenced_code"])
            stem = md_file.stem
            url_slug = f"{show_slug}/{stem}"

            ep = {
                "title": meta.get("title", stem),
                "date": ep_date.isoformat(),
                "date_obj": ep_date,
                "show_slug": show_slug,
                "show_name": show["name"],
                "show_color": show.get("color", "#4a90d9"),
                "summary": meta.get("summary", ""),
                "tags": meta.get("tags", []) or [],
                "source_episode": meta.get("source_episode", ""),
                "source_url": meta.get("source_url", ""),
                "processed_date": meta.get("processed_date", ep_date.isoformat()),
                "original_language": meta.get("original_language", show.get("language", "")),
                "body_html": body_html,
                "read_minutes": read_minutes(post.content),
                "url_slug": url_slug,
                "is_new": (today - ep_date) <= timedelta(days=NEW_DAYS),
            }
            days_ago = (today - ep_date).days
            ep["days_ago_label"] = f"{days_ago} 天前" if days_ago > 0 else "今天"

            episodes_by_show[show_slug].append(ep)
            all_episodes.append(ep)

    for slug in episodes_by_show:
        episodes_by_show[slug].sort(key=lambda e: e["date_obj"], reverse=True)

    all_episodes.sort(key=lambda e: e["date_obj"], reverse=True)
    return episodes_by_show, all_episodes


def build_show_summaries(shows_list, episodes_by_show):
    today = date.today()
    result = []
    for show in shows_list:
        eps = episodes_by_show.get(show["slug"], [])
        last_updated = eps[0]["date_obj"] if eps else None
        result.append({
            **show,
            "episode_count": len(eps),
            "last_updated": last_updated.isoformat() if last_updated else None,
            "last_updated_obj": last_updated,
            "is_new": bool(last_updated) and (today - last_updated) <= timedelta(days=NEW_DAYS),
        })
    # 有更新的排前面（按最近更新时间倒序），没有内容的排后面（按名称）
    with_content = sorted(
        [s for s in result if s["last_updated_obj"]],
        key=lambda s: s["last_updated_obj"], reverse=True,
    )
    without_content = sorted(
        [s for s in result if not s["last_updated_obj"]],
        key=lambda s: s["name"],
    )
    return with_content + without_content


def build_search_index(all_episodes):
    return [
        {
            "title": e["title"],
            "show": e["show_name"],
            "date": e["date"],
            "summary": e["summary"],
            "tags": " ".join(e["tags"]),
            "url": f"{BASE_PATH}episode/{e['url_slug']}/",
        }
        for e in all_episodes
    ]


# ── 主流程 ────────────────────────────────────────────────────────
def main():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    shows_by_slug, shows_list_raw = load_shows()
    episodes_by_show, all_episodes = load_episodes(shows_by_slug)
    shows = build_show_summaries(shows_list_raw, episodes_by_show)
    categories = sorted({s["category"] for s in shows})

    stats = {
        "show_count": len(shows),
        "episode_count": len(all_episodes),
    }

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), trim_blocks=True, lstrip_blocks=True)
    env.globals["root"] = BASE_PATH
    env.globals["stats"] = stats

    # 首页
    recent = all_episodes[:RECENT_COUNT]
    index_html = env.get_template("index.html").render(
        shows=shows,
        categories=categories,
        recent_episodes=recent,
        search_index_json=json.dumps(build_search_index(all_episodes), ensure_ascii=False),
    )
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    # 更新时间线
    updates_dir = OUTPUT_DIR / "updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    (updates_dir / "index.html").write_text(
        env.get_template("updates.html").render(episodes=all_episodes), encoding="utf-8"
    )

    # 节目页 + 单集页
    show_tpl = env.get_template("show.html")
    ep_tpl = env.get_template("episode.html")
    for show in shows:
        show_dir = OUTPUT_DIR / "show" / show["slug"]
        show_dir.mkdir(parents=True, exist_ok=True)
        eps = episodes_by_show.get(show["slug"], [])
        (show_dir / "index.html").write_text(
            show_tpl.render(show=show, episodes=eps), encoding="utf-8"
        )
        for ep in eps:
            ep_dir = OUTPUT_DIR / "episode" / ep["url_slug"]
            ep_dir.mkdir(parents=True, exist_ok=True)
            (ep_dir / "index.html").write_text(
                ep_tpl.render(show=show, ep=ep), encoding="utf-8"
            )

    # 静态资源
    static_out = OUTPUT_DIR / "static"
    shutil.copytree(STATIC_SRC_DIR, static_out)

    # GitHub Pages 不要用 Jekyll 处理
    (OUTPUT_DIR / ".nojekyll").touch()

    print(f"✅ 生成完成：{stats['show_count']} 档节目，{stats['episode_count']} 篇文字稿")
    print(f"   输出目录：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
