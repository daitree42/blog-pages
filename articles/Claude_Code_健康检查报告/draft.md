# Claude Code 健康检查报告

> 栏目：ClaudeCode
> 日期：2026-07-28
> 标签：Claude Code，健康检查，性能优化
> 摘要：用 `/doctor` 命令对 Claude Code 做了一次全面的健康检查——清理了 25 个从未使用的 skill、修剪了 CLAUDE.md、将博客工作流迁移到按需加载的 skill、升级到最新版本、开启了自动权限模式。记录过程和结果。

本文记录了在一个实际项目中对 Claude Code 执行 `/doctor` 健康检查的完整过程和结果。

## 什么是 `/doctor`

`/doctor` 是 Claude Code 内置的体检命令，它会检查：

1. **安装健康** — 重复安装、破损的配置文件、冲突的 agent 定义
2. **未使用的扩展** — skill、MCP 服务器、插件中有哪些从未被调用过
3. **CLAUDE.md 去重** — 本地配置与仓库文件之间的矛盾和重复
4. **可推导的内容** — CLAUDE.md 中那些用几条命令就能从代码库获取的信息
5. **延迟加载迁移** — 把常驻内存的内容改为按需加载（skill）
6. **慢钩子** — 配置的 hook 有没有拖慢会话
7. **版本更新** — 是不是最新版
8. **权限模式** — 是否可以用自动模式减少提示
9. **被拒绝的命令** — 频繁被拒绝的只读命令，考虑预批准

## 环境概况

| 项目 | 值 |
|------|-----|
| 原版本 | 2.1.215 |
| 安装方式 | npm global（npm 全局安装） |
| 自动更新 | 已关闭（用户设置） |
| 会话记录窗口 | 8 个会话，覆盖 9 天（Jul 20–28, 2026） |
| 使用统计 | 启动 70 次 |

## 检查结果摘要

整体来说健康状况良好。最大的发现是 **25 个 skill 全部零使用**——它们每次会话都占用了技能列表的上下文空间。

### 发现一：未使用的 skill（25 个）

用户级别的 15 个 skill 全部零使用：agent-reach、brainstorming、coastal-china-history、data-journalism 等。项目级别的 11 个 skill（deep-reader、docx、history-tutor、interview-me、pdf、universal-reader 等）同样零使用。

这些 skill 的 name 和 description 在每次会话中都会加载到上下文中，大约消耗 **350–400 estimator tokens**。

**操作**：在 `.claude/settings.local.json` 中添加 `skillOverrides`，将全部 25 个设为 `"off"`。

### 发现二：CLAUDE.md 修剪

项目根目录的 CLAUDE.md 有 4,867 字节（约 1,217 tokens）。发现两个可以安全移除的章节：

- **项目结构**（~16 行）— 文件树，`ls -R` 即可获得
- **快速开始**（~6 行）— `cd no1; python city_research.py`，读脚本名就知道

**操作**：删除这两节，每次会话节省约 100–125 tokens。

### 发现三：博客工作流迁移到 skill

CLAUDE.md 中的「博客管理」章节包含详细的发布命令——新建文章、播客转录、部署。这些命令只在博客维护时用到，不需要每次会话都加载。

**操作**：将完整命令迁移到 `.claude/skills/blog-workflow/SKILL.md`，CLAUDE.md 中只保留简短引用和 `/blog-workflow` 的提示。节省约 150 tokens/会话。

这也是本篇文章能在这里的原因——我现在通过这个 skill 的指引完成了发布。

### 发现四：版本升级

从 2.1.215 升级到 **2.1.220**（npm registry 上的最新版）。因为 `autoUpdates: false` 禁用了后台自动更新，所以需要手动运行 `npm install -g @anthropic-ai/claude-code@latest`。

### 发现五：自动模式

`permissions.defaultMode` 之前未设置，默认为手动模式（每次工具调用都提示）。现在设置为 `"auto"`——安全分类器会自动批准常规操作（读文件、搜索代码等），只在有风险的操作时才提示。如果模型不支持自动模式，CLI 会自动回退。

### 无需处理的项目

| 检查 | 结果 |
|------|------|
| 本地/仓库去重 | 无本地 CLAUDE.md 文件 |
| 慢钩子 | 无钩子配置或执行记录 |
| 上下文过重 | 正常范围（~3,100 est. tokens） |
| 预批准命令 | 只有 1 次拒绝，是 `pip install`（写操作） |

## 总节省

| 来源 | 节省 tokens/会话 |
|------|:-:|
| 禁用 25 个 skill | ~350–400 |
| 修剪 CLAUDE.md | ~100–125 |
| 博客工作流迁移 skill | ~150 |
| **合计** | **~600–700** |

## 总体评价

Claude Code 的 `/doctor` 命令是一个非常实用的自检工具。这次检查发现的问题集中在「积累的未使用扩展」和「文档优化」上——这是长期使用的自然结果。所有修改都可逆，无破坏性操作。

如果你也在长期使用 Claude Code，建议定期运行 `/doctor` 做一次清理，可以让每次会话的上下文更干净、响应更快。
