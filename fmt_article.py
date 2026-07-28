#!/usr/bin/env python3
"""Split long paragraphs in Cuba Under Siege article"""
import re

path = r"C:\cc\blog-pages\articles\2026-07-28-The_Daily-Cuba_Under_Siege\draft.md"
content = open(path, encoding="utf-8").read()

# Split post-body content at natural break points
start_marker = '<div class="post-body">\n'
end_marker = '\n---\n'

start_idx = content.find(start_marker) + len(start_marker)
end_idx = content.find(end_marker, start_idx)
body = content[start_idx:end_idx].strip()

# Break at these Chinese transition markers
break_patterns = [
    r'(Gustavo Torres Armis 25岁)',  # Introduction of person
    r'(我们本可以谈论很多事情)',  # Topic shift
    r'(你大概多久会有一天醒来没有水)',  # Question shift
    r'(你上车的时候这些公交车挤吗)',  # Topic shift
    r'(你注意到一件事)',  # Topic shift
    r'(接着讲我每天的经历)',  # Topic shift
    r'(当你回到家，通常是什么样子)',  # Topic shift
    r'(你们会谈论这场危机)',  # Topic shift
    r'(你会把自己放在哪里)',  # Topic shift
    r'(周一，古巴)',  # Time shift
    r'(以下是您今天需要)',  # Section shift
    r'(今天的节目)',  # Credits
    r'(所以，回家，那是困难的部分)',  # Section shift
]

result = body
for pattern in break_patterns:
    result = re.sub(pattern, r'\n\n\1', result)

# Insert blank line before ad break
result = result.replace('我们马上回来。', '我们马上回来。\n')
result = result.replace('嗨，我是 Ashley。', '\n嗨，我是 Ashley。')

# Remove excessive blank lines (3+ → 2)
result = re.sub(r'\n{3,}', '\n\n', result)

new_body = start_marker + '\n' + result.strip() + '\n\n' + end_marker
new_content = content[:start_idx - len(start_marker)] + new_body + content[end_idx + len(end_marker):]

open(path, 'w', encoding='utf-8').write(new_content)

import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
old_paras = body.count('\n\n')
new_paras = result.count('\n\n')
print(f"OK 段落从 {old_paras} -> {new_paras} 段")
print(f"   {path}")
