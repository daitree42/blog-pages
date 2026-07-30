#!/usr/bin/env python3
"""
batch_process.py — 批量处理播客音频（委托给 podcast2blog.py）

使用方式:
    # 处理 podcast/ 下所有音频（翻译模式，并行 3 个）
    python batch_process.py

    # 处理指定目录（仅整理，不翻译）
    python batch_process.py --dir ./podcast/已转/ --cleanup

    # 处理并同步到播客站
    python batch_process.py --podcast-site
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DIR = BASE_DIR / "podcast"


def main():
    parser = argparse.ArgumentParser(
        description="批量处理播客音频（委托 podcast2blog.py）",
    )
    parser.add_argument("--dir", default=str(DEFAULT_DIR),
                        help=f"音频目录（默认: {DEFAULT_DIR}）")
    parser.add_argument("--cleanup", action="store_true",
                        help="仅整理不翻译（默认翻译模式）")
    parser.add_argument("--podcast-site", action="store_true",
                        help="同步到播客站")
    parser.add_argument("--workers", type=int, default=3,
                        help="并行数（默认: 3）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只列出要处理的文件，不运行")
    parser.add_argument("--build-only", action="store_true",
                        help="仅构建博客+部署")
    args = parser.parse_args()

    if args.build_only:
        subprocess.run([sys.executable, str(BASE_DIR / "publish.py"), "build"])
        subprocess.run(["git", "add", "-A"], cwd=str(BASE_DIR))
        subprocess.run(["git", "commit", "-m", "deploy: 批量更新", "-q"], cwd=str(BASE_DIR))
        subprocess.run(["git", "push", "origin", "main"], cwd=str(BASE_DIR))
        return

    # 构建命令行
    cmd = [
        sys.executable,
        str(BASE_DIR / "podcast2blog.py"),
        "--batch-dir", args.dir,
        "--max-workers", str(args.workers),
    ]

    if not args.cleanup:
        cmd.append("--translate")  # 默认翻译模式

    if args.podcast_site:
        cmd.append("--podcast-site")

    if args.dry_run:
        print(f"📋 将要执行: {' '.join(cmd)}")
        return

    print(f"🚀 批量处理: {args.dir}")
    print(f"   {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
