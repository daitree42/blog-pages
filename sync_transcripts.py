#!/usr/bin/env python3
"""将修复后的文章同步到 podcast-site/transcripts/this-american-life/"""
import shutil, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"
TARGET_DIR = BASE_DIR / "podcast-site" / "transcripts" / "this-american-life"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

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

for slug in SLUGS:
    src = ARTICLES_DIR / slug / "draft.md"
    if not src.exists():
        print(f"❌ 不存在: {slug}")
        continue
    # copy to target with slug name + .md
    tgt = TARGET_DIR / f"{slug}.md"
    shutil.copy2(src, tgt)
    print(f"✅ {slug}")

print(f"\n已同步 {len(SLUGS)} 篇到 {TARGET_DIR}")
