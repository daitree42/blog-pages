#!/usr/bin/env python3
"""
format_zh.py — 为中文播客文字稿添加章节小标题、细分段落，便于阅读

输入: season1/中文/*.md（翻译稿，含 **Speaker 1：** 标注）
输出: season1/中文/整理版/*.md（# 标题 + 摘要：xxx + ## 小标题 + 分段正文）

用法:
    python format_zh.py               # 处理全部（跳过已有）
    python format_zh.py --only 001    # 只处理指定
    python format_zh.py --overwrite   # 覆盖已有
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
ZH_DIR = BASE / "season1" / "中文"
OUT_DIR = ZH_DIR / "整理版"

CHUNK_MAX_CHARS = 6000  # 每批中文字符数（避免超长截断）


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
    """解析翻译稿 → (title, [段落, ...])"""
    lines = text.split("\n")
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else ""
    paras = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
    return title, paras


def chunk_paras(paras, max_chars=CHUNK_MAX_CHARS):
    """按累计字符数切成批"""
    chunks, cur, cur_len = [], [], 0
    for p in paras:
        if cur_len + len(p) > max_chars and cur:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += len(p)
    if cur:
        chunks.append(cur)
    return chunks


SYSTEM_PROMPT = """你是播客文字稿排版编辑。将中文播客文字稿整理成便于阅读的章节化格式。

## 排版要求
1. **按话题分章节**：每章添加一个简洁的 ## 小标题（不超过 15 字）。
2. **细分段落**：把过长的段落拆分成更短的自然段（每段约 100-250 字），方便阅读。
3. **忠实保留**：保留全部内容、信息与说话人标注（**姓名：**）。只添加标题和分段，绝不删除、改写或省略任何内容。
4. **不要时间戳**：不要输出任何时间标记。
5. 段落之间、章节之间用空行分隔。

## 输出格式
## 小标题

段落……

## 小标题

段落……"""


def format_first_chunk(chunk, zh_title: str) -> str:
    """第一块：输出摘要 + 加标题分段正文"""
    raw = "\n\n".join(chunk)
    user = (
        f"这是播客《{zh_title}》第一部分文字稿。请先在开头输出一行「摘要：」并给出一句话概括本期内容（100 字以内），"
        f"然后按排版规则整理正文。\n\n{raw}"
    )
    return call_deepseek(SYSTEM_PROMPT, user)


def format_chunk(chunk, zh_title: str) -> str:
    """后续块：加标题分段正文（不输出摘要）"""
    raw = "\n\n".join(chunk)
    user = f"这是播客《{zh_title}》的后续部分文字稿。请按排版规则整理正文（不要输出摘要）。\n\n{raw}"
    return call_deepseek(SYSTEM_PROMPT, user)


def extract_summary(body: str) -> str:
    """从整理稿正文提取摘要行"""
    m = re.search(r"^摘要[：:]\s*(.+)$", body, re.M)
    return m.group(1).strip() if m else ""


def main():
    parser = argparse.ArgumentParser(description="中文稿加标题/分段/摘要")
    parser.add_argument("--only", default="", help="只处理指定文件，如 001,002")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mds = sorted(ZH_DIR.glob("*.md"))
    if args.only:
        wanted = set(f"{n}.md" for n in args.only.split(","))
        mds = [f for f in mds if f.name in wanted]

    if not mds:
        print("season1/中文/ 下没有 .md 文件")
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
            # 提取摘要（第一块输出的），并从正文移除摘要行避免重复
            summary = extract_summary(body)
            body_clean = re.sub(r"^摘要[：:]\s*.+$", "", body, count=1, flags=re.M)
            body_clean = re.sub(r"\n{3,}", "\n\n", body_clean).strip()
            content = f"# {title}\n\n摘要：{summary}\n\n{body_clean}\n"
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
