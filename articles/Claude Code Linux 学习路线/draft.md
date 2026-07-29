# Claude Code 学习路线（Linux · 初级 · 快速上手）

> 栏目：Ai技术
> 日期：2026-05-27
> 阅读时间：2
> 标签：Claude，Code，Linux，教程
> 排序：18
> 摘要：了解了你的情况，我来给你一个清晰的学习路线图！第一阶段：安装与配置（先把工具跑起来）前提条件：你需要 Node.js 和 npm# 第一步：配置 npm（避免权限问题）mkdir-p~/.npm-global
npmconfigsetprefix~/.npm-globalecho'export PA


<hr/>
<p>了解了你的情况，我来给你一个清晰的学习路线图！</p>
<h2 id="_1">第一阶段：安装与配置（先把工具跑起来）</h2>
<p><strong>前提条件：</strong> 你需要 Node.js 和 npm</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># 第一步：配置 npm（避免权限问题）</span>
mkdir<span class="w"> </span>-p<span class="w"> </span>~/.npm-global
npm<span class="w"> </span>config<span class="w"> </span><span class="nb">set</span><span class="w"> </span>prefix<span class="w"> </span>~/.npm-global
<span class="nb">echo</span><span class="w"> </span><span class="s1">'export PATH=$HOME/.npm-global/bin:$PATH'</span><span class="w"> </span>&gt;&gt;<span class="w"> </span>~/.bashrc
<span class="nb">source</span><span class="w"> </span>~/.bashrc

<span class="c1"># 第二步：安装 Claude Code</span>
npm<span class="w"> </span>install<span class="w"> </span>-g<span class="w"> </span>@anthropic-ai/claude-code

<span class="c1"># 第三步：验证安装</span>
claude<span class="w"> </span>doctor
</code></pre></div>
<p><strong>账号要求：</strong> 你需要 Claude Pro / Claude Max 订阅，或者开通了计费的 Anthropic Console 账号才能使用。</p>
<p>来源：<a href="https://www.eesel.ai/blog/install-claude-code">Eesel AI</a></p>
<hr/>
<h2 id="_2">第二阶段：基本使用流程</h2>
<p>每次进入你的项目目录，启动 Claude Code：</p>
<div class="codehilite"><pre><span></span><code><span class="nb">cd</span><span class="w"> </span>~/your-project
claude
</code></pre></div>
<p>第一次进入项目时，用 <code>/init</code> 命令让 Claude 生成一个 <code>CLAUDE.md</code> 文件，这个文件会记录你的项目结构和约定，以后每次启动 Claude Code 都会自动读取它，大大提升回答质量。</p>
<p>来源：<a href="https://itecsonline.com/post/how-to-install-claude-code-on-ubuntu-linux-complete-guide-2025">iTechs Online</a></p>
<hr/>
<h2 id="_3">第三阶段：每日必用的斜杠命令</h2>
<p>最常用的日常命令是这几个：</p>
<table>
<thead>
<tr>
<th>命令</th>
<th>用途</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>/init</code></td>
<td>初始化项目，生成 CLAUDE.md</td>
</tr>
<tr>
<td><code>/review</code></td>
<td>让 Claude 审查你的代码</td>
</tr>
<tr>
<td><code>/compact</code></td>
<td>压缩对话上下文（长时间工作必用）</td>
</tr>
<tr>
<td><code>/cost</code></td>
<td>查看本次会话消耗了多少 token</td>
</tr>
<tr>
<td><code>/help</code></td>
<td>列出所有可用命令</td>
</tr>
<tr>
<td><code>/clear</code></td>
<td>清空对话，重新开始</td>
</tr>
</tbody>
</table>
<p>经验丰富的用户每工作 20-30 分钟就会用一次 <code>/compact</code> 来释放上下文空间，防止 Claude 的回答质量下降。</p>
<p>来源：<a href="https://learn-prompting.fr/blog/claude-code-slash-commands-reference">LearnIA</a></p>
<hr/>
<h2 id="_4">第四阶段：日常开发场景示例</h2>
<p>进入对话后，你可以直接用自然语言提问，越具体越好：</p>
<div class="codehilite"><pre><span></span><code>&gt; 解释一下这个项目的目录结构
&gt; 帮我找 user.py 里的 bug
&gt; 帮我给 login 函数写单元测试
&gt; 这段代码怎么优化性能？
</code></pre></div>
<p>每次开始会话时，先定向一下背景：「我们在做什么、相关文件是哪个、成功的标准是什么」，效果会好很多。</p>
<p>来源：<a href="https://dev.to/devdaily_2026/claude-code-the-complete-setup-guide-for-macos-windows-and-linux-3dbl">DEV Community</a></p>
<hr/>
<h2 id="_5">学习建议</h2>
<ol>
<li><strong>先从自己现有的小项目开始</strong>，不要用空项目练习</li>
<li><strong>出问题时运行 <code>claude doctor</code></strong>，它会自动检测大多数配置问题</li>
<li><strong>用 <code>/cost</code> 养成习惯</strong>，了解自己的使用量</li>
</ol>