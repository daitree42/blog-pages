# Claude Code Skills 安装记：从浏览器自动化到元技能

> 栏目：Ai技术
> 日期：2026-06-01
> 阅读时间：6
> 标签：Claude，Code，Skills，教程
> 排序：12
> 摘要：起因用了一段时间 Claude Code，总觉得少了点什么。每次要操作浏览器、搜索现有技能、或者写一篇新报道，都得反复描述上下文。Skills 系统的存在就是为了解决这个——把常用的工作流固化成可复用的命令。于是花了一个下午，一口气装了 11 个技能，覆盖四个方向。方向一：浏览器自动化Claude 

<div class="post-body">
<hr/>
<h2 id="_1">起因</h2>
<p>用了一段时间 Claude Code，总觉得少了点什么。每次要操作浏览器、搜索现有技能、或者写一篇新报道，都得反复描述上下文。Skills 系统的存在就是为了解决这个——把常用的工作流固化成可复用的命令。</p>
<p>于是花了一个下午，一口气装了 11 个技能，覆盖四个方向。</p>
<hr/>
<h2 id="_2">方向一：浏览器自动化</h2>
<p>Claude Code 本身只能处理文本和代码，遇到网页操作就束手无策。两个技能去补这个缺口。</p>
<h3 id="agent-browser">agent-browser</h3>
<div class="codehilite"><pre><span></span><code>npm<span class="w"> </span>install<span class="w"> </span>-g<span class="w"> </span>agent-browser
agent-browser<span class="w"> </span>install<span class="w">    </span><span class="c1"># 下载 Chromium</span>
</code></pre></div>
<p>然后在 Claude Code 里装 skill：</p>
<div class="codehilite"><pre><span></span><code><span class="o">/</span><span class="n">plugin</span><span class="w"> </span><span class="n">marketplace</span><span class="w"> </span><span class="k">add</span><span class="w"> </span><span class="n">OWENLEEzy</span><span class="o">/</span><span class="n">agent</span><span class="o">-</span><span class="n">browser</span><span class="o">-</span><span class="n">skill</span>
<span class="o">/</span><span class="n">plugin</span><span class="w"> </span><span class="n">install</span><span class="w"> </span><span class="n">agent</span><span class="o">-</span><span class="n">browser</span><span class="o">-</span><span class="n">skill</span><span class="nv">@agent</span><span class="o">-</span><span class="n">browser</span><span class="o">-</span><span class="n">skill</span>
</code></pre></div>
<p>它的设计很有意思。不像大多数自动化工具只给你一堆命令，它把整个流程标准化成四个阶段：</p>
<ul>
<li><strong>INTAKE</strong>：逐问澄清目标，一次只问一个问题</li>
<li><strong>PLAN</strong>：给出执行计划，等你确认再动手</li>
<li><strong>EXECUTE</strong>：自动执行，遇到技术失败（元素过期、超时）自动恢复，不打断你</li>
<li><strong>REPORT</strong>：结构化报告，列出步骤结果、问题证据</li>
</ul>
<p>举个例子，你对它说「抓取这篇文章的正文」，它会先问你要保存成什么格式，然后生成打开网页、等待渲染、提取内容、保存文件的计划，确认后自动执行。中间如果元素引用过期，它会重新截图定位，不会停下来等你。</p>
<p>它还内置了七个子技能，由入口 skill 自动路由：</p>
<table>
<thead>
<tr>
<th>内部技能</th>
<th>用途</th>
</tr>
</thead>
<tbody>
<tr>
<td>agent-browser-e2e</td>
<td>E2E 测试</td>
</tr>
<tr>
<td>agent-browser-scrape</td>
<td>数据抓取</td>
</tr>
<tr>
<td>agent-browser-automate</td>
<td>表单自动化</td>
</tr>
<tr>
<td>agent-browser-debug</td>
<td>调试排查</td>
</tr>
<tr>
<td>agent-browser-visual</td>
<td>视觉回归</td>
</tr>
<tr>
<td>agent-browser-ios</td>
<td>iOS 模拟器</td>
</tr>
<tr>
<td>agent-browser-commands</td>
<td>命令参考</td>
</tr>
</tbody>
</table>
<p>你不需要记住这些，入口 <code>/agent-browser</code> 会帮你判断。</p>
<h3 id="web-access">web-access</h3>
<p>这个技能换了一条路。它不启动单独的浏览器实例，而是通过 Chrome DevTools Protocol（CDP）直连你<strong>正在用的 Chrome 浏览器</strong>。</p>
<div class="codehilite"><pre><span></span><code>npx<span class="w"> </span>skills<span class="w"> </span>add<span class="w"> </span>eze-is/web-access
</code></pre></div>
<p>安装后在 Chrome 里打开 <code>chrome://inspect</code>，勾选允许远程调试就行。</p>
<p>优势很直观：你打开的页面、登录的账号、填好的表单，它全能看到。抓取需要登录的网站（微信公众号后台、小红书、微博）时不用反复认证。但也意味着你的浏览器得开着。</p>
<p>它的架构分三层调度：简单搜索走 WebSearch，普通页面抓取走 WebFetch，需要登录或复杂交互的走 CDP。Claude 会根据任务自动选择。</p>
<hr/>
<h2 id="_3">方向二：写作辅助</h2>
<p>作为深度报道写作者，这两个技能是直接服务于写作的。</p>
<h3 id="humanizer-zh">humanizer-zh</h3>
<p>AI 写出来的东西很容易看出来——「此外」「至关重要」「不仅仅……而是……」「标志着」这些词高频出现，段落结构过于规整。<code>humanizer-zh</code> 就是来解决这个的。</p>
<div class="codehilite"><pre><span></span><code>npx<span class="w"> </span>skills<span class="w"> </span>add<span class="w"> </span>https://github.com/op7418/Humanizer-zh.git
</code></pre></div>
<p>它识别 <strong>24 种 AI 写作痕迹</strong>，分成四类：</p>
<ul>
<li><strong>内容模式</strong>：过度强调意义、模糊归因、提纲式的"挑战与展望"</li>
<li><strong>语言语法</strong>：AI 高频词汇（此外、深入探讨）、三段式法则（无缝、直观、强大）</li>
<li><strong>风格模式</strong>：破折号泛滥、表情符号滥用</li>
<li><strong>交流模式</strong>：谄媚语气、「希望这对您有帮助」、知识截止日期免责</li>
</ul>
<p>用法很直接，在 Claude Code 里输入：</p>
<div class="codehilite"><pre><span></span><code>/humanizer-zh 请帮我人性化以下文本：
[粘贴文字]
</code></pre></div>
<p>它会从直接性、节奏、信任度、真实性、精炼度五个维度打分，把 AI 味重的句子改成自然表达。比如「坐落在风景如画的杭州市中心，这家咖啡馆拥有丰富的文化底蕴」会被改成「这家咖啡馆在杭州市中心开了三年，以手冲咖啡和老建筑改造的空间出名」。</p>
<hr/>
<h2 id="_4">方向三：创意与规划</h2>
<h3 id="brainstorming">brainstorming（九步探索法）</h3>
<p>这个技能来自 obra 的 superpowers 项目，核心是一句话：<strong>先想清楚再动手</strong>。</p>
<div class="codehilite"><pre><span></span><code>npx<span class="w"> </span>skills<span class="w"> </span>add<span class="w"> </span>obra/superpowers<span class="w"> </span>--skill<span class="w"> </span>brainstorming
</code></pre></div>
<p>它强制一个九步流程，少一步都通不过：</p>
<table>
<thead>
<tr>
<th>步骤</th>
<th>做什么</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>探索项目上下文——先读你的文件再问问题</td>
</tr>
<tr>
<td>2</td>
<td>如果涉及视觉设计，可选提供视觉辅助</td>
</tr>
<tr>
<td>3</td>
<td>逐一提问澄清——一次只问一个问题</td>
</tr>
<tr>
<td>4</td>
<td>提出 2-3 种方案，附权衡分析和推荐</td>
</tr>
<tr>
<td>5</td>
<td>分段呈现设计，每段等你确认</td>
</tr>
<tr>
<td>6</td>
<td>写设计文档到 <code>docs/</code></td>
</tr>
<tr>
<td>7</td>
<td>自查文档中的 TBD、矛盾、歧义</td>
</tr>
<tr>
<td>8</td>
<td>你审阅文档，可以要求修改或批准</td>
</tr>
<tr>
<td>9</td>
<td>批准后进入执行阶段</td>
</tr>
</tbody>
</table>
<p>听起来很重，但它解决了一个真实问题：AI 太容易跳进执行了。你说了个模糊想法，它就开始写代码，写出来发现理解有偏差。九步法把这个顺序倒过来——先对齐认知，再落地执行。</p>
<hr/>
<h2 id="_5">方向四：技能生态的基础设施</h2>
<p>最后这两个构成技能的「元层」——发现技能和创造技能。</p>
<h3 id="find-skills">find-skills</h3>
<div class="codehilite"><pre><span></span><code>npx<span class="w"> </span>skills<span class="w"> </span>add<span class="w"> </span>vercel-labs/skills@find-skills<span class="w"> </span>-g<span class="w"> </span>-y
</code></pre></div>
<p>在 Claude Code 里直接说「找一个能帮我写测试的技能」，它会搜索 <a href="https://skills.sh/">skills.sh</a> 和 GitHub，评估质量后推荐给你并安装。不用去 GitHub 翻找。</p>
<h3 id="skill-creator">skill-creator</h3>
<p>来自 Anthropic 官方的元技能。</p>
<div class="codehilite"><pre><span></span><code><span class="o">/</span><span class="n">plugin</span><span class="w"> </span><span class="n">marketplace</span><span class="w"> </span><span class="k">add</span><span class="w"> </span><span class="n">anthropics</span><span class="o">/</span><span class="n">skills</span>
<span class="o">/</span><span class="n">plugin</span><span class="w"> </span><span class="n">install</span><span class="w"> </span><span class="n">skill</span><span class="o">-</span><span class="n">creator</span><span class="nv">@anthropics</span><span class="o">/</span><span class="n">skills</span>
</code></pre></div>
<p>输入 <code>/skill-creator</code>，告诉它你想要什么，它会一步步问清楚需求，生成完整的 <code>SKILL.md</code> 文件，写入 <code>~/.claude/skills/</code> 下。如果想给自己的写作流程定制一个「采访笔记整理」技能，半小时就能做出来。</p>
<hr/>
<h2 id="_6">安装方法汇总</h2>
<table>
<thead>
<tr>
<th>技能</th>
<th>安装方式</th>
</tr>
</thead>
<tbody>
<tr>
<td>agent-browser</td>
<td><code>npm install -g agent-browser</code> + <code>/plugin install</code></td>
</tr>
<tr>
<td>web-access</td>
<td><code>npx skills add eze-is/web-access</code></td>
</tr>
<tr>
<td>humanizer-zh</td>
<td><code>npx skills add https://github.com/op7418/Humanizer-zh.git</code></td>
</tr>
<tr>
<td>brainstorming</td>
<td><code>npx skills add obra/superpowers --skill brainstorming</code></td>
</tr>
<tr>
<td>find-skills</td>
<td><code>npx skills add vercel-labs/skills@find-skills -g -y</code></td>
</tr>
<tr>
<td>skill-creator</td>
<td><code>/plugin marketplace add anthropics/skills</code> + <code>/plugin install</code></td>
</tr>
</tbody>
</table>
<hr/>
<h2 id="_7">几点感受</h2>
<p><strong>Skills 的价值不在数量。</strong> 装一堆不用等于没装。今天装的这些，每个对应一个真实场景：写稿 → <code>/humanizer-zh</code>，想选题 → <code>/brainstorming</code>，查资料 → <code>/agent-browser</code>。</p>
<p><strong>元技能的组合效应。</strong> <code>find-skills</code> 发现 + <code>skill-creator</code> 创造，再加上 <code>brainstorming</code> 来设计，这三个配合起来，等于让 Claude Code 具备了扩展自己的能力。</p>
<p><strong>代理协议比语法重要。</strong> 读 <code>agent-browser</code> 的 SKILL.md 时印象很深——它花大量篇幅写协议流程（怎么问问题、怎么恢复、怎么报告），而不是复制 CLI 帮助文档。好的技能是在编码判断力，不只是粘贴命令。</p>
</div>