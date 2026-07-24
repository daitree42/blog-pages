# blog-pages 站点配置
# 所有可调整的常量集中在此文件

# 站点基本信息
SITE_TITLE = "树"
SITE_TAGLINE = "漫游，一种生活"
SITE_PREFIX = "/blog-pages"
SITE_URL = "https://daitree42.github.io/blog-pages"
AUTHOR_EMAIL = "oytree@gmail.com"
GITHUB_URL = "https://github.com/daitree42"

# 分页：每页文章数
POSTS_PER_PAGE = 5

# 阅读速度估计（中文：字/分钟）
READING_SPEED_ZH = 500

# 分类名 → URL slug 映射
CATEGORY_MAP = {
    "Ai技术": "ai-ji-shu",
    "日常走走": "ri-chang-zou-zou",
    "读书观察": "du-shu-guan-cha",
    "未分类": "uncategorized",
}

# URL slug → 分类名反向映射
CATEGORY_SLUG_MAP = {v: k for k, v in CATEGORY_MAP.items()}

# 分类 → 卡片 emoji
CATEGORY_EMOJI = {
    "Ai技术": "\U0001F4BB",      # 💻
    "日常走走": "\U0001F6B6",    # 🚶
    "读书观察": "\U0001F4D6",    # 📖
    "未分类": "\U0001F4DD",      # 📝
}

# 分类 → 封面渐变配色（亮色模式）
CATEGORY_COLORS_LIGHT = {
    "Ai技术": "linear-gradient(135deg, #e8f0f8 0%, #dce6ef 100%)",
    "日常走走": "linear-gradient(135deg, #e8f5ee 0%, #dceee4 100%)",
    "读书观察": "linear-gradient(135deg, #f5eee4 0%, #efe4d8 100%)",
    "未分类": "linear-gradient(135deg, #f0f0ee 0%, #e8e8e6 100%)",
}

# 分类 → 封面渐变配色（暗色模式）
CATEGORY_COLORS_DARK = {
    "Ai技术": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
    "日常走走": "linear-gradient(135deg, #1a2e1a 0%, #0d1f0d 100%)",
    "读书观察": "linear-gradient(135deg, #2e1a1a 0%, #1f0d0d 100%)",
    "未分类": "linear-gradient(135deg, #2c2c2c 0%, #1a1a1a 100%)",
}
