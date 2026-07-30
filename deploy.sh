#!/bin/bash
# deploy.sh — 树 博客部署脚本
# 用法: bash deploy.sh "提交信息"

set -e

cd "$(dirname "$0")"

# 构建
echo "📦 构建站点..."
python publish.py build

# 验证构建结果 — 检查首页生成了足够的文章
ARTICLE_COUNT=$(grep -c "article-item" index.html 2>/dev/null || echo 0)
echo "  首页文章数: ${ARTICLE_COUNT}"
if [ "$ARTICLE_COUNT" -lt 3 ]; then
    echo "❌ 首页文章太少 (${ARTICLE_COUNT})，部署中止。请检查发布脚本。"
    exit 1
fi

# 检查是否有未提交的文章变更
UNSTAGED=$(git diff --name-only -- articles/ | head -5)
if [ -n "$UNSTAGED" ]; then
    echo "⚠️  检测到 articles/ 有未暂存的变更:"
    echo "$UNSTAGED" | while IFS= read -r line; do echo "   - $line"; done
fi

# 部署
echo "🚀 部署到 GitHub Pages..."
git add -A

# 检查是否有变更，没有则跳过
if git diff --cached --quiet; then
    echo "ℹ️  没有新变更，跳过提交和推送。"
    exit 0
fi

if [ -n "$1" ]; then
    git commit -m "$1"
else
    git commit -m "deploy: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
fi

echo "⬆️  推送到 origin/main..."
git push origin main

echo ""
echo "✅ 部署完成！"
echo "⏳ 博客将在 1-5 分钟内更新（GitHub Pages CDN 缓存延迟）"
echo "   https://daitree42.github.io/blog-pages/"
