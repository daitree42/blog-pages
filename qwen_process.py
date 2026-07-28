#!/usr/bin/env python3
"""
qwen_process.py — 用本地 Qwen3 校对已转录的播客文本并发布到博客

用法:
  python qwen_process.py --input 原始转录.txt --show "The Daily" --episode "标题"
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "qwen3:4b"


def log(msg):
    print(f"  {msg}")


def slugify(text: str) -> str:
    slug = re.sub(r'[^\w\- ]', '', text.strip())
    return slug.strip().replace(' ', '_') or "untitled"


def call_ollama(prompt: str, system: str = "") -> str:
    """调用本地 Ollama Qwen 模型"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"num_ctx": 32768, "temperature": 0.3, "num_gpu": 0},
    }
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(f"Ollama 错误: {result['error']}")
    return result.get("response", "").strip()


def process_chunk(text: str, system_prompt: str, show: str, episode: str, part: int, total: int) -> dict:
    if total == 1:
        user_prompt = f"""Process this podcast transcript and output JSON.

## Podcast Info
- Show: {show}
- Episode: {episode}
- Language: English

## Instructions
1. Proofread and fix grammar/spelling errors
2. Remove filler words (um, uh, like, you know, sort of, basically, etc.)
3. Merge short fragments into flowing paragraphs
4. Add ## section headings at natural topic breaks
5. Keep ALL substantive content
6. Generate a concise summary (under 200 words)
7. Add source info at the end

## Output Format (pure JSON, no code blocks)
{{"title": "Article title (catchy, under 80 chars)",
 "summary": "Summary under 200 words",
 "body_md": "Full organized article in Markdown format"}}

## Transcript
{text}
"""
    else:
        user_prompt = f"""This is part {part}/{total} of a podcast transcript ({show} - {episode}).
Append the following new text naturally after previously processed parts.
Maintain consistent style and continue using ## headings.

## New Text
{text}

## Output Format (pure JSON)
{{"body_md": "The processed text for this part in Markdown"}}
"""

    resp = call_ollama(user_prompt, system_prompt)
    resp = re.sub(r'^```(?:json)?\s*\n', '', resp)
    resp = re.sub(r'\n```\s*$', '', resp)

    try:
        return json.loads(resp)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"body_md": text}


def generate_article(processed: dict, show_name: str, episode_title: str,
                     episode_date: str, category: str, tags: list[str],
                     episode_link: str, original_text: str) -> Path:
    title = processed.get("title", f"{show_name} {episode_title}")
    summary = processed.get("summary", "")
    body_md = processed.get("body_md", "")
    episode_date = episode_date or datetime.now().strftime("%Y-%m-%d")

    source_note = (
        f"\n\n---\n\n"
        f"**Source:** {show_name} · {episode_title}"
        f"{' · [Original Link](' + episode_link + ')' if episode_link else ''}\n"
        f"**Processing Date:** {episode_date}\n"
    )

    full_article = body_md + source_note
    full_article += (
        f"\n\n## 📝 Original Transcript\n\n"
        f"<details>\n<summary>Click to expand the full original transcript</summary>\n\n"
        f"{original_text}\n\n"
        f"</details>\n"
    )

    en_words = len(full_article.split())
    reading_time = max(1, round(en_words / 200))

    short_show = slugify(show_name)[:20].rstrip('-_')
    short_title = slugify(episode_title)[:25].rstrip('-_')
    slug = f"{episode_date}-{short_show}-{short_title}"
    article_dir = ARTICLES_DIR / slug
    article_dir.mkdir(parents=True, exist_ok=True)
    draft_path = article_dir / "draft.md"

    tags_str = "，".join(tags) if tags else ""
    content = f"# {title}\n\n"
    content += f"> 栏目：{category}\n"
    content += f"> 日期：{episode_date}\n"
    content += f"> 阅读时间：{reading_time} 分钟\n"
    if tags_str:
        content += f"> 标签：{tags_str}\n"
    content += f"> 摘要：{summary}\n\n<div class=\"post-body\">\n"
    content += full_article + "\n</div>\n"

    draft_path.write_text(content, encoding="utf-8")
    log(f"✅ 文章已生成: {draft_path}")
    return draft_path


def main():
    parser = argparse.ArgumentParser(description="Qwen3 校对播客转录文本")
    parser.add_argument("--input", required=True, help="原始转录文本文件")
    parser.add_argument("--show", required=True, help="播客名称")
    parser.add_argument("--episode", required=True, help="期数/标题")
    parser.add_argument("--date", default="", help="发布日期")
    parser.add_argument("--category", default="播客", help="分类")
    parser.add_argument("--tags", default="播客,The Daily,NYT", help="标签")
    parser.add_argument("--link", default="https://www.nytimes.com/the-daily", help="链接")
    parser.add_argument("--build", action="store_true", help="构建博客")
    parser.add_argument("--dry-run", action="store_true", help="仅规划")

    args = parser.parse_args()
    episode_date = args.date or datetime.now().strftime("%Y-%m-%d")
    tags_list = [t.strip() for t in args.tags.replace("，", ",").split(",") if t.strip()]

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    raw_text = input_path.read_text(encoding="utf-8").strip()

    print(f"\n🎙️  Qwen3 播客校对")
    print(f"   {'='*40}")
    print(f"   节目:   {args.show}")
    print(f"   期数:   {args.episode}")
    print(f"   文本:   {len(raw_text)} 字符")
    print(f"   模型:   {OLLAMA_MODEL}")
    print(f"   {'='*40}\n")

    if args.dry_run:
        return

    preview = raw_text[:150].replace('\n', ' ')
    print(f"📝 原文预览: {preview}...\n")

    system_prompt = (
        "You are a professional podcast transcript editor. "
        "Proofread and organize the transcript into a well-structured article. "
        "Remove filler words, merge fragments into flowing paragraphs, "
        "add ## section headings at topic breaks. Keep ALL substantive content."
    )

    MAX_CHARS = 25000
    if len(raw_text) <= MAX_CHARS:
        log("🤖 调用 Qwen3 处理...")
        processed = process_chunk(raw_text, system_prompt, args.show, args.episode, 1, 1)
    else:
        log(f"📄 文本较长 ({len(raw_text)} 字符)，分段处理...")
        chunks = [raw_text[i:i + MAX_CHARS] for i in range(0, len(raw_text), MAX_CHARS)]
        log(f"🤖 处理第 1/{len(chunks)} 段...")
        processed = process_chunk(chunks[0], system_prompt, args.show, args.episode, 1, len(chunks))
        body_parts = [processed.get("body_md", "")]
        for i, chunk in enumerate(chunks[1:], 2):
            log(f"🤖 处理第 {i}/{len(chunks)} 段...")
            cr = process_chunk(chunk, system_prompt, args.show, args.episode, i, len(chunks))
            body_parts.append(cr.get("body_md", chunk))
        processed["body_md"] = "\n\n".join(body_parts)

    log(f"   ✅ 处理完成")
    log(f"   📰 标题: {processed.get('title', processed.get('body_md', '')[:50])}")
    summary = processed.get("summary", "")
    if summary:
        log(f"   📋 摘要: {summary[:100]}...")

    draft_path = generate_article(
        processed, args.show, args.episode,
        episode_date, args.category, tags_list,
        args.link, raw_text,
    )

    # 同步到播客站
    show_slug = slugify(args.show).lower()
    from podcast_site_utils import save_to_podcast_site
    save_to_podcast_site(draft_path, show_slug, episode_date)

    if args.build:
        log("\n🔨 运行 publish.py build...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "publish.py"), "build"],
            cwd=str(BASE_DIR), capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print(f"⚠️  {result.stderr}")

    print(f"\n✅ 全部完成！")
    print(f"   文章: {draft_path}")
    print(f"   预览: cd {BASE_DIR} && python publish.py serve")
    print()


if __name__ == "__main__":
    main()
