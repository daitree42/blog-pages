# 播客转录发布完整流水线：从 VTT 到中英对照双站

> 栏目：播客笔记
> 日期：2026-08-03
> 排序：99
> 标签：播客转录，工作流
> 摘要：以 It Could Happen Here 第一季（11 集）为实战，记录播客转录发布到博客+播客站两个站点的完整流水线：VTT 转英文稿、DeepSeek 翻译中文、中英文整理加标题分段、生成中英对照文章并发布，附全部命令、脚本与踩坑经验。

## 概述

本文记录从播客音频（VTT 字幕文件）到发布中英对照文字稿到 **博客 + 播客站** 两个 GitHub Pages 站点的完整流水线，以 It Could Happen Here 第一季（11 集）为实战案例。后续处理新播客时，直接照本文复现。

## 目录结构与脚本

```
C:\cc\blog-pages\podcast\It Could Happen Here\
├── vtt_convert.py      # ① VTT → 英文转录稿（season1/*.md）
├── season1\            # 英文原稿
│   ├── 001.md ~ 011.md
│   ├── 中文\           # ② DeepSeek 翻译的中文稿
│   │   └── 整理版\     # ③ 中文整理稿（# 标题 + 摘要 + ## 小标题 + 分段）
│   └── English\整理版\ # ④ 英文整理稿（# 标题 + Summary + ## 小标题 + 分段）
├── translate_zh.py     # ② 英文 → 中文翻译
├── format_zh.py        # ③ 中文加标题/分段/摘要
├── format_en.py        # ④ 英文加标题/分段/摘要
├── generate_posts.py   # ⑤ 中文整理稿 → 博客文章 + 播客站文稿
└── add_en_versions.py  # ⑥ 英文版生成 + 中英互链 + 交错排序
```

## 关键配置

- **翻译后端**：DeepSeek（`deepseek-chat`），API Key 在 `C:\cc\blog-pages\.env`，脚本自动加载（`load_key()` 读 `.env`），无需手动设环境变量
- **博客**：`C:\cc\blog-pages\`，`publish.py build` 构建，`bash deploy.sh "提交信息"` 部署
- **播客站**：生成器 `C:\Users\张小树\Downloads\podcast-site-generator\podcast-site-src\`，`python build.py` → `public/` → 复制到 `C:\cc\podcast-site\` → git push
- **转写**（如需）：faster-whisper CPU 模式，脚本已固化 `CUDA_VISIBLE_DEVICES=""` + `compute_type="float32"` + 本地缓存 tiny 模型

## 逐步操作

### ① VTT → 英文转录稿

```bash
cd "C:/cc/blog-pages/podcast/It Could Happen Here"
python vtt_convert.py        # season1/*.vtt → season1/*.md
```

要点：cue 合并阈值 `merge_gap=6.0`（太小会断句，如 "through / your window" 被拆开）。输出格式 `**[MM:SS]** **Speaker 1：** 文本`。

### ② 英文 → 中文翻译

```bash
python translate_zh.py                # 全部（跳过已有）
python translate_zh.py --only 001     # 只处理 001
python translate_zh.py --overwrite    # 覆盖已有
```

- 中文版规范（用户指定）：**不要时间戳**、按话题自然分段、说话人标注 `**Speaker 1：**`、只去噪不润色
- 分块翻译 `CHUNK_MAX_CHARS=7000`，超长单段按句子拆分，防截断
- 每批之间 `sleep(1.5)` 降低连接被重置概率

### ③ 中文整理（加标题/分段/摘要）

```bash
python format_zh.py                   # → season1/中文/整理版/*.md
```

DeepSeek 按话题添加 `## 小标题`（≤15 字）、把长段拆成 100-250 字自然段、第一块输出 `摘要：` 行。**忠实保留全部内容**，只加标题分段不删改。

### ④ 英文整理（对照版）

```bash
python format_en.py                   # → season1/English/整理版/*.md
```

与中文整理同一套逻辑，输出 `Summary:` 行 + 英文小标题 + 60-150 词分段。**去掉时间戳**（用户确认），保留 `**Speaker 1：**` 标注。

### ⑤ 生成中文版文章（博客 + 播客站）

```bash
python generate_posts.py
```

- **博客**：`articles/2026-08-03-It_Could_Happen_Here-{EpSlug}/draft.md`
  - `> 栏目：播客笔记`、`> 标签：It Could Happen Here，播客`、`> 排序：1~11`
- **播客站**：`content/it-could-happen-here/{slug}.md`（YAML frontmatter + 纯 Markdown 正文）
- 正文是纯 Markdown（`## 小标题` + 段落），**不要包 `<div class="post-body">`**

### ⑥ 生成英文版 + 中英对照

```bash
python add_en_versions.py
```

一次性完成三件事：
1. **生成英文版**：博客 `{slug}-EN/draft.md` + 播客站 `{slug}-EN.md`，标题 `Episode N · 英文原标题`（标注集数）
2. **交错排列**：中文排序改为奇数（1,3,5…21），英文排序为偶数（2,4,6…22），每集中文后紧跟对应英文版
3. **双向互链**：中文版末尾加「英文原文对照」链接，英文版末尾加「中文翻译」链接

### ⑦ 播客站 show 定义（新播客才需要）

在 `podcast-site-src/data/shows.yaml` 追加：

```yaml
- slug: it-could-happen-here
  name: It Could Happen Here
  desc: ...
  link: https://www.iheart.com/podcast/it-could-happen-here
  language: EN
  category: 叙事故事
  color: "#8e44ad"
```

### ⑧ 构建 + 部署

```bash
# 博客
cd C:/cc/blog-pages
python publish.py build
bash deploy.sh "deploy: 发布 It Could Happen Here 第一季（11集）"

# 播客站
cd C:/Users/张小树/Downloads/podcast-site-generator/podcast-site-src
python build.py
cp -r public/* C:/cc/podcast-site/
cd C:/cc/podcast-site
git add -A && git commit -m "deploy: ..." && git push origin main
```

## 关键经验与坑

1. **DeepSeek 网络不稳定**（ConnectionResetError 10054、DNS 失败）：`call_deepseek` 做 **5 次重试 + 指数退避**（`min(5*2^n, 60)`）+ `requests.Session()` 复用连接 + 单文件 try/except 容错（失败跳过续传）+ 批间 `sleep(1.5)`。偶发失败重跑即可续传。
2. **whisper 幻觉段**：音频末尾音乐/静音被识别成无意义乱码（如 "We could show sleep time..."），DeepSeek 无法自动判断，需人工识别清理（段级删除 + 段内字符串替换）。
3. **VTT 合并阈值**：`merge_gap=6.0`，2.5 会导致句子被拆断。
4. **摘要提取 bug**：正则提取摘要行必须用 `flags=re.M` + `count=1`，否则正文残留摘要行导致重复。
5. **博客正文自动转 HTML**：`publish.py` 判断 Markdown 正文自动用 `md_lib.markdown()` 转 HTML，**无需手动转 HTML 或包 post-body div**。
6. **播客站正文必须纯 Markdown**：包 `<div class="post-body">` 会让 `**说话人：**` 不被解析成 `<strong>`、段落不生成 `<p>`。
7. **中英对照排序**：博客 `position` 字段是整数，同日期内按 position 升序稳定排列，用奇数/偶数实现交错；`publish.py` 先按 position 升序、再按 date 降序（稳定排序保序）。
8. **脚本幂等**：生成脚本检查输出存在即跳过、检查链接 marker 避免重复追加，可安全重跑。
9. **`deploy.sh` 用 `git add -A`**：会把 `podcast/` 下的转换脚本、中文稿源文件也提交进博客仓库作备份（保留即可）。
10. **英文转录稿保留 whisper 原始识别误差**（如 "shipped to do"、"r n C"）——忠实原文不清理，如需可单独去噪。

## 新播客快速复现清单

1. 准备 VTT 字幕到 `season1/`，跑 `vtt_convert.py`
2. `translate_zh.py` 翻译 → `format_zh.py` 整理中文
3. 检查中文稿质量：幻觉段、译文完整性、标题/文件名
4. `generate_posts.py` 生成中文版文章
5. 如需英文对照：`format_en.py` → `add_en_versions.py`
6. `shows.yaml` 加 show 定义（新播客）
7. `publish.py build` + `deploy.sh`（博客）；`build.py` + 复制 + push（播客站）
8. 线上验证：tag 页交错排列、播客站 episode 页、互链可跳转
