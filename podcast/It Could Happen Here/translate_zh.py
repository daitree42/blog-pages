#!/usr/bin/env python3
"""
translate_zh.py — 将 season1/*.md 英文转录稿翻译为中文文字稿

中文版规范（用户指定）：
- 无时间戳
- 按话题自然分段
- 说话人标注 **Speaker 1：**
- 只去噪不润色，保留全部信息

用法:
    python translate_zh.py               # 翻译全部（跳过已有）
    python translate_zh.py --only 001    # 只翻译 001
    python translate_zh.py --overwrite   # 覆盖已有中文
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = Path(__file__).resolve().parent
SEASON = BASE / "season1"
ZH_DIR = SEASON / "中文"

CHUNK_MAX_CHARS = 7000  # 每批英文字符数（避免超长截断）


def load_key() -> str:
    env = {}
    p = Path(r"C:\cc\blog-pages\.env")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")


KEY = load_key()

_SESSION = requests.Session()  # 复用连接，减少 TLS 握手被重置


def call_deepseek(system: str, user: str, max_tokens: int = 8000, temperature: float = 0.3) -> str:
    if not KEY:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY（检查 C:/cc/blog-pages/.env）")
    for attempt in range(5):
        try:
            r = _SESSION.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=600,
                verify=False,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == 4:
                raise
            wait = min(5 * (2 ** attempt), 60)
            print(f"    ⚠️ API 调用失败（第 {attempt+1}/5 次重试, {wait}s 后重试）: {str(e)[:100]}")
            time.sleep(wait)
    raise RuntimeError("DeepSeek API 调用失败（重试耗尽）")


def parse_md(text: str):
    """解析英文 md → (title, [(start_ts, text), ...])"""
    lines = text.split("\n")
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    paras = []
    for block in text.split("\n\n"):
        b = block.strip()
        if not b or b.startswith("#"):
            continue
        m = re.match(r"\*\*\[(\d+:\d+)\]\*\*\s*\*\*[^*]+\*\*：?\s*(.*)", b, re.S)
        if m:
            paras.append((m.group(1), m.group(2).strip()))
        else:
            paras.append(("", b))
    return title, paras


def split_long_text(text: str, limit: int) -> list:
    """按句子把超长段拆成多段（避免单批输入过大导致截断）"""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) + 1 > limit and cur:
            out.append(cur)
            cur = s
        else:
            cur = (cur + " " + s) if cur else s
    if cur:
        out.append(cur)
    return out


def chunk_paras(paras, max_chars=CHUNK_MAX_CHARS):
    """按累计字符数把段落切成批；超长单段先按句子拆分"""
    norm = []
    for ts, text in paras:
        if len(text) > max_chars:
            for part in split_long_text(text, max_chars):
                norm.append((ts, part))
        else:
            norm.append((ts, text))

    chunks, cur, cur_len = [], [], 0
    for ts, text in norm:
        if cur_len + len(text) > max_chars and cur:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append((ts, text))
        cur_len += len(text)
    if cur:
        chunks.append(cur)
    return chunks


SYSTEM_PROMPT = """你是专业的播客翻译专家，将英文播客转录稿翻译为自然流畅的中文文字稿。

## 翻译规则
1. **只做"去噪"，不做"润色"**：保留说话人原有的用词习惯、语气和口语化表达。仅删除纯填充的语气词（um、uh、you know、like 等）和口误重复。不要为了让中文通顺而替换用词或改变句式。
2. **忠实翻译**：保留原文全部信息，不遗漏、不添加。
3. **跳过无意义噪声**：如果某段是明显的语音识别错误产生的乱码、不成句的重复音节、或音频杂音误识别内容（无实义），跳过不译，不要在输出中出现对应乱码。
4. **自然分段**：按话题转换自然分段，同一话题的连续内容合并为完整段落，不要一句一段。段落之间用空行分隔。
5. **不要时间戳**：不要输出 [MM:SS] 或任何时间标记。
6. **说话人标注**：每段开头用 **Speaker 1：** 标注。
7. **专有名词**：首次出现时保留英文 +（中文），如 The Daily（每日新闻），后续可直接用中文。

## 输出格式
只输出翻译后的文字稿正文，不要任何解释、评论或额外内容。"""


def translate_title(en_title: str) -> str:
    try:
        zh = call_deepseek(
            "你是翻译专家。把英文播客标题翻译成简洁的中文标题，只输出中文，不要引号和解释。",
            en_title,
            max_tokens=60,
        )
        return zh.strip().strip('"').strip("“”")
    except Exception as e:
        print(f"    ⚠️ 标题翻译失败: {e}")
        return en_title


def translate_chunk(chunk, en_title: str) -> str:
    """翻译一批段落 → 中文文本"""
    raw = "\n\n".join(t for _, t in chunk)
    user = f"这是播客《{en_title}》的一段转录稿，请翻译成中文：\n\n{raw}"
    return call_deepseek(SYSTEM_PROMPT, user)


def main():
    parser = argparse.ArgumentParser(description="英文转录稿 → 中文文字稿")
    parser.add_argument("--only", default="", help="只处理指定文件，如 001,002")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有中文")
    args = parser.parse_args()

    ZH_DIR.mkdir(parents=True, exist_ok=True)

    mds = sorted(SEASON.glob("*.md"))
    if args.only:
        wanted = set(f"{n}.md" for n in args.only.split(","))
        mds = [f for f in mds if f.name in wanted]

    if not mds:
        print("season1 下没有 .md 文件")
        return

    failed = []
    for md in mds:
        try:
            out = ZH_DIR / md.name
            if out.exists() and not args.overwrite:
                print(f"⏭️  跳过（已存在）: {out.name}")
                continue

            title, paras = parse_md(md.read_text(encoding="utf-8"))
            if not paras:
                print(f"⚠️  无内容: {md.name}")
                continue

            print(f"\n📄 {md.name} — 《{title}》 ({len(paras)} 段)")
            zh_title = translate_title(title)
            print(f"  标题 → {zh_title}")

            chunks = chunk_paras(paras)
            parts = []
            for i, chunk in enumerate(chunks, 1):
                t0 = time.time()
                text = translate_chunk(chunk, title)
                parts.append(text)
                print(f"  批 {i}/{len(chunks)} 完成 ({time.time()-t0:.0f}s, 输入{sum(len(t) for _,t in chunk)}字符)")
                time.sleep(1.5)  # 批间小延迟，降低连接被重置概率

            body = "\n\n".join(parts)
            out.write_text(f"# {zh_title}\n\n{body}\n", encoding="utf-8")
            print(f"  ✅ 已写入: {out.relative_to(BASE)} ({len(body)} 字符)")
        except Exception as e:
            failed.append(md.name)
            print(f"  ❌ {md.name} 处理失败: {str(e)[:150]}（稍后重跑即可续传）")

    if failed:
        print(f"\n⚠️ {len(failed)} 个文件失败，可重跑续传: {', '.join(failed)}")
    print("\n全部完成。")


if __name__ == "__main__":
    main()
