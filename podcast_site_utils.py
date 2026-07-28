"""podcast_site_utils.py — 播客站同步工具"""

import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PODCAST_SITE_DIR = BASE_DIR / "podcast-site"
TRANSCRIPTS_DIR = PODCAST_SITE_DIR / "transcripts"


def slugify(text: str) -> str:
    import re
    slug = text.strip()
    slug = re.sub(r'[^\w\- ]', '', slug)
    slug = slug.strip().replace(' ', '_')
    return slug or "untitled"


def save_to_podcast_site(draft_path: Path, show_slug: str, episode_date: str) -> Path | None:
    """
    复制 articles/{slug}/draft.md → podcast-site/transcripts/{show_slug}/{date}-{slug}.md
    """
    if not draft_path or not draft_path.exists():
        return None
    if not show_slug:
        return None

    slug = draft_path.parent.name
    target_dir = TRANSCRIPTS_DIR / show_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    title_part = slug[len(episode_date)+1:] if slug.startswith(episode_date) else slug
    short_part = title_part[:35].rstrip('-_')
    target_name = f"{episode_date}-{short_part}.md"
    target_path = target_dir / target_name

    try:
        shutil.copy2(draft_path, target_path)
        print(f"  ✅ 已同步到播客站: {target_path}")
    except Exception as e:
        print(f"  ⚠️  同步到播客站失败: {e}")
        return None

    return target_path
