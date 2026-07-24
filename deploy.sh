#!/bin/bash
# deploy.sh — 树 博客部署脚本
# 用法: bash deploy.sh "提交信息"

set -e

cd "$(dirname "$0")"

# 构建
echo "📦 构建站点..."
python publish.py build

# 部署
echo "🚀 部署到 GitHub Pages..."
git add -A

if [ -n "$1" ]; then
    git commit -m "$1"
else
    git commit -m "deploy: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
fi

git push origin main

echo "✅ 部署完成！"
