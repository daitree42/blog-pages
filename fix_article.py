#!/usr/bin/env python3
"""Fix article: extract body_md from JSON wrapper using regex"""
import re, sys

path = sys.argv[1]
content = open(path, encoding='utf-8').read()

# Find the JSON in post-body
m = re.search(r'<div class="post-body">(.*?)</div>', content, re.DOTALL)
if not m:
    print("No post-body div")
    sys.exit(0)

inner = m.group(1).strip()

# Extract body_md using regex (it's a JSON string with escaped chars)
bm = re.search(r'"body_md"\s*:\s*"((?:[^"\\]|\\.)*)"', inner, re.DOTALL)
if not bm:
    print("No body_md found via simple regex, trying multiline...")
    # Try multiline JSON string
    bm = re.search(r'"body_md"\s*:\s*"(.*?)(?<!\\)"(\s*[,\n])', inner, re.DOTALL)

if bm:
    body_md = bm.group(1)
    # Unescape JSON escape sequences
    body_md = body_md.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')

    # Extract title
    tm = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', inner)
    title = tm.group(1) if tm else "The Daily"

    # Extract summary
    sm = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', inner, re.DOTALL)
    summary = sm.group(1)[:200] if sm else ""

    # Get transcript section
    ts = re.search(r'(## 📝 原始转录全文.*)', content, re.DOTALL)
    transcript = ts.group(0) if ts else ''

    # Build new content
    new_body = body_md.strip()

    # Replace JSON with actual markdown
    new_content = content.replace(inner, new_body)

    # Update title
    new_content = re.sub(r'^# .*', f'# {title}', new_content)

    # Update summary
    new_content = re.sub(r'(> 摘要：).*', lambda x: x.group(1) + summary[:200], new_content)

    # Ensure transcript is still there
    if transcript and transcript not in new_content:
        new_content = new_content.replace('</div>', transcript + '\n</div>')

    open(path, 'w', encoding='utf-8').write(new_content)
    print(f'Done! Title: {title}')
    print(f'Body: {len(body_md)} chars')
else:
    print("Could not extract body_md")
    print("Inner preview:", inner[:500])
