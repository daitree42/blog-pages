#!/usr/bin/env python3
"""修复8篇TAL文章的排版：将 post-body 内的 Markdown 转为 HTML"""
import re, sys
from pathlib import Path
import markdown as md_lib

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"

SLUGS = [
    "2026-07-29-This_American_Life-878_New_Lore_Drop",
    "2026-07-29-This_American_Life-884_The_Idiot",
    "2026-07-29-This_American_Life-885_Bless_This_Mess",
    "2026-07-29-This_American_Life-886_Blackout",
    "2026-07-29-This_American_Life-887_Two_Is_One_One_Is_Non",
    "2026-07-29-This_American_Life-888_Not_Today_Hades",
    "2026-07-29-This_American_Life-889_Theres_Something_Abou",
    "2026-07-29-This_American_Life-890_Maximal_Americanness",
]

def fix_article(slug):
    draft_path = ARTICLES_DIR / slug / "draft.md"
    if not draft_path.exists():
        print(f"❌ 不存在: {slug}")
        return False

    text = draft_path.read_text(encoding="utf-8")

    # 提取 post-body 内的内容
    m = re.search(r'<div class="post-body">\s*(.*?)\s*</div>', text, re.DOTALL)
    if not m:
        print(f"⚠️  无 post-body: {slug}")
        return False

    body_md = m.group(1)

    # 判断是否已经包含 HTML 标签
    if re.search(r'<(p|h[1-6]|div|ul|ol|li|table|hr)[\s>]', body_md[:500]):
        print(f"⏭  已有 HTML，跳过: {slug}")
        return False

    # 转换 Markdown → HTML
    body_html = md_lib.markdown(body_md, extensions=['fenced_code', 'tables', 'codehilite'])

    # 替换回文本
    text = text.replace(body_md, body_html)

    draft_path.write_text(text, encoding="utf-8")
    print(f"✅ 已修复: {slug}")
    return True

if __name__ == "__main__":
    ok = 0
    for slug in SLUGS:
        if fix_article(slug):
            ok += 1
    print(f"\n完成: 修复 {ok}/{len(SLUGS)} 篇")
