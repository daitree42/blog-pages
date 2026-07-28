#!/usr/bin/env python3
"""从混合zh.txt提取纯中文，重新生成文章：纯中文正文 + 英文折叠区"""
import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
RAW = BASE / "podcast-site" / "transcripts_raw"
ARTICLES = BASE / "articles"
DATE = "2026-07-28"
SHOW = "The Daily"
LINK = "https://www.nytimes.com/the-daily"

FILES = [
    "Can a Bad Man Be a Good Father",
    "Cuba Under Siege",
    "The Mother Who Changed a Story of Dementia",
    "What Do You Do When a Family Member Commits a Terrible Crime",
    "Why Do Some Memories Survive Dementia",
]

def is_chinese_line(line):
    """判断一行是否主要是中文"""
    if not line.strip():
        return False
    cjk = sum(1 for c in line if '一' <= c <= '鿿' or '　' <= c <= '〿')
    ascii_chars = sum(1 for c in line if c.isascii() and c.isalpha())
    return cjk > ascii_chars and cjk > 5

def extract_chinese_only(zh_text):
    """从交替排列的英文+中文中提取纯中文，按原文段落结构合并"""
    # 按空行分原始段落
    raw_paragraphs = re.split(r'\n\s*\n', zh_text)
    result_paras = []

    for para in raw_paragraphs:
        lines = para.strip().split('\n')
        # 提取其中中文行
        zh_lines = []
        for line in lines:
            stripped = line.strip()
            if is_chinese_line(stripped):
                zh_lines.append(stripped)

        if zh_lines:
            # 合并为一个段落
            merged = ''.join(zh_lines)
            result_paras.append(merged)

    # 合并短段，使每段至少120字
    final = []
    buffer = ""
    for p in result_paras:
        if not buffer:
            buffer = p
        elif len(buffer) < 120:
            buffer += p
        else:
            final.append(buffer)
            buffer = p
    if buffer:
        if final and len(buffer) < 60 and len(buffer) + len(final[-1]) < 300:
            final[-1] += buffer
        else:
            final.append(buffer)

    return '\n\n'.join(final)

def slugify(text):
    return re.sub(r'[^\w\- ]', '', text.strip()).strip().replace(' ', '_') or "untitled"

for title in FILES:
    # 找文件
    norm_title = title.replace(' ', '_')
    zh_file = en_file = None
    for f in RAW.glob(f"*{norm_title[:15]}*"):
        if '.zh.txt' in f.name:
            zh_file = f
        elif '.txt' in f.name and '.zh' not in f.name:
            en_file = f

    if not zh_file or not en_file:
        print(f"❌ 找不到文件: {title}")
        continue

    zh_mixed = zh_file.read_text(encoding="utf-8")
    en_text = en_file.read_text(encoding="utf-8").strip()

    # 提取纯中文
    zh_only = extract_chinese_only(zh_mixed)

    # 如果提取的太少，可能格式不同（纯中文），直接用原文
    if len(zh_only) < 100:
        zh_only = zh_mixed.strip()

    # 段落格式化：在自然断点加分段
    en_words = len(en_text.split())
    reading_time = max(1, round(en_words / 200))

    short_title = slugify(title)[:25].rstrip('-_')
    slug = f"{DATE}-The_Daily-{short_title}"
    article_dir = ARTICLES / slug
    article_dir.mkdir(parents=True, exist_ok=True)
    draft_path = article_dir / "draft.md"

    content = f"# {title}\n\n"
    content += f"> 栏目：播客\n"
    content += f"> 日期：{DATE}\n"
    content += f"> 阅读时间：{reading_time} 分钟\n"
    content += f"> 标签：播客，The Daily，NYT\n"
    content += f"> 摘要：{SHOW} · {title} 英文播客中文翻译\n"
    content += f'\n<div class="post-body">\n\n'
    content += zh_only
    content += f"\n\n</div>\n\n---\n\n"
    content += f"**Source:** {SHOW} · {title} · [Original Link]({LINK})\n"
    content += f"**Processing Date:** {DATE}\n"
    content += f"\n## 📝 英文原文\n\n<details>\n<summary>点击展开英文原文</summary>\n\n"
    content += en_text
    content += "\n\n</details>\n"

    draft_path.write_text(content, encoding="utf-8")
    print(f"✅ {title}: {len(zh_only)} 字中文")

print("\n全部文章已重新生成！")
