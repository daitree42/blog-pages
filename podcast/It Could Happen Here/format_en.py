#!/usr/bin/env python3
"""
format_en.py — 为英文播客文字稿添加章节小标题、细分段落，便于阅读（对照中文版）

输入: season1/*.md（英文转录稿，含 **[MM:SS]** **Speaker 1：** 标注）
输出: season1/English/整理版/*.md（# 英文原标题 + Summary: xxx + ## 小标题 + 分段正文，去时间戳）

用法:
    python format_en.py               # 处理全部（跳过已有）
    python format_en.py --only 002    # 只处理指定
    python format_en.py --overwrite   # 覆盖已有
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
OUT_DIR = SEASON / "English" / "整理版"

CHUNK_MAX_CHARS = 5000  # 每批英文字符数（避免超长截断）


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
    """解析英文转录稿 → (title, [段落, ...])；去掉 **[MM:SS]** 时间戳，保留 **Speaker 1：**"""
    lines = text.split("\n")
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    paras = []
    for block in text.split("\n\n"):
        b = block.strip()
        if not b or b.startswith("#"):
            continue
        b = re.sub(r"\*\*\[\d+:\d+\]\*\*\s*", "", b)  # 去掉 **[MM:SS]**
        b = re.sub(r"\s+", " ", b).strip()  # 折叠空白为单段
        if b:
            paras.append(b)
    return title, paras


def chunk_paras(paras, max_chars=CHUNK_MAX_CHARS):
    """按累计字符数切成批；超长单段按句子拆分"""
    norm = []
    for p in paras:
        if len(p) > max_chars:
            sentences = re.split(r"(?<=[.!?])\s+", p)
            cur = ""
            for s in sentences:
                if len(cur) + len(s) + 1 > max_chars and cur:
                    norm.append(cur)
                    cur = s
                else:
                    cur = (cur + " " + s) if cur else s
            if cur:
                norm.append(cur)
        else:
            norm.append(p)

    chunks, cur, cur_len = [], [], 0
    for p in norm:
        if cur_len + len(p) > max_chars and cur:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += len(p)
    if cur:
        chunks.append(cur)
    return chunks


SYSTEM_PROMPT = """You are a podcast transcript layout editor. Restructure an English podcast transcript into a readable, sectioned format.

## Layout rules
1. **Section by topic**: add a concise `##` heading (English, at most 6 words) for each topic section.
2. **Break up paragraphs**: split overly long paragraphs into shorter natural paragraphs (about 60-150 words each) for readability.
3. **Faithful preservation**: keep ALL content, information and speaker labels (**Speaker 1：**). Only add headings and paragraph breaks. Never delete, rewrite or omit anything.
4. **No timestamps**: do not output any time markers.
5. Separate paragraphs and sections with a blank line.

## Output format
## Heading

paragraph...

## Heading

paragraph..."""


def format_first_chunk(chunk, en_title: str) -> str:
    """第一块：输出 Summary + 加标题分段正文"""
    raw = "\n\n".join(chunk)
    user = (
        f"This is the first part of the podcast \"{en_title}\". First output a single line starting with "
        f"\"Summary: \" giving a one-sentence summary of this episode (under 100 words). Then restructure "
        f"the body following the layout rules.\n\n{raw}"
    )
    return call_deepseek(SYSTEM_PROMPT, user)


def format_chunk(chunk, en_title: str) -> str:
    """后续块：加标题分段正文（不输出 Summary）"""
    raw = "\n\n".join(chunk)
    user = f"This is a later part of the podcast \"{en_title}\". Restructure the body following the layout rules (do not output a Summary).\n\n{raw}"
    return call_deepseek(SYSTEM_PROMPT, user)


def extract_summary(body: str) -> str:
    """从整理稿正文提取 Summary 行"""
    m = re.search(r"^Summary[：:]\s*(.+)$", body, re.M)
    if not m:
        m = re.search(r"^摘要[：:]\s*(.+)$", body, re.M)
    return m.group(1).strip() if m else ""


def main():
    parser = argparse.ArgumentParser(description="英文稿加标题/分段/摘要")
    parser.add_argument("--only", default="", help="只处理指定文件，如 002,003")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

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
            out = OUT_DIR / md.name
            if out.exists() and not args.overwrite:
                print(f"⏭️  跳过（已存在）: {out.name}")
                continue

            title, paras = parse_md(md.read_text(encoding="utf-8"))
            if not paras:
                print(f"⚠️  无内容: {md.name}")
                continue

            print(f"\n📄 {md.name} — 《{title}》 ({len(paras)} 段)")
            chunks = chunk_paras(paras)
            parts = []
            for i, chunk in enumerate(chunks, 1):
                t0 = time.time()
                text = format_first_chunk(chunk, title) if i == 1 else format_chunk(chunk, title)
                parts.append(text)
                print(f"  批 {i}/{len(chunks)} 完成 ({time.time()-t0:.0f}s, {sum(len(p) for p in chunk)}字符)")
                time.sleep(1.5)

            body = "\n\n".join(parts)
            # 提取 Summary（第一块输出的），并从正文移除避免重复
            summary = extract_summary(body)
            body_clean = re.sub(r"^Summary[：:]\s*.+$", "", body, count=1, flags=re.M)
            body_clean = re.sub(r"^摘要[：:]\s*.+$", "", body_clean, count=1, flags=re.M)
            body_clean = re.sub(r"\n{3,}", "\n\n", body_clean).strip()
            content = f"# {title}\n\nSummary: {summary}\n\n{body_clean}\n"
            out.write_text(content, encoding="utf-8")
            print(f"  ✅ 已写入: {out.relative_to(BASE)} ({len(content)} 字符)")
        except Exception as e:
            failed.append(md.name)
            print(f"  ❌ {md.name} 处理失败: {str(e)[:150]}（稍后重跑即可续传）")

    if failed:
        print(f"\n⚠️ {len(failed)} 个文件失败，可重跑续传: {', '.join(failed)}")
    print("\n全部完成。")


if __name__ == "__main__":
    main()
