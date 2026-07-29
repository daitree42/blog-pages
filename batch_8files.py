#!/usr/bin/env python3
"""
batch_8files.py — 4线程并行处理 This American Life 播客音频
流程: 转录 → DeepSeek 翻译整理 → 生成文章 → 同步博客+播客站
"""
import glob, json, os, re, subprocess, sys, tempfile, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
PODCAST_DIR = BASE_DIR / "podcast"

sys.path.insert(0, str(BASE_DIR))
from process import load_env_file, slugify, check_deps, check_env
from podcast_site_utils import save_to_podcast_site

# ── 日志 ──────────────────────────────────────────────────
LOG_FILE = BASE_DIR / "batch_8files.log"
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ── 文件列表 ──────────────────────────────────────────────
PATTERNS = [
    ("*884*Idiot*",      "This American Life", "884: The Idiot",              "https://www.thisamericanlife.org/884/transcript"),
    ("*885*Mess*",       "This American Life", "885: Bless This Mess",        "https://www.thisamericanlife.org/885/transcript"),
    ("*886*Blackout*",   "This American Life", "886: Blackout",               "https://www.thisamericanlife.org/886/transcript"),
    ("*887*One*None*",   "This American Life", "887: Two Is One, One Is None", "https://www.thisamericanlife.org/887/transcript"),
    ("*888*Hades*",      "This American Life", "888: Not Today, Hades",       "https://www.thisamericanlife.org/888/transcript"),
    ("*889*Hail*Mary*",  "This American Life", "889: There’s Something About Hail Mary", "https://www.thisamericanlife.org/889/transcript"),
    ("*890*American*",   "This American Life", "890: Maximal Americanness",   "https://www.thisamericanlife.org/890/transcript"),
    ("*Lore*Drop*",      "This American Life", "878: New Lore Drop",          "https://www.thisamericanlife.org/878/transcript"),
]

def resolve_files():
    files = []
    for pattern, show, ep, link in PATTERNS:
        matches = list(PODCAST_DIR.glob(pattern))
        if matches:
            files.append((str(matches[0].name), show, ep, link))
        else:
            log(f"⚠️  未匹配到: {pattern}")
    return files

FILES = resolve_files()

SHOW_SLUG = "this-american-life"
CATEGORY = "播客笔记"
TAGS_LIST = ["播客", "This American Life", "TAL"]
EPISODE_DATE = datetime.now().strftime("%Y-%m-%d")
MAX_WORKERS = 3  # 3线程更稳定
LOCK = threading.Lock()

def _find_cached_model(model_size="tiny"):
    """在本地 HuggingFace 缓存中查找 faster-whisper 模型路径"""
    cache_dirs = [
        Path(os.environ.get("WHISPER_MODEL_DIR", "")),
        Path.home() / ".cache" / "huggingface" / "hub",
        Path(os.environ.get("HF_HOME", "")) / "hub",
    ]
    repo = f"models--Systran--faster-whisper-{model_size}"
    for cd in cache_dirs:
        if not cd or not cd.exists():
            continue
        snapshots = cd / repo / "snapshots"
        if not snapshots.exists():
            continue
        for sp in sorted(snapshots.iterdir()):
            if (sp / "model.bin").exists():
                return str(sp)
    return None

def process_one(audio_filename, show_name, episode_title, episode_link):
    audio_path = PODCAST_DIR / audio_filename
    if not audio_path.exists():
        return f"❌ 文件不存在: {audio_filename}"

    file_size = audio_path.stat().st_size / 1024 / 1024
    log(f"▶ [{episode_title}] 开始 ({file_size:.0f} MB)...")

    with tempfile.TemporaryDirectory(prefix="podcast_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        wav_path = tmp_path / "audio.wav"

        # 1. 转码
        log(f"  [{episode_title}] 🎵 ffmpeg 转码中...")
        cmd = ["ffmpeg", "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", str(wav_path)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            log(f"  [{episode_title}] ❌ ffmpeg 失败: {r.stderr[:200]}")
            return f"❌ [{episode_title}] ffmpeg 失败"

        # 2. faster-whisper 转录
        local_model = _find_cached_model("tiny")
        model_path = local_model or "tiny"
        log(f"  [{episode_title}] 🎙️ 转录中（约10-30分钟）...")
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(model_path, device="cpu", compute_type="float32")
            segments_raw, info = model.transcribe(str(wav_path), language="en",
                beam_size=5, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
            segments = []
            text_parts = []
            for seg in segments_raw:
                segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
                text_parts.append(seg.text.strip())
            raw_text = " ".join(text_parts)
            duration = info.duration if info.duration else 0
            log(f"  [{episode_title}] ✅ 转录完成: {len(raw_text)} 字符, {len(segments)} 段, {duration:.0f}s 音频")
        except Exception as e:
            log(f"  [{episode_title}] ❌ 转录失败: {e}")
            return f"❌ [{episode_title}] 转录失败: {e}"

        if not raw_text.strip():
            return f"❌ [{episode_title}] 转录为空"

        # 3. DeepSeek 翻译 + 整理
        log(f"  [{episode_title}] 🤖 DeepSeek 翻译整理中...")
        try:
            from process import _call_llm, build_llm_prompt, parse_llm_response
            sp, up = build_llm_prompt(raw_text, segments, show_name, episode_title, "en", episode_link)
            resp = _call_llm(sp, up)
            processed = parse_llm_response(resp, show_name, episode_title)
        except Exception as e:
            log(f"  [{episode_title}] ❌ DeepSeek 失败: {e}")
            return f"❌ [{episode_title}] DeepSeek 失败: {e}"
        log(f"  [{episode_title}] ✅ 整理完成: {processed['title']}")

        # 4. 生成 blog 文章
        from process import generate_article
        draft_path = generate_article(processed, show_name, episode_title,
            EPISODE_DATE, CATEGORY, TAGS_LIST, episode_link, "en")
        log(f"  [{episode_title}] ✅ 文章: {draft_path.parent.name}/draft.md")

        # 5. 同步到 podcast-site/transcripts
        save_to_podcast_site(draft_path, SHOW_SLUG, EPISODE_DATE)

    return f"✅ [{episode_title}] 全部完成"

def main():
    # 清旧日志
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    load_env_file()
    missing = check_deps()
    if missing:
        log(f"❌ 缺少依赖: {missing}")
        sys.exit(1)
    err = check_env()
    if err:
        log(f"❌ {err}")
        sys.exit(1)

    log(f"\n📦 处理 {len(FILES)} 个音频 (并发 {MAX_WORKERS})")
    log(f"   节目: This American Life")
    log(f"   日期: {EPISODE_DATE}")
    log(f"   LLM:  {os.environ.get('LLM_PROVIDER', 'deepseek')}")
    log(f"{'='*55}")

    start = time.time()
    success, fail = 0, 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_one, f, show, ep, link): ep
            for f, show, ep, link in FILES
        }
        for future in as_completed(futures):
            ep = futures[future]
            try:
                result = future.result()
                log(result)
                if result.startswith("✅"):
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                log(f"❌ [{ep}] 异常: {e}")
                import traceback
                traceback.print_exc()
                fail += 1

    elapsed = time.time() - start
    log(f"\n{'='*55}")
    log(f"📊 结果: ✅ {success} / ❌ {fail} / 耗时 {elapsed/60:.1f} 分钟")

    if fail > 0:
        log(f"⚠️  有 {fail} 个失败，请检查日志")

    # 6. 构建播客独立站
    log(f"🔨 构建播客独立站...")
    subprocess.run([sys.executable, str(BASE_DIR / "podcast-site" / "build.py")],
                   capture_output=True, text=True)

    # 7. 构建博客
    log(f"🔨 构建博客...")
    r = subprocess.run([sys.executable, str(BASE_DIR / "publish.py"), "build"],
                       capture_output=True, text=True)
    log(f"  博客构建完成")

    log(f"\n{'='*55}")
    log(f"✅ 全部完成！")
    log(f"   发布: cd {BASE_DIR}")
    log(f"   git add -A && git commit -m \"deploy: This American Life 8集批量\"")
    log(f"   git push origin main")

if __name__ == "__main__":
    main()
