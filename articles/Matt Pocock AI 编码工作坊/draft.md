# AI 编码完整工作流：从规划到生产的工程化方法论——Matt Pocock 工作坊实录

> 栏目：Ai技术
> 日期：2026-04-23
> 阅读时间：9
> 排序：27
> 摘要：以下为 Matt Pocock 在 AI Engineer 大会上的工作坊 Full Walkthrough: Workflow for AI Coding from Planning to Production 的完整文字稿中文翻译。开场：软件工程基本功依然是放大器Matt 开场说道：「好，人满了

<div class="post-body">
<hr/>
<p><em>以下为 Matt Pocock 在 AI Engineer 大会上的工作坊 Full Walkthrough: Workflow for AI Coding from Planning to Production 的完整文字稿中文翻译。</em></p>
<hr/>
<h2 id="_1">开场：软件工程基本功依然是放大器</h2>
<p>Matt 开场说道：</p>
<p>「好，人满了，我们开始吧。我是 Matt，一名老师，现在也教 AI。」</p>
<p>他的核心论点是：我们总说 AI 是一个新范式，但在谈论这个新范式时，我们忘记了——<strong>软件工程基本功，那些与人协作至关重要的东西，跟 AI 协作同样有效。</strong> 今天的工作坊就是试图证明这一点。</p>
<p>他先做了一个现场调查：有多少人曾经用 AI 写过代码？——全场举手。每天都用 AI 写代码的？——大部分人举手。曾被 AI 搞得很恼火的？——所有人依然举着手。现场哄堂大笑。</p>
<hr/>
<h2 id="llm">LLM 的「聪明区」与「蠢笨区」</h2>
<p>Matt 引入了 HumanLayer 创始人 Dex Hardy 的一个概念：<strong>LLM 有聪明区（smart zone）和蠢笨区（dumb zone）。</strong></p>
<p>当你刚开始一段新对话时，LLM 从零开始——这时它表现最好。因为注意力关系（attention relationships）的负担最轻。每增加一个 token，注意力关系的数量就像往足球联赛里加球队一样——比赛场次呈二次方增长。</p>
<p>他给出的经验阈值是 <strong>大约 10 万个 token 左右</strong>。超过这个点，LLM 就会「越来越蠢，直到做出非常愚蠢的决策」。</p>
<p>——觉得熟悉的人举手？全场又笑了。</p>
<p>这意味着我们需要把任务控制在聪明区内。这其实是老派的工程建议：Martin Fowler 谈重构、Pragmatic Programmer 都说过——<strong>不要贪多嚼不烂</strong>。保持任务足够小，人脑也不会崩溃。</p>
<p>但怎么处理大任务呢？不能一直堆 token 直到进入蠢笨区再压缩回来，那样效果不好。</p>
<h3 id="ralph-wiggum">多阶段计划与 Ralph Wiggum 循环</h3>
<p>Matt 说他自己以前也用的多阶段计划：把大任务拆成小块，每块都在聪明区完成。</p>
<p>但任何一个靠谱的开发者看到这个模式都会说——<strong>「这是一个循环啊」</strong>。阶段一、阶段二、阶段三、阶段四……为什么不做阶段 N？用一个计划在后台运行，然后不断循环，直到完成。</p>
<p>这就是 <strong>Ralph Wiggum 实践</strong>——本质上只需要指定目标终点（一个 PRD 文档说明要去哪里），然后告诉 AI「做一个小改变，一步步靠近目标」。Ralph 工作得还不错，但 Matt 更喜欢多一点点结构。</p>
<hr/>
<h2 id="llm_1">LLM 像《记忆碎片》的主角</h2>
<p>另一个奇怪的约束：<strong>LLM 就像电影《记忆碎片》的主角</strong>，持续遗忘，每次重置回到初始状态。</p>
<p>他画了一个示意图——每次与 LLM 的会话都经过几个阶段：</p>
<ol>
<li><strong>系统提示（system prompt）</strong>——灰色框，始终在上下文中，要尽量小。如果你在里面塞 25 万个 token，「直接就掉进蠢笨区，什么都做不了」</li>
<li><strong>探索阶段</strong>——AI 编码代理去探索代码库</li>
<li><strong>实现阶段</strong></li>
<li><strong>测试阶段</strong></li>
</ol>
<p>当你清空上下文，就直接回到系统提示——删除了之前的一切。</p>
<h3 id="vs">压缩 vs. 清空</h3>
<p>他介绍了两种策略：</p>
<ul>
<li><strong>压缩（compacting）</strong>：把整个对话历史压成更小的空间，生成一份书面记录</li>
<li><strong>清空（clearing）</strong>：直接回到零状态</li>
</ul>
<p>「开发者不知为何特别喜欢压缩，但我讨厌它。我更喜欢让 AI 像《记忆碎片》里的主角一样——<strong>因为清空后的状态始终一样，如果你能为此优化，你就处在绝佳位置。</strong>」</p>
<p>他说有两个东西需要记住：<strong>LLM 有聪明区和蠢笨区；LLM 像《记忆碎片》的主角。</strong></p>
<hr/>
<h2 id="grill-me">实操演示：Grill Me 技能</h2>
<p>Matt 开始演示第一个练习。</p>
<p>他构建了一个课程管理平台（CMS），今天要在这个平台里实现一个功能——从想法出发，到 PRD，再到最终实现。</p>
<h3 id="grill-me_1">Grill Me 技能</h3>
<p>他使用的第一个技能叫 <strong>「Grill Me」（追问我）</strong>。这个技能非常短小精悍，用来防止与 AI 协作中最大的问题——<strong>需求对齐失败</strong>。</p>
<p>他强烈反对的是所谓的「specs to code」（规范转代码）运动——写一份规范文档，扔给 AI 变成代码。如果代码有问题，不修改代码，而是修改规范，再让 AI 重来。这本质上就是另一种「氛围编程」（vibe coding）——你根本不在乎代码。</p>
<p>「我试过了，真的试过了。<strong>它行不通。</strong> 因为你需要掌控代码。你需要理解代码里有什么。代码是你的战场。」</p>
<h3 id="_2">客户需求</h3>
<p>场景是一个来自「Sarah Chen」的 Slack 消息——不知为什么 Claude 总是选 Sarah Chen 这个名字。消息说：课程平台的留存率不高，学生注册后学了几节课就流失了，想加入游戏化功能。</p>
<h3 id="grill-me_2">Grill Me 如何工作</h3>
<p>Matt 清空上下文，调用 <code>/grill-me</code> 技能，传入客户需求。此时 LLM 只有两个东西：技能定义和需求描述。这也是他每次用 AI 开始工作的方式。</p>
<p>Grill Me 技能的内容极其简短：</p>
<blockquote>
<p>「Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the decision tree resolving dependencies one by one.」</p>
<p>「不停地追问我这个计划的每一个方面，直到我们达成共识。沿着决策树的每个分支逐一解决依赖关系。每个问题都要提供你的推荐答案。」</p>
</blockquote>
<p>他发现与 AI 协作时，AI 总是急切地想直接给出计划。「好的，我觉得够了，砰——计划生成。」但他意识到他想要的不是计划，而是 <strong>共享的理解</strong>。</p>
<p>他引用 Frederick P. Brooks 在《The Design of Design》中的话——设计概念（design concept）是所有参与者之间的一个共享理念。他需要与 AI 达成同频，而不是让 AI 替他输出一份计划。</p>
<h3 id="sub-agent">Sub-Agent（子代理）</h3>
<p>在 AI 提出第一个问题之前，它先调用了一个探索子代理，消耗了约 9.3 万个 Opus token。Matt 解释：「<strong>子代理本质上是一种委派。</strong> 它调用另一个 LLM，后者拥有独立的上下文窗口，探索完所有内容之后，把重要的信息摘要汇报回父代理。」</p>
<h3 id="_3">追问过程</h3>
<p>AI 问的第一个问题：「积分经济——什么行为能赚积分，赚多少？」</p>
<p>Matt 每次都给推荐答案：「保持简单，两种积分来源起步。」</p>
<p>接着的问题越来越深入：积分要追溯吗？现有的课程进度记录有时间戳。这是一个很棘手的问题——是否要回填之前的记录？他让现场举手投票，没有人举手——全场都是骑墙派。</p>
<p>「这种问题你必须有共识，才能好好完成这个功能。Sarah Chen 本人肯定也没想过这个问题。」</p>
<p>一共问了 <strong>22 个问题</strong>——Matt 说这很有代表性。一次 Grill Me 会话可能从 40 到 100 个问题不等，「你可能要坐在那里跟 AI 聊一个小时。」</p>
<h3 id="_4">两个关键文档</h3>
<p>Grill 完成后，Matt 提出了两个关键文件的概念：</p>
<ol>
<li><strong>目的地文档（destination document）</strong>——PRD（产品需求文档），记录最终目标、所有用户故事和完成定义</li>
<li><strong>旅程文档（journey document）</strong>——任务如何拆分</li>
</ol>
<h3 id="prd">写作 PRD</h3>
<p>他调用 <code>write-a-prd</code> 技能。这个技能会：</p>
<ol>
<li>要求用户详细描述问题</li>
<li>安装仓库（如果还没做）</li>
<li>再次追问用户</li>
<li>组装 PRD 模板</li>
</ol>
<p>PRD 包含：问题陈述、解决方案、用户故事列表、实现决策、<strong>测试决策</strong>（关键！）。</p>
<p>他展示了自己的工作仓库，其中包含 <strong>744 个已关闭的 issue</strong>——所有 PRD 和实现任务都在里面。</p>
<h3 id="_5">关于框架选择的观点</h3>
<p>有观众问是否试过 Spec Kit、Open Spec 或其他框架，Matt 的回答很直接：</p>
<blockquote>
<p>「现阶段没有明确的赢家，没有唯一正确的路径，事情在不断变化，<strong>你需要尽可能掌控自己的规划栈</strong>。很多学生过度依赖某一套栈，遇到麻烦的时候因为不拥有这套栈、没有可观测性，只会说『这不行』。而如果你能掌控一切，至少你知道怎么修。」</p>
</blockquote>
<hr/>
<h2 id="vs-afk">人类在环 vs. AFK 任务</h2>
<p>Matt 提出了一个关键区分：</p>
<blockquote>
<p>「我认为 AI 时代有两类任务。<strong>人类在环的任务</strong>——需要人坐在那里做，就是这个阶段。我们是环中的人类，是多个人类在环中。<strong>还有 AFK 任务</strong>——人可以离开键盘，没关系。」</p>
<p><strong>「实现，我们会看到，可以变成 AFK 任务。但规划、对齐阶段，必须是人类在环。必须。」</strong></p>
</blockquote>
<p>为什么不能跳过对齐？有人喊「Ralph loop 这个」。Matt 说：「我不能循环这个。在 AI 的每个阶段，我都会重新评估。这就是为什么我一直在这里回答问题。」</p>
<hr/>
<h2 id="_6">后续流程</h2>
<p>工作坊继续展示了从 PRD 到任务拆分的完整流程：</p>
<ul>
<li><strong>PRD → 看板任务</strong>：将 PRD 拆分成可执行的看板任务，采用 <strong>垂直切片（vertical slicing）和曳光弹开发（tracer bullet development）</strong>，避免 AI 水平编码（做一半停下）</li>
<li><strong>白班/夜班模式</strong>：人类白天规划，AI 夜间自动实现。采用名为 <strong>Ralph 的全自动 Agent 循环</strong></li>
<li><strong>TDD 是关键</strong>：测试驱动开发是从 AI 身上榨取最大价值的关键——红-绿-重构循环</li>
<li><strong>代码审查</strong>：AI 实现完后需要人工 QA，防止产出「渣滓」</li>
<li><strong>深度模块 vs. 浅模块</strong>：复杂隐藏在简洁接口背后的模块设计，对 AI 更友好</li>
</ul>
<h3 id="_7">完整工作流总结</h3>
<blockquote>
<p><strong>想法 → 对齐（Grill Me）→ PRD → 看板 → 实现（Ralph 循环）→ 审查</strong></p>
</blockquote>
<p>Matt 的最终建议：<strong>多读经典软件工程书籍</strong>——他把这称为「一座纯金矿」。</p>
<hr/>
<h2 id="_8">来源</h2>
<blockquote>
<p>原文标题：<em>How I got 30k+ GitHub stars as a nontechnical builder: vibe coding techniques and principles</em></p>
<p>来源视频：Microsoft Developer YouTube 频道 / AI Engineer 大会
文字稿整理：autoem.net</p>
<p>链接：https://youtu.be/jvB2F_hYkXA</p>
</blockquote>
</div>