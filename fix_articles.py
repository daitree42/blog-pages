#!/usr/bin/env python3
"""
fix_articles.py — 修复批量生成的文章质量问题
1. 移除翻译文本中残留的提示词
2. 统一段落格式
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPTS_RAW_DIR = BASE_DIR / "podcast-site" / "transcripts_raw"
ARTICLES_DIR = BASE_DIR / "articles"

def clean_translation(text):
    """移除翻译文本开头的提示词残留"""
    lines = text.strip().split('\n')
    # 如果开头有 "播客: ..." 和 "逐句翻译..." 行，移除
    cleaned = []
    skip_header = True
    for line in lines:
        if skip_header:
            stripped = line.strip()
            # 跳过广告语开头
            if stripped.startswith('The New York Times app') or stripped.startswith('《纽约时报》应用'):
                skip_header = False
                cleaned.append(line)
                continue
            if skip_header and (
                stripped.startswith('播客:') or
                stripped.startswith('逐句翻译') or
                stripped == ''
            ):
                continue
            skip_header = False
        cleaned.append(line)
    return '\n'.join(cleaned).strip()

def rebuild_article(episode_title, show_name, chinese_text, raw_text):
    """重新生成格式统一的文章"""
    en_words = len(raw_text.split())
    reading_time = max(1, round(en_words / 200))
    date = "2026-07-28"

    content = f"# {episode_title}\n\n"
    content += f"> 栏目：播客\n"
    content += f"> 日期：{date}\n"
    content += f"> 阅读时间：{reading_time} 分钟\n"
    content += f"> 标签：播客，The Daily，NYT\n"
    content += f"> 摘要：{show_name} · {episode_title} 英文播客中文翻译\n"
    content += f'\n<div class="post-body">\n'

    # 清洗中文文本
    chinese_text = clean_translation(chinese_text)

    # 按段落拆分，添加空行分隔
    paragraphs = re.split(r'\n\s*\n', chinese_text)
    content += '\n\n'.join(p.strip() for p in paragraphs if p.strip())

    content += f"\n\n---\n\n"
    content += f"**Source:** {show_name} · {episode_title} · [Original Link](https://www.nytimes.com/the-daily)\n"
    content += f"**Processing Date:** {date}\n"
    content += f"\n## 📝 英文原文\n\n<details>\n<summary>点击展开英文原文</summary>\n\n"
    content += raw_text
    content += "\n\n</details>\n</div>\n"
    return content


def main():
    # 查找所有今天的原始转录和中文翻译
    raw_files = sorted(TRANSCRIPTS_RAW_DIR.glob("2026-07-28-*.txt"))
    zh_files = sorted(TRANSCRIPTS_RAW_DIR.glob("2026-07-28-*.zh.txt"))

    for zh_file in zh_files:
        # 找到对应的原始英文文件
        base_name = zh_file.stem.replace('.zh', '')
        raw_file = TRANSCRIPTS_RAW_DIR / f"{base_name}.txt"
        if not raw_file.exists():
            print(f"⚠️  找不到英文原文: {raw_file.name}")
            continue

        # 读取内容
        chinese_text = zh_file.read_text(encoding="utf-8")
        cleaned_zh = clean_translation(chinese_text)

        # 检查是否被清理（有变化才写回）
        if cleaned_zh != chinese_text.strip():
            zh_file.write_text(cleaned_zh, encoding="utf-8")
            print(f"✅ 清理: {zh_file.name}")

        # 读取英文原文
        raw_text = raw_file.read_text(encoding="utf-8").strip()

        # 找到对应的文章目录
        from slugify import slugify
        short_show = slugify("The Daily")[:20].rstrip('-_')
        short_title = slugify(episode_title_from_file(zh_file))[:25].rstrip('-_')
        slug = f"2026-07-28-{short_show}-{short_title}"

        article_dir = ARTICLES_DIR / slug
        draft_path = article_dir / "draft.md"

        if not draft_path.exists():
            print(f"⚠️  找不到文章: {draft_path}")
            # 尝试模糊匹配
            matched = list(ARTICLES_DIR.glob(f"*{short_title}*/draft.md"))
            if matched:
                draft_path = matched[0]
                print(f"   改用: {draft_path}")
            else:
                continue

        # 检查文章是否有问题（开头是否包含提示词）
        draft_content = draft_path.read_text(encoding="utf-8")
        if '播客:' in draft_content.split('\n')[5:15]:
            print(f"🔧 修复文章: {draft_path.parent.name}")

            # 重写文章
            show_name = "The Daily"
            title = episode_title_from_file(zh_file)
            new_content = rebuild_article(title, show_name, cleaned_zh, raw_text)
            draft_path.write_text(new_content, encoding="utf-8")
            print(f"  ✅ 已重写")
        else:
            print(f"  ✓ 无问题: {draft_path.parent.name}")


def slugify(text):
    slug = re.sub(r'[^\w\- ]', '', text.strip())
    return slug.strip().replace(' ', '_') or "untitled"

def episode_title_from_file(zh_file):
    """从文件名提取节目名称"""
    name = zh_file.stem.replace('.zh', '')
    # 格式: 2026-07-28-The_Daily-Episode_Title
    parts = name.split('-', 2)
    if len(parts) >= 3:
        title_part = parts[2]
    else:
        title_part = parts[-1] if len(parts) > 1 else parts[0]
    title = title_part.replace('_', ' ')
    return title


if __name__ == "__main__":
    main()
