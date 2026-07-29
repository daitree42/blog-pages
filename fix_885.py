#!/usr/bin/env python3
"""修复885文章：JSON被当成正文的问题"""
import json, re, sys
from pathlib import Path
import markdown as md_lib

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

draft_path = Path("C:/cc/blog-pages/articles/2026-07-29-This_American_Life-885_Bless_This_Mess/draft.md")
text = draft_path.read_text(encoding="utf-8")

# 提取 post-body
m = re.search(r'<div class="post-body">\s*(.*?)\s*</div>', text, re.DOTALL)
body = m.group(1).strip()
body = re.sub(r'^<p>(.*)</p>$', r'\1', body, flags=re.DOTALL)

# 提取字段
title_m = re.search(r'"title"\s*:\s*"([^"]+)"', body)
summary_m = re.search(r'"summary"\s*:\s*"([^"]+)"', body)
body_md_m = re.search(r'"body_md"\s*:\s*"(.*)"\s*,\s*"#', body, re.DOTALL)

if body_md_m:
    body_md = body_md_m.group(1)
    # 处理转义
    body_md = body_md.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

    title = title_m.group(1) if title_m else "885: Bless This Mess"
    summary = summary_m.group(1) if summary_m else ""

    print(f"标题: {title}")
    print(f"正文: {len(body_md)} 字符")

    # Markdown → HTML
    body_html = md_lib.markdown(body_md, extensions=['fenced_code', 'tables', 'codehilite'])

    # 替换 post-body 内容
    new_text = text.replace(body, body_html)

    # 修复标题
    new_text = re.sub(r'^# .*', f'# {title}', new_text)

    # 修复摘要
    new_text = re.sub(r'> 摘要：.*', f'> 摘要：{summary[:200]}', new_text)

    draft_path.write_text(new_text, encoding="utf-8")
    print("✅ 885 已修复")
else:
    print("❌ 未能提取 body_md")
    # 尝试另一种方法：直接找到 body_md: 之后到 },
    idx = body.find('"body_md"')
    if idx >= 0:
        colon = body.index(':', idx + 9)
        # 找到 body_md 值开头
        q_start = body.index('"', colon + 1)
        # 找匹配的结束引号 - 找最后一个 " 在 }, 前
        end_marker = body.find('"#', q_start + 1)
        if end_marker >= 0:
            # 从 end_marker 往前找真正的结束引号
            raw_val = body[q_start+1:end_marker]
            # 去掉末尾的 \
            raw_val = raw_val.rstrip('\\').rstrip()
            body_md = raw_val.replace('\\n', '\n').replace('\\"', '"')
            print(f"备用方法: {len(body_md)} 字符")

            body_html = md_lib.markdown(body_md, extensions=['fenced_code', 'tables', 'codehilite'])
            new_text = text.replace(body, body_html)
            draft_path.write_text(new_text, encoding="utf-8")
            print("✅ 885 已修复（备用方法）")
        else:
            print("❌ 无法提取 body_md")
