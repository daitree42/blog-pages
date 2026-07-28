#!/usr/bin/env python3
"""用 DeepSeek API 校对已转录的播客文稿并发布到博客"""

import argparse, json, os, re, subprocess, sys, urllib.request
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR / "articles"

# 复用 process.py 的 LLM 模块
sys.path.insert(0, str(BASE_DIR))
from process import load_env_file, get_llm_provider, _call_llm, build_llm_prompt, parse_llm_response, slugify, generate_article


def main():
    parser = argparse.ArgumentParser(description="DeepSeek 校对播客文稿")
    parser.add_argument("--input", required=True, help="原始转录文本文件")
    parser.add_argument("--show", required=True, help="播客名称")
    parser.add_argument("--episode", required=True, help="期数/标题")
    parser.add_argument("--date", default="", help="发布日期")
    parser.add_argument("--category", default="播客", help="分类")
    parser.add_argument("--tags", default="播客,The Daily,NYT", help="标签")
    parser.add_argument("--link", default="https://www.nytimes.com/the-daily", help="链接")
    parser.add_argument("--build", action="store_true", help="构建博客")
    parser.add_argument("--lang", default="en", help="源语言")
    args = parser.parse_args()

    load_env_file()
    episode_date = args.date or datetime.now().strftime("%Y-%m-%d")
    tags_list = [t.strip() for t in args.tags.replace("，", ",").split(",") if t.strip()]

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    raw_text = input_path.read_text(encoding="utf-8").strip()
    provider = get_llm_provider()

    print(f"\n🎙️  播客文稿整理（{provider}）")
    print(f"   {'='*40}")
    print(f"   节目:   {args.show}")
    print(f"   期数:   {args.episode}")
    print(f"   文本:   {len(raw_text)} 字符")
    print(f"   提供商: {provider}")
    print(f"   语言:   {args.lang}")
    print(f"   {'='*40}\n")

    # 先用几个 segment 构造时间戳参考（build_llm_prompt 需要）
    dummy_segments = [{"start": i*60, "end": (i+1)*60, "text": s}
                      for i, s in enumerate(raw_text.split(". ")[:5]) if s.strip()]

    # 构建提示词 - process.py 的 build_llm_prompt 会处理翻译
    system_prompt, user_prompt = build_llm_prompt(
        raw_text, dummy_segments, args.show, args.episode,
        args.lang, args.link,
    )

    print(f"🤖 调用 {provider} API 整理文稿...")
    preview = raw_text[:150].replace('\n', ' ')
    print(f"   原文预览: {preview}...")

    # 分批处理（process.py 的 process_with_llm 逻辑）
    max_chars = 60000
    response_text = _call_llm(system_prompt, user_prompt)
    result = parse_llm_response(response_text, args.show, args.episode)

    print(f"  ✅ 整理完成")
    print(f"    标题: {result.get('title', '')}")
    print(f"    摘要: {result.get('summary', '')[:100]}...")

    # 生成文章
    from process import generate_article as ga
    draft_path = ga(
        result, args.show, args.episode,
        episode_date, args.category, tags_list,
        args.link, args.lang,
    )

    # 在文章中追加完整原文（保持原文不删减）
    draft_content = draft_path.read_text(encoding="utf-8")
    # 检查是否已包含原文
    if "Original Transcript" not in draft_content:
        transcript_section = (
            f"\n\n## 📝 原始转录全文\n\n"
            f"<details>\n<summary>点击展开完整英文原文</summary>\n\n"
            f"{raw_text}\n\n"
            f"</details>\n"
        )
        # 在 </div> 前插入
        draft_content = draft_content.replace("</div>", transcript_section + "\n</div>")
        draft_path.write_text(draft_content, encoding="utf-8")
        print(f"  ✅ 已追加完整原文")

    # 同步到播客站
    try:
        from podcast_site_utils import save_to_podcast_site
        show_slug = slugify(args.show).lower()
        save_to_podcast_site(draft_path, show_slug, episode_date)
    except Exception as e:
        print(f"  ⚠️  播客站同步跳过: {e}")

    # 构建博客
    if args.build:
        print(f"\n🔨 运行 publish.py build...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "publish.py"), "build"],
            cwd=str(BASE_DIR), capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0 and result.stderr:
            print(f"⚠️  {result.stderr}")

    print(f"\n✅ 全部完成！")
    print(f"   文章: {draft_path}")
    print(f"   预览: cd {BASE_DIR} && python publish.py serve")

if __name__ == "__main__":
    main()
