#!/usr/bin/env python3
"""彻底重写885文章正文：从当前杂乱内容中提取所有文本，重新生成干净的HTML"""
import re, sys
from pathlib import Path
import markdown as md_lib

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

draft_path = Path("C:/cc/blog-pages/articles/2026-07-29-This_American_Life-885_Bless_This_Mess/draft.md")
text = draft_path.read_text(encoding="utf-8")

# 从第一个 <div class="post-body"> 到最后一个 </div> 提取
m_start = text.index('<div class="post-body">')
m_end = text.rindex('</div>') + len('</div>')
body_block = text[m_start:m_end]

# 提取所有纯文本行，忽略HTML标签和JSON语法
inner = re.sub(r'<[^>]+>', '\n', body_block)
inner = re.sub(r'^\s*["\']|["\'],?\s*$', '', inner, flags=re.MULTILINE)
lines = [l.strip() for l in inner.split('\n')]
lines = [l for l in lines if l and l != 'div']
lines = [l for l in lines if l not in ('post-body', 'div class=post-body')]

# 合并 [00:00] 时间戳到上一行末尾
merged = []
for line in lines:
    if re.match(r'^\[\d+:\d+\]', line) and merged:
        merged[-1] += ' ' + line
    elif line.startswith('## ') and merged and not merged[-1].startswith('## '):
        merged.append(line)
    else:
        merged.append(line)

inner = '\n'.join(merged)
inner = re.sub(r'([^\n])\n(## )', r'\1\n\n\2', inner)
inner = inner.strip()

print(f"纯文本: {len(inner)} 字符")
print(f"标题数: {inner.count('## ')}")

# 转为HTML
body_html = md_lib.markdown(inner, extensions=['fenced_code', 'tables', 'codehilite'])
h2_count = body_html.count('<h2>')
print(f"HTML中 <h2> 数量: {h2_count}")

# 替换整个 body_block
new_body_block = f'<div class="post-body">\n{body_html}\n</div>'
new_text = text[:m_start] + new_body_block + text[m_end:]

# 修复嵌套标签
new_text = new_text.replace('<p><h2>', '<h2>').replace('</h2></p>', '</h2>')
new_text = re.sub(r'(</div>)\s*\1+', r'\1', new_text)

draft_path.write_text(new_text, encoding="utf-8")
print("✅ 885 已修复")
