#!/usr/bin/env python3
"""
podcast2blog.py — 播客转博客文章流水线

从播客分享链接自动下载音频 → 语音转文字 → LLM 整理 → 发布为博客文章。

用法:
    python podcast2blog.py <url>                          # 从链接完整处理
    python podcast2blog.py --audio <本地文件.mp3>          # 使用本地音频文件
    python podcast2blog.py --transcript <转录稿.txt>       # 直接用已有转录稿
    python podcast2blog.py build                           # 仅构建+部署
    python podcast2blog.py serve                           # 本地预览

LLM 后端（文本整理）:
    ANTHROPIC_API_KEY=sk-ant-...     → Claude（默认模型: claude-sonnet-4）
    OPENAI_API_KEY=sk-...            → OpenAI / Kimi / DeepSeek 等
    API_BASE_URL=https://.../v1      → OpenAI 兼容 API 地址
    API_MODEL=model-name             → 指定模型名

  Kimi 示例:
    export OPENAI_API_KEY=sk-...
    export API_BASE_URL=https://api.moonshot.cn/v1
    export API_MODEL=moonshot-v1-8k

  DeepSeek 示例:
    export OPENAI_API_KEY=sk-...
    export API_BASE_URL=https://api.deepseek.com/v1
    export API_MODEL=deepseek-chat

  不设 API Key 则跳过文本整理，使用原始转录稿。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
import urllib3

# Windows SSL: 某些站点证书链不完整时降级
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Windows 终端兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 配置 ────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"
PODCAST_INBOX_DIR = BASE_DIR / "podcast_inbox"

# Whisper 模型大小: tiny / base / small / medium / large-v3
WHISPER_MODEL_SIZE = "medium"

# ── LLM API 配置 ──────────────────────────────────────────────────
# 支持多种后端，按优先级自动选择:
#   1. ANTHROPIC_API_KEY → Claude (api.anthropic.com)
#   2. OPENAI_API_KEY   → OpenAI / Kimi / DeepSeek 等兼容 API
#
# OpenAI 兼容模式可自定义:
#   API_BASE_URL  (默认: https://api.openai.com/v1)
#   API_MODEL     (默认: gpt-4o)
#
# Kimi 示例:
#   export OPENAI_API_KEY=sk-...
#   export API_BASE_URL=https://api.moonshot.cn/v1
#   export API_MODEL=moonshot-v1-8k
#
# DeepSeek 示例:
#   export OPENAI_API_KEY=sk-...
#   export API_BASE_URL=https://api.deepseek.com/v1
#   export API_MODEL=deepseek-chat

LLM_PROVIDER = "none"  # 自动检测: anthropic / openai / none
LLM_API_KEY = ""
LLM_BASE_URL = ""
LLM_MODEL = ""

# 检测 Anthropic
_ak = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if _ak:
    LLM_PROVIDER = "anthropic"
    LLM_API_KEY = _ak
    LLM_BASE_URL = "https://api.anthropic.com/v1"
    LLM_MODEL = os.environ.get("API_MODEL", "claude-sonnet-4-20250514")

# 检测 OpenAI 兼容（如果没设 Anthropic key 或设了 OPENAI_API_KEY）
_ok = os.environ.get("OPENAI_API_KEY", "").strip()
if _ok and LLM_PROVIDER == "none":
    LLM_PROVIDER = "openai"
    LLM_API_KEY = _ok
    LLM_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    LLM_MODEL = os.environ.get("API_MODEL", "gpt-4o")
elif _ok and LLM_PROVIDER == "openai":
    # 同时设了两个 key，用 OpenAI 的但复用已检测到的 base_url/model
    LLM_API_KEY = _ok

# 日志
LOG_PREFIX = {
    "info": "  📝",
    "step": "  🚀",
    "ok": "  ✅",
    "warn": "  ⚠️ ",
    "audio": "  🔊",
    "transcribe": "  🎙️",
    "brain": "  🧠",
    "write": "  ✍️",
    "deploy": "  🚀",
    "error": "  ❌",
}


def log(tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = LOG_PREFIX.get(tag, "  •")
    print(f"[{ts}] {icon} {msg}")


# ── 工具函数 ────────────────────────────────────────────────────────

def slugify(text):
    """生成文件路径安全的 slug"""
    slug = text.strip()
    for ch in '/\\:?*"<>|':
        slug = slug.replace(ch, "")
    slug = slug.replace(" ", "_")
    # 限制长度
    if len(slug) > 80:
        slug = slug[:80]
    return slug


def safe_filename(text):
    """安全的文件名（保留扩展名用）"""
    safe = text.strip()
    for ch in '/\\:?*"<>|':
        safe = safe.replace(ch, "_")
    return safe


def download_file(url, dest_path, desc="文件"):
    """下载文件并显示进度"""
    log("audio", f"下载 {desc}...")
    try:
        resp = requests.get(url, stream=True, timeout=30, verify=False)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total and downloaded % (1024 * 1024) == 0:
                    pct = downloaded / total * 100
                    print(f"\r    {downloaded // (1024*1024)}MB / {total // (1024*1024)}MB ({pct:.0f}%)", end="")
        if total:
            print(f"\r    {total // (1024*1024)}MB / {total // (1024*1024)}MB (100%)")
        log("ok", f"{desc} 下载完成: {dest_path}")
        return True
    except Exception as e:
        log("error", f"下载失败: {e}")
        return False


def run_cmd(cmd, desc="命令"):
    """执行外部命令"""
    log("info", f"执行: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=False,  # 用 bytes 避免 GBK 编码问题
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        log("error", f"{desc} 超时")
        return False, ""

    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

    if result.returncode != 0:
        log("warn", f"{desc} 退出码: {result.returncode}")
        if stderr.strip():
            err_text = stderr.strip()
            if len(err_text) > 300:
                err_text = err_text[-300:]
            print(f"       {err_text}")
        return False, stdout
    return True, stdout


# ═══════════════════════════════════════════════════════════════════
# 第一步：解析器插件系统
# ═══════════════════════════════════════════════════════════════════

def parse_youtube(url):
    """YouTube 分享链接解析器"""
    patterns = [
        r"youtube\.com/watch\?v=([\w-]+)",
        r"youtu\.be/([\w-]+)",
        r"youtube\.com/shorts/([\w-]+)",
    ]
    video_id = None
    for p in patterns:
        m = re.search(p, url)
        if m:
            video_id = m.group(1)
            break
    if not video_id:
        return None

    log("step", "识别为 YouTube 链接，提取信息...")

    # 用 yt-dlp 获取元数据（不下载）
    ok, out = run_cmd(
        [sys.executable, "-m", "yt_dlp", "--no-check-certificate", "--dump-json", "--no-download", f"https://www.youtube.com/watch?v={video_id}"],
        desc="YouTube 元数据提取",
    )
    if not ok:
        return None

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None

    episode_title = data.get("title", "").strip()
    show_name = data.get("channel", data.get("uploader", ""))
    upload_date = data.get("upload_date", "")  # YYYYMMDD
    if len(upload_date) == 8:
        publish_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    else:
        publish_date = datetime.now().strftime("%Y-%m-%d")

    log("ok", f"  {show_name} — {episode_title} ({publish_date})")

    return {
        "audio_url": url,
        "show_name": show_name,
        "episode_title": episode_title,
        "publish_date": publish_date,
        "source_link": url,
        "platform": "youtube",
        "video_id": video_id,
    }


def parse_xiaoyuzhou(url):
    """小宇宙分享链接解析器"""
    if "xiaoyuzhoufm.com" not in url:
        return None

    log("step", "识别为小宇宙链接，解析页面...")

    # 标准化 URL
    if not url.startswith("http"):
        url = "https://" + url

    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log("error", f"页面获取失败: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 方法1: 从 __NEXT_DATA__ 提取
    next_data = soup.find("script", id="__NEXT_DATA__")
    episode_data = None
    audio_url = None
    episode_title = ""
    show_name = ""
    publish_date = ""

    if next_data:
        try:
            data = json.loads(next_data.string)
            props = data.get("props", {}).get("pageProps", {})
            episode = props.get("episode", {})
            if episode:
                episode_title = episode.get("title", "")
                audio_url = episode.get("audio", {}).get("url", "") or episode.get("enclosure", {}).get("url", "")
                show_name = episode.get("podcast", {}).get("title", "")
                pub_ts = episode.get("pubDate", "") or episode.get("publishedAt", "")
                if pub_ts:
                    if isinstance(pub_ts, (int, float)):
                        publish_date = datetime.fromtimestamp(pub_ts / 1000).strftime("%Y-%m-%d")
                    else:
                        try:
                            publish_date = datetime.fromisoformat(pub_ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                        except ValueError:
                            pass
        except (json.JSONDecodeError, AttributeError):
            pass

    # 方法2: 从页面 meta / audio 标签提取
    if not audio_url:
        audio_tag = soup.find("audio")
        if audio_tag and audio_tag.get("src"):
            audio_url = audio_tag["src"]

    if not audio_url:
        # 查找任何包含 .mp3 的链接
        for script in soup.find_all("script"):
            if script.string:
                mp3s = re.findall(r'(https?://[^"\']+\.mp3[^"\']*)', script.string)
                if mp3s:
                    audio_url = mp3s[0]
                    break

    if not audio_url:
        log("error", "未找到音频链接")
        return None

    if not publish_date:
        publish_date = datetime.now().strftime("%Y-%m-%d")

    log("ok", f"  {show_name} — {episode_title} ({publish_date})")

    return {
        "audio_url": audio_url,
        "show_name": show_name or "小宇宙播客",
        "episode_title": episode_title or "",
        "publish_date": publish_date,
        "source_link": url,
        "platform": "xiaoyuzhou",
    }


def _extract_apple_podcast_id(url):
    """从 Apple Podcasts URL 提取节目 ID"""
    m = re.search(r'/id(\d{6,})', url)
    return m.group(1) if m else None


def _itunes_lookup(podcast_id):
    """用 iTunes Search API 查询播客 RSS feed"""
    try:
        resp = requests.get(
            f"https://itunes.apple.com/lookup?id={podcast_id}",
            timeout=15,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            return results[0].get("feedUrl", "")
    except Exception as e:
        log("warn", f"iTunes API 查询失败: {e}")
    return ""


def _parse_rss_for_episode(feed_url, episode_title=None, episode_guid=None):
    """解析 RSS feed，匹配指定集数"""
    import feedparser
    log("info", f"解析 RSS feed...")

    # 手动获取 RSS XML（避免 feedparser 内部 SSL 问题）
    feed_xml = ""
    try:
        r = requests.get(feed_url, timeout=15, verify=False)
        if r.status_code == 200:
            feed_xml = r.text
    except Exception:
        pass

    if feed_xml:
        feed = feedparser.parse(feed_xml)
    else:
        log("warn", "RSS 下载失败，尝试 feedparser 直连...")
        feed = feedparser.parse(feed_url)

    show_name = feed.feed.get("title", "")
    episodes = []

    for entry in feed.entries:
        audio_url = ""
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" or (link.get("type") and "audio" in link.get("type", "")):
                audio_url = link["href"]
                break
        if not audio_url and entry.get("enclosures"):
            audio_url = entry.enclosures[0].get("href", "")

        pub_struct = entry.get("published_parsed")
        pub_date = ""
        if pub_struct:
            pub_date = f"{pub_struct.tm_year:04d}-{pub_struct.tm_mon:02d}-{pub_struct.tm_mday:02d}"

        episodes.append({
            "title": entry.get("title", ""),
            "url": audio_url,
            "date": pub_date,
            "guid": entry.get("id", ""),
        })

    # 按指定集数匹配
    if episode_guid:
        for ep in episodes:
            if ep["guid"] == episode_guid or episode_guid in ep["guid"]:
                return show_name, ep

    if episode_title:
        for ep in episodes:
            if ep["title"] == episode_title or episode_title in ep["title"]:
                return show_name, ep

    # 不匹配特定集数 → 返回最新一集
    if episodes:
        log("info", f"未指定特定集数，使用最新一集: {episodes[0]['title']}")
        return show_name, episodes[0]

    return show_name, None


def parse_apple_podcasts(url):
    """Apple Podcasts 分享链接解析器（支持节目页和单集页）"""
    if "podcasts.apple.com" not in url and "podcasts.apple" not in url:
        return None

    log("step", "识别为 Apple Podcasts 链接，解析中...")
    if not url.startswith("http"):
        url = "https://" + url

    # 提取参数
    podcast_id = _extract_apple_podcast_id(url)
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    episode_id = query_params.get("i", [None])[0]

    if not podcast_id:
        log("error", "无法提取播客 ID")
        return None

    log("info", f"播客 ID: {podcast_id}" + (f", 单集 ID: {episode_id}" if episode_id else ""))

    # 获取页面信息（尽力而为）
    show_name = ""
    episode_title = ""
    publish_date = ""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, verify=False)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # JSON-LD → show/episode 名
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if data.get("@type") == "PodcastEpisode":
                            episode_title = data.get("name", "") or episode_title
                            show_name = data.get("partOfSeries", {}).get("name", "")
                            pub_date = data.get("datePublished", "")
                            if pub_date:
                                publish_date = pub_date[:10]
                        elif data.get("@type") == "CreativeWorkSeries":
                            show_name = data.get("name", "")
                except (json.JSONDecodeError, AttributeError):
                    pass
            # 从标题回退
            if not episode_title and soup.title:
                page_title = soup.title.string or ""
                if " - Podcast - Apple Podcasts" in page_title:
                    if not show_name:
                        show_name = page_title.split(" - Podcast - Apple Podcasts")[0].strip()
                elif " on Apple Podcasts" in page_title:
                    parts = page_title.split(" on Apple Podcasts")
                    if not episode_title:
                        episode_title = parts[0].strip()
    except Exception as e:
        log("warn", f"页面解析警告: {e}")

    # iTunes API → RSS feed URL
    feed_url = _itunes_lookup(podcast_id)
    if not feed_url:
        log("error", "无法找到播客 RSS feed（iTunes API 查询失败）")
        return {
            "audio_url": "",
            "show_name": show_name or "Apple Podcasts 播客",
            "episode_title": episode_title or "",
            "publish_date": publish_date or datetime.now().strftime("%Y-%m-%d"),
            "source_link": url,
            "platform": "apple_podcasts",
            "feed_url": "",
        }

    log("ok", f"找到 RSS feed: {feed_url}")

    # 从 RSS 匹配集数
    show_name_feed, episode = _parse_rss_for_episode(feed_url, episode_title, episode_id)

    if not show_name:
        show_name = show_name_feed

    audio_url = episode["url"] if episode else ""
    if episode and not episode_title:
        episode_title = episode["title"]
    if episode and not publish_date:
        publish_date = episode["date"]

    if not episode:
        log("warn", "RSS feed 中未找到匹配集数")
    elif not audio_url:
        log("warn", f"找到集数 '{episode_title}' 但无音频链接")
    else:
        log("ok", f"  {show_name} — {episode_title} ({publish_date})")

    if not publish_date:
        publish_date = datetime.now().strftime("%Y-%m-%d")

    return {
        "audio_url": audio_url or "",
        "show_name": show_name or "Apple Podcasts 播客",
        "episode_title": episode_title or "",
        "publish_date": publish_date,
        "source_link": url,
        "platform": "apple_podcasts",
        "feed_url": feed_url,
    }


def parse_generic_ytdlp(url):
    """
    通用 yt-dlp 解析器（兜底）
    尝试用 yt-dlp 处理任意 URL（如 Bilibili、Spotify 等）
    """
    log("step", "尝试 yt-dlp 通用解析器...")

    ok, out = run_cmd(
        [sys.executable, "-m", "yt_dlp", "--no-check-certificate", "--dump-json", "--no-download", url],
        desc="通用元数据提取",
    )
    if not ok:
        return None

    try:
        data = json.loads(out.strip().split("\n")[0])
    except json.JSONDecodeError:
        return None

    episode_title = data.get("title", "").strip()
    show_name = data.get("channel", data.get("uploader", data.get("webpage_url_basename", "")))
    upload_date = data.get("upload_date", "")
    if len(upload_date) == 8:
        publish_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    else:
        publish_date = datetime.now().strftime("%Y-%m-%d")

    platform = data.get("extractor", "generic").lower().split(":")[0]

    log("ok", f"  [{platform}] {show_name} — {episode_title} ({publish_date})")

    return {
        "audio_url": url,
        "show_name": show_name or "未知节目",
        "episode_title": episode_title or "",
        "publish_date": publish_date,
        "source_link": url,
        "platform": platform,
    }


def parse_manual_audio(filepath):
    """用户手动放入的本地音频文件"""
    path = Path(filepath)
    if not path.exists():
        log("error", f"文件不存在: {filepath}")
        return None

    log("ok", f"使用本地音频文件: {path.name}")

    # 从文件名猜测日期和标题
    name = path.stem
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = name

    # 尝试从文件名提取日期（如 2026-07-24-标题.mp3）
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", name)
    if date_match:
        date_str = date_match.group(1)
        title = date_match.group(2).replace("_", " ").replace("-", " ")

    return {
        "audio_url": str(path),
        "show_name": "本地播客",
        "episode_title": title,
        "publish_date": date_str,
        "source_link": str(path),
        "platform": "local",
    }


# 解析器注册列表（按优先级排序）
PARSERS = [
    ("YouTube", parse_youtube),
    ("小宇宙", parse_xiaoyuzhou),
    ("Apple Podcasts", parse_apple_podcasts),
    ("通用 (yt-dlp)", parse_generic_ytdlp),
]


def resolve_audio_source(url_or_path):
    """
    解析音频来源，返回统一元数据。
    输入：URL 或本地文件路径
    """
    # 检查是否本地文件
    local_path = Path(url_or_path)
    if local_path.exists() and local_path.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac"):
        return parse_manual_audio(url_or_path)

    # 遍历解析器
    for name, parser in PARSERS:
        log("info", f"尝试 {name} 解析器...")
        result = parser(url_or_path)
        if result is not None:
            return result

    log("error", f"无法解析来源: {url_or_path}")
    log("info", "提示：可以将音频文件放入 podcast_inbox/ 目录后用 --audio 参数指定")
    return None


# ═══════════════════════════════════════════════════════════════════
# 第二步：音频下载
# ═══════════════════════════════════════════════════════════════════

def download_audio(meta) -> Optional[Path]:
    """
    根据元数据下载音频文件。
    返回本地文件路径，或 None 表示失败。
    """
    PODCAST_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    audio_url = meta["audio_url"]
    platform = meta["platform"]
    date_str = meta["publish_date"]
    title_slug = slugify(meta["episode_title"] or "podcast")
    filename = f"{date_str}-{title_slug}.mp3"
    dest = PODCAST_INBOX_DIR / filename

    # 如果已有缓存则跳过
    if dest.exists():
        log("ok", f"音频已存在: {dest}")
        return dest

    # 本地文件直接复制
    if platform == "local":
        shutil.copy2(audio_url, dest)
        log("ok", f"音频已复制到: {dest}")
        return dest

    # YouTube / 通用 yt-dlp — 用 yt-dlp 下载音频
    if platform in ("youtube",) or audio_url.startswith(("http://", "https://")):
        # 判断是否已经是直链（以 .mp3/.m4a 结尾）
        if re.search(r'\.(mp3|m4a|wav|ogg)(\?|$)', audio_url, re.I):
            if download_file(audio_url, dest, desc="音频"):
                return dest
        else:
            # 用 yt-dlp 下载音频
            log("audio", "用 yt-dlp 下载音频...")
            ok, out = run_cmd([
                sys.executable, "-m", "yt_dlp",
                "--no-check-certificate",
                "-x", "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", str(dest),
                "--no-playlist",
                "--print", "after_move:filepath",
                audio_url,
            ], desc="音频下载")
            if ok:
                # yt-dlp 可能加了额外的后缀，检查
                if dest.exists():
                    return dest
                # 查找实际输出文件
                for f in PODCAST_INBOX_DIR.iterdir():
                    if f.stem.startswith(date_str) and f.suffix in (".mp3", ".m4a", ".wav"):
                        return f
                # 从输出中提取路径
                for line in out.strip().split("\n"):
                    p = Path(line.strip())
                    if p.exists():
                        return p
                log("warn", "yt-dlp 下载完成但未找到输出文件，尝试搜索...")
                # 搜索最近添加的 mp3
                mp3s = sorted(PODCAST_INBOX_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)
                if mp3s:
                    return mp3s[0]
            else:
                return None

    # 普通 URL 直链下载
    if audio_url.startswith(("http://", "https://")):
        if download_file(audio_url, dest, desc="音频"):
            return dest

    log("error", f"无法下载音频: {audio_url}")
    return None


# ═══════════════════════════════════════════════════════════════════
# 第三步：语音转文字
# ═══════════════════════════════════════════════════════════════════

def transcribe_audio(audio_path: Path) -> Optional[dict]:
    """
    用 faster-whisper 将音频转为带时间戳的文字。
    返回分段列表: [{start, end, text}, ...]
    """
    log("transcribe", f"转录音频: {audio_path.name}")
    log("transcribe", f"模型: {WHISPER_MODEL_SIZE}，语言: zh")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("error", "faster_whisper 未安装，请运行: pip install faster-whisper")
        return None

    log("transcribe", "加载模型中（首次使用会下载）...")
    start_time = time.time()

    # GPU 可用则用 GPU
    compute_type = None
    try:
        import torch
        if torch.cuda.is_available():
            compute_type = "float16"
            log("info", "使用 GPU 加速")
        else:
            compute_type = "int8"
            log("info", "使用 CPU（int8 量化）")
    except ImportError:
        compute_type = "int8"
        log("info", "使用 CPU（int8 量化）")

    model = WhisperModel(WHISPER_MODEL_SIZE, device="auto", compute_type=compute_type)

    log("transcribe", "转写中（这可能需要较长时间）...")

    segments, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=5,
        vad_filter=True,        # 过滤静音段
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    duration = time.time() - start_time
    log("ok", f"转写完成！用时 {duration:.0f} 秒")
    log("info", f"检测语言: {info.language} (概率 {info.language_probability:.1%})")

    # 收集分段
    result_segments = []
    for seg in segments:
        result_segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })

    log("ok", f"共 {len(result_segments)} 个语音段")

    return {
        "segments": result_segments,
        "language": info.language,
        "duration": info.duration,
    }


# ═══════════════════════════════════════════════════════════════════
# 第四步：Claude 文本整理
# ═══════════════════════════════════════════════════════════════════

def format_transcript_for_prompt(transcript: dict) -> str:
    """将转录结果格式化为可读文本供 Claude 处理"""
    lines = []
    for seg in transcript["segments"]:
        start_m = int(seg["start"] // 60)
        start_s = int(seg["start"] % 60)
        timestamp = f"[{start_m:02d}:{start_s:02d}]"
        lines.append(f"{timestamp} {seg['text']}")
    return "\n".join(lines)


def call_llm_api(system_prompt, user_prompt, max_tokens=4096):
    """调用 LLM API（自动选择后端）"""
    if LLM_PROVIDER == "none":
        log("warn", "未检测到 LLM API Key")
        log("info", "可用方式:")
        log("info", "  1) export ANTHROPIC_API_KEY=sk-ant-...  (Claude)")
        log("info", "  2) export OPENAI_API_KEY=sk-...         (OpenAI/Kimi/DeepSeek)")
        log("info", "  3) 用 --transcript 跳过文本整理步骤")
        return None

    log("brain", f"后端: {LLM_PROVIDER}, 模型: {LLM_MODEL}")

    if LLM_PROVIDER == "anthropic":
        return _call_anthropic(system_prompt, user_prompt, max_tokens)
    else:
        return _call_openai(system_prompt, user_prompt, max_tokens)


def _call_anthropic(system_prompt, user_prompt, max_tokens):
    """调用 Anthropic Claude API"""
    headers = {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt}
        ],
    }
    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/messages",
            headers=headers,
            json=payload,
            timeout=300,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        text_parts = [block["text"] for block in content if block.get("type") == "text"]
        return "\n".join(text_parts)
    except Exception as e:
        log("error", f"API 调用失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                err_data = e.response.json()
                log("error", f"  {err_data.get('error', {}).get('message', e.response.text[:200])}")
            except json.JSONDecodeError:
                log("error", f"  {e.response.text[:200]}")
        return None


def _call_openai(system_prompt, user_prompt, max_tokens):
    """调用 OpenAI 兼容 API（Kimi / DeepSeek / OpenAI 等）"""
    headers = {
        "authorization": f"Bearer {LLM_API_KEY}",
        "content-type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log("error", f"API 调用失败: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                err_data = e.response.json()
                log("error", f"  {err_data.get('error', {}).get('message', e.response.text[:200])}")
            except json.JSONDecodeError:
                log("error", f"  {e.response.text[:200]}")
        return None


SYSTEM_PROMPT_CLEANUP = """你是一个专业的播客转录稿整理专家。你的任务是将语音识别转录稿整理成一篇可读性高的博客文章。

## 要求

1. **去口语化**：去掉语气词（嗯、啊、这个、那个）、重复口误、不完整的句子
2. **合并分段**：将零散的语音分段合并成有逻辑的段落
3. **加小标题**：按话题自然分段，为每段加一个 ## 小标题
4. **写摘要**：文章开头用一段话（200字以内）概括本期内容
5. **保留时间戳**：关键内容旁保留 [MM:SS] 时间戳，方便读者跳转到原音频对应位置
6. **保留说话人标记**：如果转录稿中有说话人标记（如 主持人/嘉宾），保留并标注
7. **保持原意**：不要添加转录稿中没有的观点和信息
8. **语言**：使用原文语言（中文为主）

## 输出格式

```markdown
> 本期摘要（200字以内）

## 小标题1

正文段落……[01:23]

## 小标题2

正文段落……[05:45]

---

*本文章由播客「节目名」转录整理而成。*
*原始链接：链接地址*
```"""


def cleanup_transcript(transcript: dict, meta: dict) -> Optional[str]:
    """
    用 LLM API 整理转录稿。
    返回整理后的 Markdown 文本。
    """
    if not transcript or not transcript.get("segments"):
        log("warn", "没有转录内容可整理")
        return None

    raw_text = format_transcript_for_prompt(transcript)
    total_chars = len(raw_text)
    if total_chars < 10:
        log("warn", "转录稿内容为空，跳过文本整理")
        return None
    log("brain", f"转录稿共 {total_chars} 字，发送给 LLM 整理...")

    if total_chars > 80000:
        log("warn", f"转录稿较长（{total_chars}字），处理可能需要更长时间")
        estimated_tokens = total_chars // 2
        max_tokens = min(max(4096, estimated_tokens), 16384)
    else:
        max_tokens = 4096

    user_prompt = f"""请整理以下播客转录稿为博客文章。

## 节目信息
- 节目：{meta.get('show_name', '')}
- 标题：{meta.get('episode_title', '')}
- 日期：{meta.get('publish_date', '')}
- 原始链接：{meta.get('source_link', '')}

## 转录稿（带时间戳）
{raw_text}
"""

    log("brain", "等待 LLM 响应...")
    result = call_llm_api(SYSTEM_PROMPT_CLEANUP, user_prompt, max_tokens)

    if result:
        log("ok", f"文本整理完成，共 {len(result)} 字")
        if "原始链接" not in result and meta.get("source_link"):
            result += f"\n\n---\n\n*本文章由播客「{meta.get('show_name', '')}」转录整理而成。*\n"
            result += f"*原始链接：{meta.get('source_link', '')}*"
        return result
    return None


# ═══════════════════════════════════════════════════════════════════
# 第五步：生成博客文章
# ═══════════════════════════════════════════════════════════════════

def generate_article(cleaned_text: str, meta: dict, reading_time: int = None) -> Path:
    """
    生成 articles/{slug}/draft.md 文件。
    返回 draft.md 路径。
    """
    title = meta["episode_title"] or f"播客：{meta['show_name']}"
    date_str = meta["publish_date"]
    slug = slugify(title)
    show_name = meta["show_name"]
    source_link = meta["source_link"]

    # 提取摘要（从整理稿的第一段）
    excerpt = ""
    if cleaned_text:
        # 取第一段或 blockquote 内容
        excerpt_match = re.search(r'>\s*(.+?)(?:\\n|$)', cleaned_text)
        if excerpt_match:
            excerpt = excerpt_match.group(1).strip()
        if not excerpt or len(excerpt) < 10:
            # 取前 150 字
            text_clean = re.sub(r'[#*\[\]]', '', cleaned_text)
            excerpt = text_clean[:150].strip().split('\n')[0]

    # 计算阅读时间
    if reading_time is None:
        zh_chars = len(re.findall(r'[一-鿿]', cleaned_text or ""))
        reading_time = max(1, round(zh_chars / 500))

    # 构建正文
    # 移除摘要 blockquote（已在 metadata 中）
    body = cleaned_text or ""
    body = re.sub(r'^>\s*[^\\n]*\\n?', '', body).strip()

    # 确保有来源标注
    if "原始链接" not in body:
        body += f"\n\n---\n\n*本文章由播客「{show_name}」转录整理而成。*\n"
        body += f"*原始链接：{source_link}*"

    # 写入 draft.md
    draft_dir = ARTICLES_DIR / slug
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / "draft.md"

    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"> 栏目：未分类\n")
        f.write(f"> 日期：{date_str}\n")
        f.write(f"> 标签：播客\n")
        f.write(f"> 排序：0\n")
        f.write(f"> 阅读时间：{reading_time}\n")
        f.write(f"> 摘要：{excerpt}\n")
        f.write("\n")
        f.write(body)
        f.write("\n")

    log("ok", f"文章已生成: {draft_path}")
    return draft_path


# ═══════════════════════════════════════════════════════════════════
# 构建与部署
# ═══════════════════════════════════════════════════════════════════

def build_site():
    """运行 publish.py build"""
    log("deploy", "构建站点...")
    ok, out = run_cmd(
        [sys.executable, str(BASE_DIR / "publish.py"), "build"],
        desc="站点构建",
    )
    if ok:
        if out and out.strip():
            for line in out.strip().split("\n"):
                print(f"       {line}")
        return True
    # 即使警告也视为成功，只要 publish.py 正常退出
    log("warn", "构建过程有警告（已忽略）")
    return True


def deploy(commit_msg=None):
    """git add / commit / push"""
    log("deploy", "部署到 GitHub Pages...")

    # git add
    ok, out = run_cmd(["git", "add", "-A"], desc="git add")
    if not ok:
        return False

    # git commit
    if not commit_msg:
        commit_msg = f"deploy: 播客转文章 {datetime.now().strftime('%Y-%m-%d')}"
    ok, out = run_cmd(["git", "commit", "-m", commit_msg], desc="git commit")
    if not ok:
        if "nothing to commit" in out.lower() or "nothing to commit" in (out or "").lower():
            log("info", "没有新变更需要提交")
            return True
        return False

    # git push
    ok, out = run_cmd(["git", "push", "origin", "main"], desc="git push")
    if ok:
        log("deploy", "部署完成！")
        return True
    return False


# ═══════════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════════

def process_episode(url_or_path, skip_deploy=False, skip_transcribe=False):
    """
    完整处理一集播客：
    1. 解析 → 2. 下载 → 3. 转写 → 4. 整理 → 5. 生成文章 → 6. 构建 → 7. 部署
    """
    print()
    log("step", "=" * 50)
    log("step", "播客转博客文章 - 处理开始")
    log("step", "=" * 50)
    print()

    # ── 1. 解析来源 ──
    log("step", "【第一步】解析音频来源")
    meta = resolve_audio_source(url_or_path)
    if not meta:
        return False
    print()

    # ── 2. 下载音频 ──
    log("step", "【第二步】获取音频文件")
    audio_path = None
    if meta["platform"] != "local":
        audio_path = download_audio(meta)
        if not audio_path:
            return False
    else:
        audio_path = Path(meta["audio_url"])
        log("ok", f"使用本地文件: {audio_path}")
    print()

    # ── 3. 语音转文字 ──
    transcript = None
    if not skip_transcribe:
        log("step", "【第三步】语音转文字")
        transcript = transcribe_audio(audio_path)
        if not transcript:
            log("error", "转写失败")
            return False

        # 保存转录稿 JSON
        transcript_path = audio_path.with_suffix(".transcript.json")
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        log("ok", f"转录稿已保存: {transcript_path}")

        # 也保存纯文本版本
        text_path = audio_path.with_suffix(".txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(format_transcript_for_prompt(transcript))
        log("ok", f"文本稿已保存: {text_path}")
        print()
    else:
        # 尝试加载已有转录稿
        txt_path = audio_path.with_suffix(".txt")
        if txt_path.exists():
            log("info", f"使用已有转录稿: {txt_path}")
            with open(txt_path, "r", encoding="utf-8") as f:
                raw = f.read()
            # 构造伪 segments
            lines = raw.strip().split("\n")
            pseudo_segments = []
            for line in lines:
                ts_match = re.match(r'\[(\d+):(\d+)\]\s*(.*)', line)
                if ts_match:
                    start = int(ts_match.group(1)) * 60 + int(ts_match.group(2))
                    pseudo_segments.append({"start": start, "end": start + 30, "text": ts_match.group(3)})
                else:
                    pseudo_segments.append({"start": 0, "end": 0, "text": line})
            transcript = {"segments": pseudo_segments, "language": "zh", "duration": 0}
        else:
            log("warn", "未找到已有转录稿，跳过文本整理，仅生成元数据文章")
            transcript = {
                "segments": [{"start": 0, "end": 0, "text": ""}],
                "language": "zh",
                "duration": 0,
            }
            # 标记无内容，后续跳过文本整理
            meta["_no_content"] = True

    # ── 4. Claude 文本整理 ──
    log("step", "【第四步】Claude 文本整理")
    cleaned = cleanup_transcript(transcript, meta)
    if not cleaned:
        log("warn", "文本整理跳过，将使用原始转录稿")
        # 使用原始转录稿作为后备
        raw_lines = []
        for seg in transcript["segments"]:
            m, s = int(seg["start"] // 60), int(seg["start"] % 60)
            raw_lines.append(f"[{m:02d}:{s:02d}] {seg['text']}")
        cleaned = "\n".join(raw_lines)
    print()

    # ── 5. 生成文章 ──
    log("step", "【第五步】生成博客文章")
    draft_path = generate_article(cleaned, meta)
    print()

    # ── 6. 构建站点 ──
    log("step", "【第六步】构建站点")
    if not build_site():
        log("error", "站点构建失败")
        return False
    print()

    # ── 7. 部署 ──
    if not skip_deploy:
        log("step", "【第七步】部署")
        if not deploy():
            log("warn", "请手动部署: bash deploy.sh")
        print()

    print()
    log("ok", "=" * 50)
    log("ok", f"全部完成！文章: {draft_path}")
    log("ok", f"博客: https://daitree42.github.io/blog-pages/")
    log("ok", "=" * 50)
    return True


def process_transcript_only(transcript_file, skip_deploy=False):
    """
    直接用已有转录稿文件生成博客文章。
    转录稿格式：每行 [MM:SS] 文本，或纯文本。
    """
    log("step", "使用已有转录稿...")

    path = Path(transcript_file)
    if not path.exists():
        log("error", f"文件不存在: {transcript_file}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 从文件名推测元数据
    name = path.stem
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    title = name
    if date_match:
        title = name[11:] if len(name) > 11 else name

    meta = {
        "show_name": "播客节目",
        "episode_title": title.replace("_", " ").replace("-", " "),
        "publish_date": date_str,
        "source_link": "",
    }

    # 构建伪 segments
    lines = content.strip().split("\n")
    segments = []
    for line in lines:
        ts_match = re.match(r'\[(\d+):(\d+)\]\s*(.*)', line)
        if ts_match:
            start = int(ts_match.group(1)) * 60 + int(ts_match.group(2))
            segments.append({"start": start, "end": start + 30, "text": ts_match.group(3)})
        else:
            segments.append({"start": 0, "end": 0, "text": line})
    transcript = {"segments": segments, "language": "zh", "duration": 0}

    # Claude 整理
    log("step", "文本整理...")
    cleaned = cleanup_transcript(transcript, meta)

    if cleaned:
        log("step", "生成文章...")
        draft_path = generate_article(cleaned, meta)
    else:
        log("warn", "文本整理跳过，使用原始内容")
        draft_path = generate_article(content, meta)

    if not skip_deploy:
        build_site()
        deploy()

    log("ok", f"文章已生成: {draft_path}")
    return True


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🎙️ 播客转博客文章流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python podcast2blog.py https://www.youtube.com/watch?v=xxx     # YouTube 播客
  python podcast2blog.py https://www.xiaoyuzhoufm.com/episode/xxx # 小宇宙
  python podcast2blog.py --audio ./podcast.mp3                    # 本地音频
  python podcast2blog.py --transcript ./转录稿.txt                  # 已有转录稿
  python podcast2blog.py --build                                  # 仅构建
  python podcast2blog.py --serve                                  # 仅预览
        """,
    )
    parser.add_argument("url", nargs="?", help="播客分享链接")
    parser.add_argument("--audio", help="本地音频文件路径")
    parser.add_argument("--transcript", help="已有转录稿文件路径（跳过转写）")
    parser.add_argument("--no-deploy", action="store_true", help="跳过部署步骤")
    parser.add_argument("--no-transcribe", action="store_true", help="跳过转写步骤")
    parser.add_argument("--whisper-model", default=None,
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper 模型大小（默认: medium）")
    parser.add_argument("--build", action="store_true", help="仅构建站点")
    parser.add_argument("--serve", action="store_true", help="本地预览")

    args = parser.parse_args()

    # 全局模型设置（必须在函数顶部声明 global）
    global WHISPER_MODEL_SIZE
    if args.whisper_model:
        WHISPER_MODEL_SIZE = args.whisper_model

    # 处理构建/预览
    if args.build:
        build_site()
        return
    if args.serve:
        run_cmd([sys.executable, str(BASE_DIR / "publish.py"), "serve"], "预览")
        return

    # 判断输入类型
    if args.transcript:
        process_transcript_only(args.transcript, skip_deploy=args.no_deploy)
    elif args.audio:
        process_episode(args.audio, skip_deploy=args.no_deploy, skip_transcribe=args.no_transcribe)
    elif args.url:
        process_episode(args.url, skip_deploy=args.no_deploy, skip_transcribe=args.no_transcribe)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
