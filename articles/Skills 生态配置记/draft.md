# 给记者建一个工具包：Claude Skills 的安装与配置

> 栏目：日常走走
> 日期：2026-06-03
> 阅读时间：3
> 标签：Claude，Code，skills，工作流，效率工具
> 排序：9
> 摘要：最近花了些时间搭建 Claude Code 的 Skills 生态，整理一下过程，既是备忘，也是给同样做深度报道的朋友一个参考。什么是 SkillsClaude Code 的 Skills 有点像编辑部的工具柜——每个技能是一个专门的能力包，告诉 AI 怎么帮你做特定的事。搜资料、转写录音、核查事实

<div class="post-body">
<p>最近花了些时间搭建 Claude Code 的 Skills 生态，整理一下过程，既是备忘，也是给同样做深度报道的朋友一个参考。</p>
<h2 id="skills">什么是 Skills</h2>
<p>Claude Code 的 Skills 有点像编辑部的工具柜——每个技能是一个专门的能力包，告诉 AI 怎么帮你做特定的事。搜资料、转写录音、核查事实、生成文档……不用每次都从零开始描述需求，直接调用就好。</p>
<p>安装方式很简单：</p>
<div class="codehilite"><pre><span></span><code>npx skills add &lt;仓库名/技能名&gt; -g
</code></pre></div>
<h2 id="_1">装了什么</h2>
<p>最先装的是<strong>微信读书助手</strong>（weread-skills），因为我平时的阅读积累大量在微信读书上。装好之后可以直接搜书、看书架、查阅读统计、拉取笔记划线——写稿时查资料不用切 App。</p>
<p>然后做了个全面审计，看看缺什么。作为记者，最核心的需求是采访、资料、写作、核查这条链。发现新闻相关的技能几乎空白，于是装了一整包。</p>
<h3 id="_2">从新闻技能包拆出来的</h3>
<table>
<thead>
<tr>
<th>技能</th>
<th>做什么</th>
</tr>
</thead>
<tbody>
<tr>
<td>interview-transcription</td>
<td>采访录音转写整理</td>
</tr>
<tr>
<td>interview-prep</td>
<td>采访提纲准备</td>
</tr>
<tr>
<td>fact-check-workflow</td>
<td>事实核查</td>
</tr>
<tr>
<td>source-verification</td>
<td>信源核实</td>
</tr>
<tr>
<td>web-scraping</td>
<td>网页抓取做资料收集</td>
</tr>
<tr>
<td>social-media-intelligence</td>
<td>社交媒体线索挖掘</td>
</tr>
<tr>
<td>data-journalism</td>
<td>数据新闻处理</td>
</tr>
<tr>
<td>story-pitch</td>
<td>选题策划</td>
</tr>
<tr>
<td>editorial-workflow</td>
<td>编辑流程</td>
</tr>
<tr>
<td>foia-requests</td>
<td>信息公开申请</td>
</tr>
</tbody>
</table>
<p>还有几个辅助的：PDF 和 DOCX 文档处理、写作提纲规划（writing-plans）、写作润色（writing-skills）。</p>
<h2 id="_3">工作流能怎么走</h2>
<p>这些技能串起来，一个深度报道的生命周期大致是：</p>
<p><strong>选题阶段</strong>——story-pitch 出选题方案，brainstorming 帮打磨</p>
<p><strong>资料阶段</strong>——weread-skills 查相关书籍，web-scraping 爬公开资料，social-media-intelligence 摸社交媒体讨论</p>
<p><strong>采访阶段</strong>——interview-prep 列提纲，interview-transcription 转写录音</p>
<p><strong>写作阶段</strong>——writing-plans 搭结构，writing-skills + newsroom-style + humanizer-zh 打磨文字</p>
<p><strong>核查阶段</strong>——fact-check-workflow 核查事实，source-verification 验证信源</p>
<p><strong>交付阶段</strong>——docx 出 Word 给编辑</p>
<h2 id="_4">一点感受</h2>
<p>技能的真正价值不是"让 AI 做更多事"，而是<strong>减少语境切换的成本</strong>。</p>
<p>以前查资料要切到微信读书，搜网页要开浏览器，转写录音要开另一个工具——每切一次就断一次思路。现在写稿的时候直接说"帮我搜一下 xx"或者"转写这段录音"，AI 在同一界面里完成，思维不用中断。</p>
<p>当然，这些技能只是工具。一篇好报道的核心永远是人：判断力、叙事感、在现场的理解。但工具如果能让人更专注在核心的事情上，就值得花时间搭。</p>
<h2 id="_5">附：你当前可用的技能清单</h2>
<p>如果在用 Claude Code，可以跑 <code>npx skills add</code> 装需要的能力。目前我个人配置中比较常用的：</p>
<ul>
<li><strong>采前</strong>：interview-prep, story-pitch, brainstorming</li>
<li><strong>采中</strong>：interview-transcription, weread-skills</li>
<li><strong>资料</strong>：deep-research, web-scraping, web-access</li>
<li><strong>核查</strong>：fact-check-workflow, source-verification</li>
<li><strong>写作</strong>：writing-plans, writing-skills, humanizer-zh, newsroom-style</li>
<li><strong>输出</strong>：docx, pdf, publish</li>
</ul>
</div>