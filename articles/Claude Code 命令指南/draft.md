# Claude Code 斜杠命令完全指南

> 栏目：Ai技术
> 日期：2026-05-26
> 阅读时间：4
> 标签：Claude，Code，命令行工具
> 排序：20
> 摘要：Claude Code 是一个终端里的 AI 编程助手，和 Claude 网页版不同，它在命令行里工作，能直接读写文件、执行命令、管理整个项目。而它的斜杠命令（slash commands）是控制这个工具最直接的方式。之前一直以为 Claude Code 只有 /help 和 /clear 几个简单

<div class="post-body">
<hr/>
<p>Claude Code 是一个终端里的 AI 编程助手，和 Claude 网页版不同，它在命令行里工作，能直接读写文件、执行命令、管理整个项目。而它的斜杠命令（slash commands）是控制这个工具最直接的方式。</p>
<p>之前一直以为 Claude Code 只有 /help 和 /clear 几个简单命令，仔细查了一下，发现内置命令比预想的多不少。</p>
<h2 id="_1">一、内置命令完整列表</h2>
<p>以下十个命令是 Claude Code 自带的：</p>
<table>
<thead>
<tr>
<th>命令</th>
<th>用途</th>
<th>什么时候用</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>/help</code></td>
<td>列出所有可用命令和说明</td>
<td>刚上手，或想查某个命令怎么用</td>
</tr>
<tr>
<td><code>/clear</code></td>
<td>清空当前对话历史</td>
<td>换一个新任务，不想让旧对话干扰</td>
</tr>
<tr>
<td><code>/reset</code></td>
<td>同 /clear</td>
<td>同上</td>
</tr>
<tr>
<td><code>/new</code></td>
<td>同 /clear</td>
<td>同上</td>
</tr>
<tr>
<td><code>/compact</code></td>
<td>压缩上下文，压缩后续中间步骤</td>
<td>会话聊了很久，感觉 Claude 反应变慢时</td>
</tr>
<tr>
<td><code>/context</code></td>
<td>显示当前上下文窗口用量</td>
<td>不确定还能聊多久，提前看看剩余空间</td>
</tr>
<tr>
<td><code>/cost</code></td>
<td>查看本次会话消耗的 token 总量</td>
<td>想知道一次任务花了多少量</td>
</tr>
<tr>
<td><code>/verify</code></td>
<td>验证代码改动是否正确</td>
<td>改完代码后跑一下检查</td>
</tr>
<tr>
<td><code>/bug</code></td>
<td>向 Anthropic 报告 bug</td>
<td>遇到工具本身的 bug</td>
</tr>
<tr>
<td><code>/plan</code></td>
<td>进入计划模式，Claude 先出方案再执行</td>
<td>做比较大的改动前，确认思路</td>
</tr>
<tr>
<td><code>/review</code></td>
<td>代码审查</td>
<td>提交前让别人（或 AI）看看代码</td>
</tr>
<tr>
<td><code>/init</code></td>
<td>初始化项目，生成 CLAUDE.md</td>
<td>开始一个新项目时</td>
</tr>
</tbody>
</table>
<p>值得注意的是，/clear、/reset、/new 三个命令功能完全一样，只是不同习惯的人可以用自己顺手的名字。</p>
<h2 id="markdown">二、自定义命令：用 Markdown 文件扩展能力</h2>
<p>内置命令之外，Claude Code 允许你自己定义命令。做法很简单：在 <code>~/.claude/commands/</code> 目录下放一个 Markdown 文件，文件名就是命令名。</p>
<p>比如创建一个 <code>~/.claude/commands/publish.md</code>，内容写：</p>
<div class="codehilite"><pre><span></span><code># 发布博客

运行构建，然后部署到 GitHub Pages：
cd /root/blog &amp;&amp; python3 publish.py &amp;&amp; bash /root/blog/deploy.sh
</code></pre></div>
<p>之后在 Claude Code 里输入 <code>/publish</code>，Claude 就会读取这个文件并执行你写的指令。文件里可以包含步骤说明、shell 命令、检查清单等。</p>
<p>这意味着你可以把一切重复性的工作流变成一条命令：发布博客、运行测试、部署服务、格式化代码。只要写一次 Markdown 就行。</p>
<h2 id="_2">三、实用组合建议</h2>
<p>几个实际场景中可以搭配使用的命令：</p>
<p>做大改动之前，先跑 <code>/plan</code>。Claude 会先分析项目结构，给出方案，你确认了再动手。避免它直接改代码而方向不对。</p>
<p>改完代码之后跑 <code>/verify</code>，确认改动没有引入新问题。</p>
<p>会话持续了很久、感觉 Claude 反应开始变慢时，用 <code>/compact</code> 压缩上下文。不需要重开对话，中间的状态都保留。</p>
<p>想知道这一轮花了多少 token，随时跑 <code>/cost</code>。</p>
<p>如果手头有几个标准操作（发布、部署、检查），写成自定义命令是最省事的——输入三个字母的事。</p>
<h2 id="_3">四、自定义命令的更多用法</h2>
<p>自定义命令不只是执行脚本。因为 Markdown 文件里可以写自然语言指令，你可以把它当作一个可复用的 prompt 模板。</p>
<div class="codehilite"><pre><span></span><code><span class="gh"># 写周报</span>

请根据本周的 git 提交记录，生成一份周报草稿：
<span class="k">1.</span> 运行 git log --since="7 days ago" --oneline
<span class="k">2.</span> 分类整理提交记录（新功能、修复、重构）
<span class="k">3.</span> 用正式语气写一段工作进展摘要
<span class="k">4.</span> 列出下周计划，留空待填写
</code></pre></div>
<p>输入 <code>/周报</code> 就能生成一份草稿，省去逐条翻提交记录的功夫。</p>
<h2 id="_4">小结</h2>
<p>Claude Code 的斜杠命令系统设计得比较克制——内置命令不多，但覆盖了核心需求。自定义命令的机制才是真正灵活的部分，它把工具的能力边界交到了用户手里。</p>
<p>参考来源：
- <a href="https://clskillshub.com/blog/claude-code-slash-commands-2026">Claude Skills Hub — 2026 Command List</a>
- <a href="https://medium.com/@ekondur/the-complete-guide-to-claude-code-slash-commands-may-2026-48a127aef832">Medium — The Complete Guide to Claude Code Slash Commands</a></p>
</div>