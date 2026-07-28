#!/usr/bin/env python3
"""
podcast_local.py — 播客处理全流程（使用本地 Ollama Qwen 模型）

流程:
  1. 下载 RSS feed 音频（可选）
  2. faster-whisper 转录
  3. Ollama Qwen3:8b 校对/整理（英文保持原文 + 整理版）
  4. 生成 blog-pages 文章
  5. 可选：构建博客

用法:
  python podcast_local.py audio.mp3 --show "The Daily" --episode "标题"
  python podcast_local.py audio.mp3 --show "The Daily" --episode "标题" --build
  python podcast_local.py --rss RSS_URL --show "The Daily"  # 从 RSS 下载最新集
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "qwen3:8b"


def log(msg):
    print(f"  {msg}")


def slugify(text: str) -> str:
    slug = text.strip()
    slug = re.sub(r'[^一-鿿\w\- ]', '', slug)
    slug = slug.strip().replace(' ', '_')
    return slug or "untitled"


def format_timestamp(seconds: float) -> str:
    s = int(seconds)
    h, m = divmod(s, 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def run_ffmpeg(input_path: Path, output_path: Path):
    """转码为 16kHz 单声道 WAV"""
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", str(output_path)]
    log("🎵 转码中...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败:\n{result.stderr}")
    log(f"✅ 转码完成: {output_path.name}")


def download_rss_audio(rss_url: str, output_path: Path):
    """从 RSS feed 下载最新一集的音频"""
    log(f"📡 获取 RSS: {rss_url}")
    req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    tree = ET.parse(resp)
    root = tree.getroot()

    # 找到第一个 item
    item = root.find(".//item")
    if item is None:
        # 有时是 RSS 2.0 命名空间
        ns = {"": "http://www.w3.org/2005/Atom"}
        # 尝试默认命名空间
        for ns_name in ["", "http://www.w3.org/2005/Atom"]:
            items = root.findall(f".//{{{ns_name}}}entry") if ns_name else root.findall(".//entry")
            if items:
                item = items[0]
                break

    if item is None:
        # 标准 RSS 2.0
        item = root.find(".//channel/item")
    if item is None:
        raise RuntimeError("无法从 RSS 中找到节目")

    # 获取标题
    title_el = item.find("title")
    title = title_el.text.strip() if title_el is not None and title_el.text else "Unknown"

    # 获取音频 URL
    enclosure = item.find("enclosure")
    audio_url = None
    if enclosure is not None:
        audio_url = enclosure.get("url")

    # 如果 enclosure 没有，尝试 media:content
    if not audio_url:
        media = item.find("{http://search.yahoo.com/mrss/}content")
        if media is not None:
            audio_url = media.get("url")

    if not audio_url:
        raise RuntimeError("未找到音频 URL")

    # 获取时长
    duration_el = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
    duration_str = duration_el.text.strip() if duration_el is not None and duration_el.text else ""

    log(f"📖 最新集: {title}")
    log(f"⏱  时长: {duration_str}")
    log(f"⬇️  下载音频 ({audio_url[:80]}...)")

    urllib.request.urlretrieve(audio_url, output_path)
    size_mb = output_path.stat().st_size / 1024 / 1024
    log(f"✅ 下载完成: {size_mb:.1f} MB")

    return title, duration_str


def transcribe(audio_path: Path, language: str = "en", model_size: str = "medium"):
    """使用 faster-whisper 转录"""
    from faster_whisper import WhisperModel

    # 找本地缓存
    local_model = _find_cached_whisper_model(model_size)
    model_path = local_model or model_size
    if local_model:
        log(f"使用本地缓存模型: {local_model}")
    else:
        log(f"从 HuggingFace 下载模型...")

    try:
        model = WhisperModel(model_path, device="auto", compute_type="float16")
    except Exception:
        model = WhisperModel(model_path, device="cpu", compute_type="float32")

    log(f"🎙️  转录中（模型: {model_size}，语言: {language}）...")
    segments_raw, info = model.transcribe(
        str(audio_path),
        language=language if language != "auto" else None,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    segments = []
    text_parts = []
    for seg in segments_raw:
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        text_parts.append(seg.text.strip())

    full_text = " ".join(text_parts)
    duration = info.duration if info.duration else 0

    log(f"✅ 转录完成: {len(segments)} 段, 约 {duration:.0f}s 音频, {len(full_text)} 字符")
    return full_text, segments


def _find_cached_whisper_model(model_size: str) -> Optional[str]:
    cache_dirs = [
        Path(os.environ.get("WHISPER_MODEL_DIR", "")),
        Path.home() / ".cache" / "huggingface" / "hub",
        Path(os.environ.get("HF_HOME", "")) / "hub",
    ]
    repo = f"models--Systran--faster-whisper-{model_size}"
    for cd in cache_dirs:
        if not cd or not cd.exists():
            continue
        snapshots_dir = cd / repo / "snapshots"
        if not snapshots_dir.exists():
            continue
        for sp in sorted(snapshots_dir.iterdir()):
            if (sp / "model.bin").exists():
                return str(sp)
    return None


def call_ollama(prompt: str, system: str = "") -> str:
    """调用本地 Ollama Qwen 模型"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "num_ctx": 32768,
            "temperature": 0.3,
            "num_gpu": 0,
        }
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


def process_text_with_qwen(full_text: str, show_name: str, episode_title: str) -> dict:
    """使用 Qwen3 对转录文本进行校对和整理"""
    system_prompt = (
        "You are a professional podcast transcript editor. Your task is to:\n"
        "1. Proofread and organize the transcript into a well-structured article\n"
        "2. Remove filler words (um, uh, you know, like, sort of, etc.)\n"
        "3. Merge fragmented sentences into natural paragraphs\n"
        "4. Add clear section headings (## style) at topic transitions\n"
        "5. Keep EVERYTHING important - do not delete any substantive content\n"
        "6. Output in valid JSON format only"
    )

    # 分段处理——先检查长度
    MAX_CHARS = 30000  # Qwen3 上下文限制内安全长度
    if len(full_text) <= MAX_CHARS:
        return _call_qwen_once(full_text, system_prompt, show_name, episode_title)

    # 长文本分段处理
    log(f"📄 文本较长 ({len(full_text)} 字符)，分段处理...")
    chunks = [full_text[i:i + MAX_CHARS] for i in range(0, len(full_text), MAX_CHARS)]

    # 第一段
    result = _call_qwen_once(chunks[0], system_prompt, show_name, episode_title)
    body_parts = [result.get("body_md", "")]
    summaries = [result.get("summary", "")]
    titles = [result.get("title", f"{show_name} {episode_title}")]

    # 后续段落增量追加
    for i, chunk in enumerate(chunks[1:], 2):
        meta_info = f"Episode: {show_name} - {episode_title}\nThis is part {i}/{len(chunks)}.\nAppend the following new text naturally after the previously processed parts. Maintain consistent style and continue using ## headings."
        chunk_prompt = f"{meta_info}\n\n## New Text to Append\n\n{chunk}"
        resp = call_ollama(chunk_prompt, system_prompt)
        try:
            cr = json.loads(resp)
            body_parts.append(cr.get("body_md", chunk))
            summaries.append(cr.get("summary", ""))
        except json.JSONDecodeError:
            body_parts.append(chunk)

    return {
        "title": titles[0],
        "summary": " ".join(filter(None, summaries))[:200],
        "body_md": "\n\n".join(body_parts),
    }


def _call_qwen_once(text: str, system_prompt: str, show_name: str, episode_title: str) -> dict:
    """单段调用 Qwen 整理"""
    user_prompt = f"""Process this podcast transcript and output JSON.

## Podcast Info
- Show: {show_name}
- Episode: {episode_title}
- Language: English

## Instructions
1. Proofread and fix grammar/spelling errors
2. Remove filler words (um, uh, like, you know, sort of, basically, etc.)
3. Merge short fragments into flowing paragraphs
4. Add ## section headings at natural topic breaks
5. Keep ALL substantive content - do not delete or summarize away any substantive discussion, data points, quotes, or arguments
6. Generate a concise summary (under 200 words)
7. Add source info at the end: show name, episode, and processing date

## Output Format (pure JSON, no markdown code blocks)
{{"title": "Article title (catchy, under 80 chars)",
 "summary": "Summary under 200 words",
 "body_md": "Full organized article in Markdown format"}}

## Transcript
{text}
"""
    resp = call_ollama(user_prompt, system_prompt)

    # 解析 JSON
    resp = re.sub(r'^```(?:json)?\s*\n', '', resp)
    resp = re.sub(r'\n```\s*$', '', resp)
    try:
        result = json.loads(resp)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', resp, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
            except json.JSONDecodeError:
                result = {"title": f"{show_name} {episode_title}", "summary": "", "body_md": text}
        else:
            result = {"title": f"{show_name} {episode_title}", "summary": "", "body_md": text}

    result.setdefault("title", f"{show_name} {episode_title}")
    result.setdefault("summary", "")
    result.setdefault("body_md", text)
    return result


def generate_article(processed: dict, show_name: str, episode_title: str,
                     episode_date: str, category: str, tags: list[str],
                     episode_link: str, original_text: str) -> Path:
    """生成博客文章，包含原文和整理版"""
    title = processed.get("title", f"{show_name} {episode_title}")
    summary = processed.get("summary", "")
    body_md = processed.get("body_md", "")

    # 添加原文（保持原文不删减）
    source_note = (
        f"\n\n---\n\n"
        f"**Source:** {show_name} · {episode_title}"
        f"{' · [Original Link](' + episode_link + ')' if episode_link else ''}\n"
        f"**Processing Date:** {episode_date}\n"
    )

    # 在文章末尾添加完整原文
    full_article = body_md + source_note
    full_article += (
        f"\n\n## 📝 Original Transcript\n\n"
        f"<details>\n<summary>Click to expand the full original transcript</summary>\n\n"
        f"{original_text}\n\n"
        f"</details>\n"
    )

    # 计算阅读时间
    zh_chars = len(re.findall(r'[一-鿿]', full_article))
    reading_time = max(1, round(zh_chars / 500))
    # 英文按单词数算
    en_words = len(full_article.split())
    if zh_chars < 100:
        reading_time = max(1, round(en_words / 200))

    # 生成 slug
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
    content += f"> 摘要：{summary}\n"
    content += f"\n"
    content += f'<div class="post-body">\n'
    content += full_article
    content += f'\n</div>\n'

    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(content)

    log(f"✅ 文章已生成: {draft_path}")
    return draft_path


def main():
    parser = argparse.ArgumentParser(description="播客处理（本地 Qwen 版）")
    parser.add_argument("audio", nargs="?", help="音频文件路径")
    parser.add_argument("--rss", help="RSS feed URL（自动下载最新集）")
    parser.add_argument("--show", required=True, help="播客名称")
    parser.add_argument("--episode", default="", help="期数/标题（留空从 RSS 自动获取）")
    parser.add_argument("--lang", default="en", help="音频语言 (默认 en)")
    parser.add_argument("--date", default="", help="发布日期 (默认今天)")
    parser.add_argument("--category", default="播客", help="博客分类")
    parser.add_argument("--tags", default="播客,The Daily,NYT", help="标签，逗号分隔")
    parser.add_argument("--link", default="https://www.nytimes.com/the-daily", help="原始链接")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="whisper 模型大小 (默认 medium)")
    parser.add_argument("--build", action="store_true", help="处理完后自动构建博客")
    parser.add_argument("--dry-run", action="store_true", help="仅显示流程规划")
    parser.add_argument("--show-slug", default="the-daily", help="播客站 slug")

    args = parser.parse_args()
    episode_date = args.date or datetime.now().strftime("%Y-%m-%d")
    tags_list = [t.strip() for t in args.tags.replace("，", ",").split(",") if t.strip()]

    # ── 音频来源 ──────────────────────────────────────────────
    audio_path = None
    episode_title = args.episode

    if args.rss:
        log(f"📻 从 RSS 获取最新集: {args.rss}")
        tmp_dir = tempfile.mkdtemp(prefix="podcast_")
        tmp_path = Path(tmp_dir) / "episode.mp3"
        fetched_title, duration_str = download_rss_audio(args.rss, tmp_path)
        audio_path = tmp_path
        if not episode_title:
            episode_title = fetched_title
    elif args.audio:
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(f"❌ 文件不存在: {audio_path}")
            sys.exit(1)
        if not episode_title:
            episode_title = audio_path.stem
        tmp_dir = None
    else:
        print("❌ 请提供音频文件或 --rss URL")
        sys.exit(1)

    if not episode_title:
        episode_title = "Untitled"

    # ── 显示规划 ──────────────────────────────────────────────
    file_size = f" ({audio_path.stat().st_size / 1024 / 1024:.1f} MB)" if audio_path.exists() else ""
    print(f"\n🎙️  播客处理工作流（本地 Qwen3:8b）")
    print(f"   {'='*45}")
    print(f"   节目:   {args.show}")
    print(f"   期数:   {episode_title}")
    print(f"   文件:   {audio_path.name}{file_size}")
    print(f"   语言:   {args.lang}")
    print(f"   日期:   {episode_date}")
    print(f"   模型:   whisper {args.model} → Ollama {OLLAMA_MODEL}")
    print(f"   {'='*45}\n")

    if args.dry_run:
        print("🔍 仅规划模式，未执行任何操作。")
        return

    # ── 1. 转码 ──────────────────────────────────────────────
    with tempfile.TemporaryDirectory(prefix="podcast_") as tmp_dir_name:
        tmp_p = Path(tmp_dir_name)

        if audio_path.suffix.lower() == ".wav":
            wav_path = audio_path
        else:
            wav_path = tmp_p / "audio.wav"
            run_ffmpeg(audio_path, wav_path)

        # ── 2. 转录 ──────────────────────────────────────────
        raw_text, segments = transcribe(wav_path, args.lang, args.model)

        if not raw_text.strip():
            print("❌ 转录结果为空")
            sys.exit(1)

        print(f"\n📝 原始转录: {len(raw_text)} 字符, {len(segments)} 段")

        # 保存原始转录
        raw_storage = BASE_DIR / "podcast-site" / "transcripts_raw"
        raw_storage.mkdir(parents=True, exist_ok=True)
        raw_slug = slugify(f"{episode_date}-{args.show}-{episode_title}")
        raw_path = raw_storage / f"{raw_slug}.txt"
        raw_path.write_text(raw_text, encoding="utf-8")
        raw_path_debug = tmp_p / "raw_transcript.txt"
        raw_path_debug.write_text(raw_text, encoding="utf-8")
        log(f"💾 原始转录已保存: {raw_path}")

        # ── 3. Qwen3 校对整理 ──────────────────────────────
        print(f"\n🤖 调用本地 Qwen3 ({OLLAMA_MODEL}) 校对整理...")

        # 显示前200字预览
        preview = raw_text[:200].replace('\n', ' ')
        print(f"   原文预览: {preview}...")

        processed = process_text_with_qwen(raw_text, args.show, episode_title)
        print(f"  ✅ 整理完成")
        print(f"    标题: {processed['title']}")
        print(f"    摘要: {processed['summary'][:100]}...")

        # ── 4. 生成博客文章（原文 + 整理版） ─────────────
        draft_path = generate_article(
            processed, args.show, episode_title,
            episode_date, args.category, tags_list,
            args.link, raw_text,
        )

        # ── 5. 同步到播客站 ─────────────────────────────
        if args.show_slug:
            from podcast_site_utils import save_to_podcast_site
            save_to_podcast_site(draft_path, args.show_slug, episode_date)

        # ── 6. 构建博客 ─────────────────────────────────
        if args.build:
            print(f"\n🔨 运行 publish.py build...")
            result = subprocess.run(
                [sys.executable, str(BASE_DIR / "publish.py"), "build"],
                cwd=str(BASE_DIR), capture_output=True, text=True,
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"⚠️  build 有错误:\n{result.stderr}")
            else:
                print(f"  ✅ 博客构建完成")

    print(f"\n✅ 全部完成！")
    print(f"   文章: {draft_path}")
    print(f"   发布: cd {BASE_DIR} && python publish.py build && git add -A && git commit -m \"...\" && git push")
    print()


if __name__ == "__main__":
    main()
