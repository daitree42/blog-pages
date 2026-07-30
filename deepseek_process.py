#!/usr/bin/env python3
"""
deepseek_process.py — 用 DeepSeek 校对/翻译播客文稿（委托给 podcast2blog.py）

使用方式:
    # 翻译英文转录稿为中文
    python deepseek_process.py --input ./transcript.txt --show "The Daily" --episode "标题"

    # 仅整理（不翻译）
    python deepseek_process.py --input ./zh_transcript.txt --cleanup

    # 同步到播客站
    python deepseek_process.py --input ./transcript.txt --podcast-site

注意: 此脚本是原专用版的重写，核心逻辑已移至 podcast2blog.py。
      用以下命令可达到相同效果:
        python podcast2blog.py --transcript ./transcript.txt --translate
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(
        description="校对/翻译播客文稿（委托 podcast2blog.py）",
    )
    parser.add_argument("--input", required=True, help="转录文本文件")
    parser.add_argument("--show", default="", help="播客名称（用于元数据）")
    parser.add_argument("--episode", default="", help="期数/标题")
    parser.add_argument("--date", default="", help="发布日期")
    parser.add_argument("--cleanup", action="store_true",
                        help="仅整理不翻译（默认翻译模式）")
    parser.add_argument("--podcast-site", action="store_true",
                        help="同步到播客站")
    parser.add_argument("--build", action="store_true", help="构建博客")
    parser.add_argument("--dry-run", action="store_true",
                        help="只显示命令，不运行")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    cmd = [
        sys.executable,
        str(BASE_DIR / "podcast2blog.py"),
        "--transcript", str(input_path),
    ]

    if not args.cleanup:
        cmd.append("--translate")

    if args.podcast_site:
        cmd.append("--podcast-site")

    if not args.build:
        cmd.append("--no-deploy")

    if args.dry_run:
        print(f"📋 将要执行: {' '.join(cmd)}")
        return

    print(f"🚀 处理: {args.input}")
    if args.show or args.episode:
        print(f"   节目: {args.show} · {args.episode}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
