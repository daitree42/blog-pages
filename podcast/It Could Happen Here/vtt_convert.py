#!/usr/bin/env python3
"""
vtt_convert.py — WebVTT 字幕 → Markdown 文字稿

用法:
    python vtt_convert.py --to-en                 # 把 season1/*.vtt 转为 season1/*.md（英文，保留时间戳）
    python vtt_convert.py --to-en --only 001,002  # 只转指定文件
"""

import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
VTT_DIR = BASE / "season1"


def parse_vtt(text: str):
    """解析 WebVTT，返回 [(start_sec, speaker, text), ...]"""
    cues = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(
            r"^(\d{1,2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*\d{1,2}:\d{2}:\d{2}[.,]\d{3}",
            line,
        )
        if m:
            h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            start = h * 3600 + mi * 60 + s + ms / 1000
            i += 1
            texts = []
            while i < len(lines) and lines[i].strip():
                texts.append(lines[i].strip())
                i += 1
            raw = " ".join(texts)
            speaker = "Speaker"
            m2 = re.match(r"^<v\s+([^>]+)>\s*(.*)$", raw, re.S)
            if m2:
                speaker = m2.group(1).strip()
                raw = m2.group(2).strip()
            if raw:
                cues.append((start, speaker, raw))
        else:
            i += 1
    return cues


def fmt_time(sec: float) -> str:
    m, s = int(sec // 60), int(sec % 60)
    return f"{m:02d}:{s:02d}"


def build_md(cues, merge_gap=6.0) -> str:
    """合并连续同说话人 cue 为段落（字幕逐句切割，用明显停顿 >6s 作为分段点），段前加时间戳 + 说话人标注"""
    paras = []  # (start, end, speaker, text)
    for start, sp, text in cues:
        if paras and paras[-1][2] == sp and start - paras[-1][1] <= merge_gap:
            ps, pe, psp, ptext = paras[-1]
            paras[-1] = (ps, max(pe, start), psp, ptext + " " + text)
        else:
            paras.append((start, start, sp, text))
    return "\n\n".join(f"**[{fmt_time(p[0])}]** **{p[2]}：** {p[3]}" for p in paras)


def main():
    parser = argparse.ArgumentParser(description="WebVTT → Markdown 文字稿")
    parser.add_argument("--to-en", action="store_true", help="VTT → 英文 MD")
    parser.add_argument("--only", default="", help="只处理指定文件，如 001,002")
    args = parser.parse_args()

    if not args.to_en:
        print("请指定 --to-en")
        return

    vtts = sorted(VTT_DIR.glob("*.vtt"))
    if args.only:
        wanted = set(f"{n}.vtt" for n in args.only.split(","))
        vtts = [f for f in vtts if f.name in wanted]

    if not vtts:
        print(f"season1 目录下没有 .vtt 文件: {VTT_DIR}")
        return

    for vtt in vtts:
        text = vtt.read_text(encoding="utf-8")
        # 标题（WEBVTT 第一行）
        first = text.splitlines()[0]
        title = first.replace("WEBVTT", "").replace("-", "").strip()
        cues = parse_vtt(text)
        body = build_md(cues)
        out = VTT_DIR / vtt.with_suffix(".md").name
        out.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        print(f"✅ {vtt.name} → {out.name}  ({len(cues)} cue, {len(body)} 字符)")


if __name__ == "__main__":
    main()
