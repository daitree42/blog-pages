# CLAUDE.md 是什么

> 栏目：Ai技术
> 日期：2026-05-27
> 阅读时间：3
> 标签：Claude，Code，最佳实践，教程
> 排序：17
> 摘要：好，信息够了，给你一个清晰实用的讲解。CLAUDE.md 是什么CLAUDE.md 是一个特殊文件，Claude 每次开始对话时都会自动读取它。你可以把它理解为给 Claude 的项目说明书——不用每次都重复告诉它背景信息。来源：Claude Code 最佳实践怎么生成进入你的项目目录，运行：cd~


<hr/>
<p>好，信息够了，给你一个清晰实用的讲解。</p>
<h2 id="claudemd">CLAUDE.md 是什么</h2>
<p>CLAUDE.md 是一个特殊文件，Claude 每次开始对话时都会自动读取它。你可以把它理解为<strong>给 Claude 的项目说明书</strong>——不用每次都重复告诉它背景信息。</p>
<p>来源：<a href="https://code.claude.com/docs/en/best-practices">Claude Code 最佳实践</a></p>
<hr/>
<h2 id="_1">怎么生成</h2>
<p>进入你的项目目录，运行：</p>
<div class="codehilite"><pre><span></span><code><span class="nb">cd</span><span class="w"> </span>~/your-project
claude
&gt;<span class="w"> </span>/init
</code></pre></div>
<p><code>/init</code> 会分析你的代码库，自动检测构建系统、测试框架和代码规范，生成一个初始版本。生成后<strong>不要原封不动地用</strong>，需要手动修改精简。</p>
<p>来源：<a href="https://code.claude.com/docs/en/best-practices">Claude Code 最佳实践</a></p>
<hr/>
<h2 id="_2">写什么内容</h2>
<p>格式没有硬性要求，但要保持简短易读。典型内容包括：Bash 命令、代码风格规范、工作流规则——这些是 Claude 光看代码无法推断的信息。</p>
<p>来源：<a href="https://code.claude.com/docs/en/best-practices">Claude Code 最佳实践</a></p>
<p>一个实用的模板：</p>
<div class="codehilite"><pre><span></span><code><span class="gh"># 项目概况</span>
这是一个用 Python + Flask 写的后端 API 项目。

<span class="gh"># 常用命令</span>
<span class="k">-</span><span class="w"> </span>启动开发服务器：`flask run`
<span class="k">-</span><span class="w"> </span>运行测试：`pytest tests/`
<span class="k">-</span><span class="w"> </span>安装依赖：`pip install -r requirements.txt`

<span class="gh"># 代码规范</span>
<span class="k">-</span><span class="w"> </span>用 4 个空格缩进，不用 Tab
<span class="k">-</span><span class="w"> </span>函数和变量名用 snake_case（小写+下划线）
<span class="k">-</span><span class="w"> </span>每个函数都要写注释说明用途

<span class="gh"># 注意事项</span>
<span class="k">-</span><span class="w"> </span>不要直接修改 config.py，配置走环境变量
<span class="k">-</span><span class="w"> </span>数据库迁移文件放在 migrations/ 目录
</code></pre></div>
<hr/>
<h2 id="claudemd_1">写 CLAUDE.md 的关键原则</h2>
<p>对每一行问自己：「没有这行，Claude 会犯错吗？」如果 Claude 本来就做得对，这行就是噪音。大约有 150-200 条指令的预算，超过后遵守率会下降，而系统提示本身已经用掉了约 50 条。</p>
<p>来源：<a href="https://www.builder.io/blog/claude-code-tips-best-practices">Builder.io — Claude Code Tips</a></p>
<p>简单说：<strong>只写 Claude 不知道但必须知道的东西。</strong></p>
<hr/>
<h2 id="claudemd_2">两个位置的 CLAUDE.md</h2>
<table>
<thead>
<tr>
<th>位置</th>
<th>作用</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>~/.claude/CLAUDE.md</code></td>
<td><strong>全局</strong>：对你所有项目生效，写个人偏好</td>
</tr>
<tr>
<td><code>项目根目录/CLAUDE.md</code></td>
<td><strong>项目级</strong>：只对这个项目生效，写项目特定规范</td>
</tr>
</tbody>
</table>
<p>CLAUDE.md 文件可以用 <code>@path/to/file</code> 语法引用其他文件，比如 <code>See @README.md for project overview</code>。</p>
<p>来源：<a href="https://code.claude.com/docs/en/best-practices">Claude Code 最佳实践</a></p>
<hr/>
<h2 id="_3">快速上手建议</h2>
<ol>
<li>先用 <code>/init</code> 生成，然后<strong>删掉你看不懂的行</strong></li>
<li>只保留「启动命令」「代码风格」「特殊注意事项」三类</li>
<li>把 CLAUDE.md 提交到 git，团队共享，这个文件会随时间越来越有价值</li>
</ol>
<p>来源：<a href="https://code.claude.com/docs/en/best-practices">Claude Code 最佳实践</a></p>