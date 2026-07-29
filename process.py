#!/usr/bin/env python3
"""
process.py — 播客音频 → 博客文章 本地工作流

用法:
    python process.py audio.mp3 --show "播客名" --episode "第X期" [选项]

流程:
    1. 本地 faster-whisper 语音转文字
    2. LLM（Claude/DeepSeek）翻译（非中文）+ 整理 + 分段 + 摘要
    3. 生成 blog-pages 兼容的 articles/{slug}/draft.md
    4. 可选：自动运行 publish.py build

依赖安装:
    pip install -r requirements.txt
    pip install faster-whisper anthropic

环境变量:
    ANTHROPIC_API_KEY     Claude API 密钥（必填）
    WHISPER_MODEL_DIR     whisper 模型缓存目录（可选，默认 ~/.cache/whisper）

示例:
    python process.py 今日话题.mp3 --show "随机波动" --episode "第100期" --lang zh
    python process.py interview.mp3 --show "The Daily" --episode "2026-07-25" --lang en
    python process.py audio.m4a --show "故事FM" --episode "E800" --tags "真实故事,口述" --build
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# Windows 终端兼容：避免 emoji 编码错误
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # py3.7+

# ── 配置 ──────────────────────────────────────────────────────────

# blog-pages 路径（脚本放在 blog-pages 目录下）
BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"

# 播客独立站点路径
PODCAST_SITE_DIR = BASE_DIR / "podcast-site"
TRANSCRIPTS_DIR = PODCAST_SITE_DIR / "transcripts"

# 默认 whisper 模型大小
DEFAULT_WHISPER_MODEL = "tiny"

# 支持的模型（按速度/质量排序）
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# LLM 提供商配置
LLM_PROVIDERS = {
    "claude": {
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-5-20251001",
        "package": "anthropic",
    },
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-v4-flash",
        "package": "openai",
        "base_url": "https://api.deepseek.com",
    },
}


# ── 工具函数 ──────────────────────────────────────────────────────

def check_deps() -> list[str]:
    """检查必需的外部工具是否存在，返回缺失列表"""
    missing = []

    # ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing.append("ffmpeg")

    # faster-whisper
    try:
        import faster_whisper  # noqa
    except ImportError:
        missing.append("faster-whisper")

    # LLM 包（按提供商）
    provider = get_llm_provider()
    if provider == "claude":
        try:
            import anthropic  # noqa
        except ImportError:
            missing.append("anthropic")
    elif provider == "deepseek":
        try:
            import openai  # noqa
        except ImportError:
            missing.append("openai")

    return missing


def get_llm_provider() -> str:
    """获取用户选择的 LLM 提供商（deepseek / claude），默认 claude"""
    provider = os.environ.get("LLM_PROVIDER", "claude").lower().strip()
    return provider if provider in LLM_PROVIDERS else "claude"


def load_env_file():
    """从 .env 文件加载环境变量"""
    dotenv_path = BASE_DIR / ".env"
    if not dotenv_path.exists():
        return
    with open(dotenv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value and key not in os.environ:
                    os.environ[key] = value


def check_env() -> Optional[str]:
    """检查环境变量，返回错误信息或 None"""
    load_env_file()

    provider = get_llm_provider()
    cfg = LLM_PROVIDERS[provider]
    env_key = cfg["env_key"]

    if not os.environ.get(env_key):
        return (
            f"缺少 {env_key}（当前提供商: {provider}）\n"
            f"  方式一：set {env_key}=sk-xxx  （Windows）\n"
            f"  方式二：在 blog-pages/.env 文件中写入 {env_key}=sk-xxx\n"
            f"  切换提供商：set LLM_PROVIDER=deepseek 或 set LLM_PROVIDER=claude"
        )
    return None


def slugify(text: str) -> str:
    """标题 → 文件路径安全的 slug"""
    slug = text.strip()
    # 只保留中文、字母、数字、连字符、下划线
    slug = re.sub(r'[^一-鿿\w\- ]', '', slug)
    slug = slug.strip().replace(' ', '_')
    return slug or "untitled"


def format_timestamp(seconds: float) -> str:
    """秒数 → MM:SS 或 HH:MM:SS"""
    seconds = int(seconds)
    h, m = divmod(seconds, 3600)
    m, s = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def run_ffmpeg(input_path: Path, output_path: Path) -> None:
    """转码为 16kHz 单声道 WAV"""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-ar", "16000",
        "-ac", "1",
        "-sample_fmt", "s16",
        str(output_path),
    ]
    print(f"  🎵 转码中...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 转码失败:\n{result.stderr}"
        )
    print(f"  ✅ 转码完成: {output_path.name}")


# ── 转录 ──────────────────────────────────────────────────────────

def transcribe(
    audio_path: Path,
    language: str,
    model_size: str = DEFAULT_WHISPER_MODEL,
) -> tuple[str, list[dict]]:
    """
    使用 faster-whisper 转录音频。

    返回:
        full_text: 完整文本（不含时间戳，用于 LLM）
        segments: [{start, end, text}, ...]（含时间戳）
    """
    from faster_whisper import WhisperModel

    # 先找本地缓存（避免 HuggingFace SSL 问题）
    local_model = _find_cached_whisper_model(model_size)
    if local_model:
        model_path = local_model
        print(f"  使用本地缓存模型: {local_model}")
    else:
        model_path = model_size
        print(f"  从 HuggingFace 下载模型（首次需要网络）...")

    # 支持 GPU（cuBLAS）和 CPU 自动切换
    try:
        model = WhisperModel(
            model_path,
            device="auto",
            compute_type="float16",
            download_root=os.environ.get("WHISPER_MODEL_DIR"),
        )
    except Exception:
        model = WhisperModel(
            model_path,
            device="cpu",
            compute_type="float32",
            download_root=os.environ.get("WHISPER_MODEL_DIR"),
        )

    print(f"  🎙️  转录中（模型: {model_size}，语言: {language}，这步最慢）...")
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
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
        text_parts.append(seg.text.strip())

    full_text = " ".join(text_parts)
    duration = info.duration if info.duration else 0

    print(f"  ✅ 转录完成: {len(segments)} 段, 约 {duration:.0f}s 音频")
    return full_text, segments


def _find_cached_whisper_model(model_size: str) -> str | None:
    """在本地 HuggingFace 缓存中查找 faster-whisper 模型路径"""
    cache_dirs = [
        Path(os.environ.get("WHISPER_MODEL_DIR", "")),
        Path.home() / ".cache" / "huggingface" / "hub",
        Path(os.environ.get("HF_HOME", "")) / "hub",
    ]

    repo_dir_name = f"models--Systran--faster-whisper-{model_size}"

    for cache_dir in cache_dirs:
        if not cache_dir or not cache_dir.exists():
            continue
        snapshots_dir = cache_dir / repo_dir_name / "snapshots"
        if not snapshots_dir.exists():
            continue
        # 找到包含 model.bin 的 snapshot 目录
        for snapshot_path in sorted(snapshots_dir.iterdir()):
            if (snapshot_path / "model.bin").exists():
                return str(snapshot_path)

    return None


# ── LLM 处理（支持 Claude / DeepSeek） ──────────────────────────────


def build_llm_prompt(
    raw_text: str,
    segments: list[dict],
    show_name: str,
    episode_title: str,
    source_lang: str,
    episode_link: str = "",
) -> tuple[str, str]:
    """构建 LLM 提示词，返回 (system_prompt, user_prompt)"""
    # 构造时间戳参考
    ts_lines = []
    for seg in segments[:5]:
        ts_lines.append(f"[{format_timestamp(seg['start'])}] {seg['text'][:80]}...")
    ts_example = "\n".join(ts_lines)

    needs_translation = source_lang != "zh"

    system_prompt = (
        "你是一个专业的播客内容整理助手。你需要将播客转录文本整理为清晰、可读的中文文章。"
        "保留原意的同时去除口语化表达，按主题自动分段并添加小标题。"
    )

    user_prompt = f"""请处理以下播客转录文本，输出 JSON。

## 播客信息
- 节目名称：{show_name}
- 期数：{episode_title}
- 源语言：{source_lang}
{"- 原始链接：" + episode_link if episode_link else ""}

## 处理要求
{"1. 将英文翻译为中文（保留专有名词和术语的原文，必要时加括号标注）" if needs_translation else "1. 中文内容，保持原文语言"}
2. 去除口语填充词（"嗯"、"啊"、"然后"、"那个"等），合并意思连贯的句子为自然段落
3. 按话题自动分段，每段加 ## 小标题
4. 每段保留 1-2 个关键时间戳（格式 [MM:SS]），位置放在小标题下一行
5. 生成一段 200 字以内的摘要
6. 末尾附来源信息：播客名、期数、原始链接（如有）、处理日期

## 时间戳参考格式
{ts_example}

## 输出格式（纯 JSON，不要 markdown 代码块包裹）
{{"title": "整理后的文章标题（20字以内，吸引人）",
 "summary": "200字以内的摘要",
 "body_md": "完整文章内容，Markdown 格式",
 "segments_count": "源转录段落数量",
 "source_lang": "检测到的语言"}}

## 转录文本
{raw_text}
"""
    return system_prompt, user_prompt


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """调用当前配置的 LLM，返回响应文本"""
    provider = get_llm_provider()
    cfg = LLM_PROVIDERS[provider]
    model = cfg["default_model"]
    api_key = os.environ[cfg["env_key"]]

    print(f"  🤖 调用 {provider} ({model}) 整理文稿...")

    if provider == "claude":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text.strip()

    elif provider == "deepseek":
        from openai import OpenAI

        # Windows SSL 兼容：用不验证证书的 httpx 客户端
        import httpx
        http_client = httpx.Client(verify=False)
        client = OpenAI(
            api_key=api_key,
            base_url=cfg["base_url"],
            http_client=http_client,
        )
        # 抑制 urllib3 的 SSL 警告
        import warnings
        warnings.filterwarnings("ignore", message=".*SSL.*")

        response = client.chat.completions.create(
            model=model,
            max_tokens=16000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def parse_llm_response(text: str, show_name: str, episode_title: str) -> dict:
    """解析 LLM 返回的 JSON"""
    # 去掉可能的 markdown 代码块包裹
    text = re.sub(r'^```(?:json)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(0))
            except json.JSONDecodeError:
                result = _fallback_result(text, show_name)
        else:
            result = _fallback_result(text, show_name)

    result.setdefault("title", f"{show_name} {episode_title}")
    result.setdefault("summary", "")
    result.setdefault("body_md", text)
    result.setdefault("source_lang", "zh")
    return result


def process_with_llm(
    raw_text: str,
    segments: list[dict],
    show_name: str,
    episode_title: str,
    source_lang: str,
    episode_link: str = "",
) -> dict:
    """
    调用 LLM（Claude 或 DeepSeek）处理转录文本：
    1. 非中文 → 翻译为中文
    2. 去除口语填充词，合并自然段落
    3. 按话题自动分小标题
    4. 生成摘要
    5. 保留关键时间戳
    """
    system_prompt, user_prompt = build_llm_prompt(
        raw_text, segments, show_name, episode_title,
        source_lang, episode_link,
    )

    # 单次调用上限（60K 字符）
    max_chars = 60000
    if len(raw_text) <= max_chars:
        text = _call_llm(system_prompt, user_prompt)
        return parse_llm_response(text, show_name, episode_title)

    # 长文本分批处理
    print(f"  📄 文本较长 ({len(raw_text)} 字符)，分段处理...")
    chunks = [raw_text[i:i+max_chars] for i in range(0, len(raw_text), max_chars)]

    # 第一块
    text = _call_llm(system_prompt,
        f"这是第 1/{len(chunks)} 部分\n\n" + user_prompt.replace(raw_text, chunks[0]))
    result = parse_llm_response(text, show_name, episode_title)

    # 后续块增量追加
    for i, chunk in enumerate(chunks[1:], 2):
        chunk_text = _call_llm(system_prompt,
            f"这是第 {i}/{len(chunks)} 部分（追加到已有文章后面）\n\n"
            f"## 播客信息\n节目名称：{show_name}\n期数：{episode_title}\n\n"
            f"## 处理要求\n将以下新文本自然地追加到前面已整理的部分后面。"
            f"保持语言风格一致，继续使用 ## 小标题分段。\n\n"
            f"## 新文本\n{chunk}")
        chunk_result = parse_llm_response(chunk_text, show_name, episode_title)
        result["body_md"] += "\n\n" + chunk_result["body_md"]

    return result


def _fallback_result(text: str, show_name: str) -> dict:
    """当 LLM 返回非 JSON 时的兜底方案"""
    return {
        "title": show_name,
        "summary": "自动转录整理",
        "body_md": text,
        "source_lang": "unknown",
    }


# ── 播客站点输出 ─────────────────────────────────────────────────


def save_to_podcast_site(
    draft_path: Path,
    show_slug: str,
    episode_date: str,
) -> Path | None:
    """
    将生成的文章也保存到 podcast-site/transcripts/ 目录。

    复制 articles/{slug}/draft.md → podcast-site/transcripts/{show_slug}/{date}-{slug}.md
    """
    if not draft_path or not draft_path.exists():
        return None
    if not show_slug:
        return None

    slug = draft_path.parent.name
    target_dir = TRANSCRIPTS_DIR / show_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    # 截取 slug 后半段的标题部分（前面已经是日期前缀了）
    title_part = slug[len(episode_date)+1:] if slug.startswith(episode_date) else slug
    short_part = title_part[:35].rstrip('-_')
    target_name = f"{episode_date}-{short_part}.md"
    target_path = target_dir / target_name

    try:
        import shutil
        shutil.copy2(draft_path, target_path)
        print(f"  ✅ 已同步到播客站: {target_path}")
    except Exception as e:
        print(f"  ⚠  同步到播客站失败: {e}")
        return None

    return target_path


# ── 生成博客文章 ──────────────────────────────────────────────────

def generate_article(
    processed: dict,
    show_name: str,
    episode_title: str,
    episode_date: str,
    category: str,
    tags: list[str],
    episode_link: str,
    source_lang: str,
) -> Path:
    """
    生成 articles/{slug}/draft.md

    返回 draft.md 的路径
    """
    title = processed.get("title", f"{show_name} {episode_title}")
    summary = processed.get("summary", "")
    body_md = processed.get("body_md", "")

    # 正文附加来源信息（如果 Claude 没加）
    source_note = (
        f"\n\n---\n\n"
        f"**来源：** {show_name} · {episode_title}"
        f"{' · [原始链接](' + episode_link + ')' if episode_link else ''}\n"
        f"**处理日期：** {episode_date}\n"
        f"**原始语言：** {source_lang}"
    )

    # 检查正文末尾是否已有来源信息
    if "**来源：**" not in body_md:
        body_md += source_note

    # 将 Markdown 正文转换为 HTML（如果没有被 HTML 标签包裹）
    import markdown as md_lib
    if not re.search(r'<(p|h[1-6]|div|ul|ol|table|hr)[\s>]', body_md[:500]):
        body_md = md_lib.markdown(body_md, extensions=['fenced_code', 'tables', 'codehilite'])

    # 计算阅读时间
    zh_chars = len(re.findall(r'[一-鿿]', body_md))
    reading_time = max(1, round(zh_chars / 500))

    # 生成短 slug
    short_show = slugify(show_name)[:20].rstrip('-_')
    short_title = slugify(episode_title)[:25].rstrip('-_')
    slug = f"{episode_date}-{short_show}-{short_title}"

    # 目录
    article_dir = ARTICLES_DIR / slug
    article_dir.mkdir(parents=True, exist_ok=True)
    draft_path = article_dir / "draft.md"

    tags_str = "，".join(tags) if tags else ""

    content = f"# {title}\n\n"
    content += f"> 栏目：{category}\n"
    content += f"> 日期：{episode_date}\n"
    content += f"> 阅读时间：{reading_time}\n"
    content += f"> 标签：{tags_str}\n" if tags_str else ""
    content += f"> 摘要：{summary}\n"
    content += f"\n"
    content += f'<div class="post-body">\n'
    content += body_md
    content += f'\n</div>\n'

    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  ✅ 文章已生成: {draft_path}")
    return draft_path


# ── 主流程 ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="播客音频 → 博客文章 本地工作流",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python process.py 今日话题.mp3 --show \"随机波动\" --episode \"第100期\"\n"
            "  python process.py talk.mp3 --show \"The Daily\" --episode \"2026-07-25\" --lang en\n"
            "  python process.py audio.m4a --show \"故事FM\" --episode \"E800\" --build\n"
            "\n环境变量:\n"
            "  ANTHROPIC_API_KEY   Claude API 密钥（claude 提供商）\n"
            "  DEEPSEEK_API_KEY    DeepSeek API 密钥（deepseek 提供商）\n"
            "  LLM_PROVIDER        选择提供商: claude（默认）或 deepseek\n"
        ),
    )
    parser.add_argument("audio", help="音频文件路径 (.mp3/.m4a/.wav/...)")
    parser.add_argument("--show", required=True, help="播客节目名称")
    parser.add_argument("--episode", required=True, help="期数/标题")
    parser.add_argument("--lang", default="auto",
                        help="音频语言代码 (zh/en/ja/auto，默认 auto 自动检测)")
    parser.add_argument("--date", default="",
                        help="发布日期 (默认今天)")
    parser.add_argument("--category", default="未分类",
                        help="博客分类 (默认 未分类)")
    parser.add_argument("--tags", default="",
                        help='标签，逗号分隔，如 "播客,科技,访谈"')
    parser.add_argument("--link", default="",
                        help="原始链接（小宇宙/YouTube 等）")
    parser.add_argument("--show-slug", default="",
                        help="播客站节目 slug（指定后将同步到 podcast-site/）")
    parser.add_argument("--model", default=DEFAULT_WHISPER_MODEL,
                        choices=WHISPER_MODELS,
                        help=f"whisper 模型大小 (默认 {DEFAULT_WHISPER_MODEL})")
    parser.add_argument("--no-claude", action="store_true",
                        help="跳过 LLM 整理，仅保存原始转录文本")
    parser.add_argument("--build", action="store_true",
                        help="处理后自动运行 publish.py build")
    parser.add_argument("--dry-run", action="store_true",
                        help="只显示流程规划，不实际执行")

    args = parser.parse_args()

    # 先加载 .env（不依赖外部工具），确保提供商信息可用
    load_env_file()
    episode_date = args.date or datetime.now().strftime("%Y-%m-%d")
    tags_list = [t.strip() for t in args.tags.replace("，", ",").split(",") if t.strip()]
    provider = get_llm_provider()

    # 显示规划概览
    audio_path = Path(args.audio)
    file_size = f" ({audio_path.stat().st_size / 1024 / 1024:.1f} MB)" if audio_path.exists() else " (文件不存在)"
    print(f"\n🎙️  播客处理工作流")
    print(f"   {'='*40}")
    print(f"   节目:   {args.show}")
    print(f"   期数:   {args.episode}")
    print(f"   文件:   {audio_path.name}{file_size}")
    print(f"   语言:   {args.lang}")
    print(f"   日期:   {episode_date}")
    print(f"   模型:   {args.model}")
    if not args.no_claude:
        print(f"   LLM:   {provider}")
    else:
        print(f"   LLM:   跳过")
    print(f"   {'='*40}\n")

    if args.dry_run:
        print("🔍 仅规划模式，未执行任何操作。")
        return

    # ── 前置检查 ────────────────────────────────────────────────
    missing = check_deps()
    if missing:
        print("❌ 缺少依赖，请先安装:")
        for pkg in missing:
            print(f"   pip install {pkg}")
        print("   (ffmpeg 需单独安装: https://ffmpeg.org/download.html)")
        sys.exit(1)

    env_err = check_env()
    if env_err and not args.no_claude:
        print(f"❌ {env_err}")
        sys.exit(1)

    if not audio_path.exists():
        print(f"❌ 音频文件不存在: {audio_path}")
        sys.exit(1)

    tags = tags_list

    # ── 1. 转码 ──────────────────────────────────────────────
    # 如果不是 wav 格式，转码
    with tempfile.TemporaryDirectory(prefix="podcast_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        if audio_path.suffix.lower() == ".wav":
            wav_path = audio_path
            print(f"  ✅ 已是 WAV 格式，跳过转码")
        else:
            wav_path = tmp_path / "audio.wav"
            run_ffmpeg(audio_path, wav_path)

        # ── 2. 转录 ──────────────────────────────────────────
        raw_text, segments = transcribe(wav_path, args.lang, args.model)

        if not raw_text.strip():
            print("❌ 转录结果为空，无法继续")
            sys.exit(1)

        print(f"  📝 原始转录: {len(raw_text)} 字符, {len(segments)} 段")

        # 保存原始转录到 podcast-site/transcripts_raw/（方便调试和重试）
        raw_storage_dir = BASE_DIR / "podcast-site" / "transcripts_raw"
        raw_storage_dir.mkdir(parents=True, exist_ok=True)
        raw_slug = slugify(f"{episode_date}-{args.show}-{args.episode}")
        raw_storage_path = raw_storage_dir / f"{raw_slug}.txt"
        raw_storage_path.write_text(raw_text, encoding="utf-8")
        print(f"  💾 原始转录已保留: {raw_storage_path}")

        # 保存原始转录到临时目录（调试用）
        raw_path = tmp_path / "raw_transcript.txt"
        raw_path.write_text(raw_text, encoding="utf-8")

        # ── 3. LLM 整理 ────────────────────────────────────
        if args.no_claude:
            # 跳过 LLM，直接保存原始转录
            processed = {
                "title": f"{args.show} {args.episode}",
                "summary": "原始转录（未经整理）",
                "body_md": raw_text,
            }
            source_lang = args.lang if args.lang != "auto" else "zh"
            print(f"  ⏭  跳过 LLM，使用原始转录文本")
        else:
            source_lang = args.lang
            processed = process_with_llm(
                raw_text, segments,
                args.show, args.episode,
                source_lang,
                args.link,
            )
            source_lang = processed.get("source_lang", source_lang)
            print(f"  ✅ LLM 整理完成")
            print(f"    标题: {processed['title']}")
            print(f"    摘要: {processed['summary'][:80]}...")

        # ── 4. 生成博客文章 ─────────────────────────────────
        draft_path = generate_article(
            processed, args.show, args.episode,
            episode_date, args.category, tags,
            args.link, source_lang,
        )

        # ── 5. 同步到播客站（如果指定了 --show-slug） ──────
        if args.show_slug:
            save_to_podcast_site(draft_path, args.show_slug, episode_date)

        # ── 6. 可选构建 ─────────────────────────────────────
        if args.build:
            print(f"\n🔨 运行 publish.py build...")
            result = subprocess.run(
                [sys.executable, str(BASE_DIR / "publish.py"), "build"],
                cwd=str(BASE_DIR),
                capture_output=True, text=True,
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"⚠  build 有错误:\n{result.stderr}")
            else:
                print(f"  ✅ 博客构建完成")

    print(f"\n✅ 全部完成！")
    print(f"   文章: {draft_path}")
    print(f"   发布: cd {BASE_DIR} && python publish.py build && git add -A && git commit -m \"...\" && git push")
    print()


if __name__ == "__main__":
    main()
