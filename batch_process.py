#!/usr/bin/env python3
"""
batch_process.py — 批量处理 podcast/ 下的音频文件（并行版）
流程: 转录 → DeepSeek 翻译中文(保守处理) → 生成博客文章 → 构建
"""

import argparse, glob, json, os, re, subprocess, sys, tempfile, urllib.request, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
PODCAST_DIR = BASE_DIR / "podcast"
TRANSCRIPTS_RAW_DIR = BASE_DIR / "podcast-site" / "transcripts_raw"
ARTICLES_DIR = BASE_DIR / "articles"

CATEGORY = "播客"
TAGS = "播客,The Daily,NYT"
LINK = "https://www.nytimes.com/the-daily"
EPISODE_DATE = datetime.now().strftime("%Y-%m-%d")

FILES = [
    ("can a bad man be a good father.mp3", "The Daily", "Can a Bad Man Be a Good Father"),
    ("Cuba Under Siege.mp3", "The Daily", "Cuba Under Siege"),
    ("The Mother Who Changed A Story of Dementia.mp3", "The Daily", "The Mother Who Changed a Story of Dementia"),
    ("what do you do when a family member commits a terrible crime.mp3", "The Daily", "What Do You Do When a Family Member Commits a Terrible Crime"),
    ("Why Do Some Memories Survive Dementia.mp3", "The Daily", "Why Do Some Memories Survive Dementia"),
]

MAX_WORKERS = 3  # 并行数

def log(msg):
    print(f"  {msg}")


def slugify(text):
    slug = re.sub(r'[^\w\- ]', '', text.strip())
    return slug.strip().replace(' ', '_') or "untitled"


def process_one_file(filename, show_name, episode_title):
    """处理单个文件：转码→转录→翻译→生成文章"""
    audio_path = PODCAST_DIR / filename
    if not audio_path.exists():
        return f"⚠️  文件不存在: {filename}"

    file_size = audio_path.stat().st_size / 1024 / 1024
    result_lines = []
    result_lines.append(f"\n[{episode_title}] ({file_size:.0f} MB)")

    with tempfile.TemporaryDirectory(prefix="podcast_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        wav_path = tmp_path / "audio.wav"

        # 1. 转码
        if audio_path.suffix.lower() != ".wav":
            cmd = ["ffmpeg", "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", str(wav_path)]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        else:
            wav_path = audio_path

        # 2. 转录
        raw_text, segments = _transcribe(wav_path)
        if not raw_text.strip():
            return f"❌ 转录为空: {filename}"

        # 保存原始转录
        TRANSCRIPTS_RAW_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = TRANSCRIPTS_RAW_DIR / f"{EPISODE_DATE}-{slugify(show_name)}-{slugify(episode_title)}.txt"
        raw_path.write_text(raw_text, encoding="utf-8")

        # 3. 翻译
        processed = _translate(raw_text, show_name, episode_title)

        # 保存中文版
        zh_path = TRANSCRIPTS_RAW_DIR / f"{EPISODE_DATE}-{slugify(show_name)}-{slugify(episode_title)}.zh.txt"
        zh_path.write_text(processed, encoding="utf-8")

        # 4. 生成博客文章
        draft_path = _generate_article(processed, raw_text, show_name, episode_title)

        # 5. 同步播客站
        try:
            from podcast_site_utils import save_to_podcast_site
            show_slug = slugify(show_name).lower()
            save_to_podcast_site(draft_path, show_slug, EPISODE_DATE)
        except Exception:
            pass

    result_lines.append(f"  ✅ 完成 ({len(raw_text)} 字符 → {len(processed)} 字符)")
    return "\n".join(result_lines)


def _transcribe(audio_path):
    """Whisper tiny 转录"""
    from faster_whisper import WhisperModel
    model_path = None
    cache_dirs = [
        Path(os.environ.get("WHISPER_MODEL_DIR", "")),
        Path.home() / ".cache" / "huggingface" / "hub",
    ]
    repo = "models--Systran--faster-whisper-tiny"
    for cd in cache_dirs:
        if not cd or not cd.exists():
            continue
        snapshots = cd / repo / "snapshots"
        if snapshots.exists():
            for sp in sorted(snapshots.iterdir()):
                if (sp / "model.bin").exists():
                    model_path = str(sp)
                    break

    model = WhisperModel(model_path or "tiny", device="cpu", compute_type="float32")
    segments, info = model.transcribe(str(audio_path), language="en",
                                        beam_size=5, vad_filter=True,
                                        vad_parameters=dict(min_silence_duration_ms=500))
    text_parts = [seg.text.strip() for seg in segments]
    return " ".join(text_parts), []


def _translate(raw_text, show_name, episode_title):
    """DeepSeek 翻译"""
    from openai import OpenAI
    import httpx, warnings
    warnings.filterwarnings("ignore", message=".*SSL.*")

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        # 从 .env 加载
        dotenv_path = BASE_DIR / ".env"
        if dotenv_path.exists():
            for line in open(dotenv_path, encoding="utf-8"):
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return raw_text

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com",
                    http_client=httpx.Client(verify=False))

    system = (
        "你是一个翻译助手。将英文播客转录文本逐句翻译为中文。\n"
        "要求：\n"
        "1. 逐句翻译，不遗漏任何内容\n"
        "2. 修改原文中的错别字和语法错误\n"
        "3. 合理分段：按语义划分段落，每个段落3-5句为宜，段落之间用空行分隔\n"
        "4. 调整语句顺序让中文通顺自然，但不要改变原意\n"
        "5. 不要润色、不要增删内容、不要添加原文没有的信息\n"
        "6. 保留专有名词和人名原文（可在括号中附中文翻译）\n"
        "7. 原文段落和中文翻译段落交替排列\n"
        "8. 保持原始的时间顺序和段落结构\n"
        "9. 对话部分保留引号或换行区分发言人，使文本易于阅读"
    )

    MAX_CHARS = 50000
    if len(raw_text) <= MAX_CHARS:
        prompt = f"播客: {show_name} - {episode_title}\n\n逐句翻译以下英文转录文本为中文。原文段落和中文翻译段落交替排列。\n\n{raw_text}"
        resp = client.chat.completions.create(
            model="deepseek-v4-flash", max_tokens=16000,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    chunks = [raw_text[i:i+MAX_CHARS] for i in range(0, len(raw_text), MAX_CHARS)]
    results = []
    for i, chunk in enumerate(chunks, 1):
        prompt = f"播客: {show_name} - {episode_title}\n这是第 {i}/{len(chunks)} 部分。\n\n逐句翻译以下英文转录文本为中文。\n\n{chunk}"
        resp = client.chat.completions.create(
            model="deepseek-v4-flash", max_tokens=16000,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        results.append(resp.choices[0].message.content.strip())
    return "\n\n".join(results)


def _generate_article(processed_text, raw_text, show_name, episode_title):
    """生成博客文章"""
    short_show = slugify(show_name)[:20].rstrip('-_')
    short_title = slugify(episode_title)[:25].rstrip('-_')
    slug = f"{EPISODE_DATE}-{short_show}-{short_title}"
    article_dir = ARTICLES_DIR / slug
    article_dir.mkdir(parents=True, exist_ok=True)
    draft_path = article_dir / "draft.md"

    en_words = len(raw_text.split())
    reading_time = max(1, round(en_words / 200))
    tags_str = "，".join([t.strip() for t in TAGS.replace("，", ",").split(",") if t.strip()])

    content = f"# {episode_title}\n\n"
    content += f"> 栏目：{CATEGORY}\n"
    content += f"> 日期：{EPISODE_DATE}\n"
    content += f"> 阅读时间：{reading_time} 分钟\n"
    content += f"> 标签：{tags_str}\n"
    content += f"> 摘要：{show_name} · {episode_title} 英文播客中文翻译\n"
    content += f'\n<div class="post-body">\n'
    content += processed_text
    content += f"\n\n---\n\n"
    content += f"**Source:** {show_name} · {episode_title} · [Original Link]({LINK})\n"
    content += f"**Processing Date:** {EPISODE_DATE}\n"
    content += f"\n## 📝 英文原文\n\n<details>\n<summary>点击展开英文原文</summary>\n\n"
    content += raw_text
    content += "\n\n</details>\n</div>\n"

    draft_path.write_text(content, encoding="utf-8")
    return draft_path


def main():
    print(f"\n📦 批量并行处理 {len(FILES)} 个音频文件 (并发 {MAX_WORKERS})")
    print(f"{'='*50}")

    start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_one_file, filename, show, episode): episode
            for filename, show, episode in FILES
        }
        for future in as_completed(futures):
            ep = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(result)
            except Exception as e:
                results.append(f"  ❌ {ep} 失败: {e}")
                print(f"  ❌ {ep} 失败: {e}")

    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"✅ 处理完成！耗时 {elapsed/60:.1f} 分钟")

    # 构建博客
    print(f"\n🔨 构建博客...")
    result = subprocess.run(
        [sys.executable, str(BASE_DIR / "publish.py"), "build"],
        cwd=str(BASE_DIR), capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print(f"⚠️  {result.stderr}")

    print(f"\n✅ 全部完成！")
    print(f"   发布: cd {BASE_DIR} && git add -A && git commit -m \"deploy: 批量播客\" && git push")


if __name__ == "__main__":
    main()
