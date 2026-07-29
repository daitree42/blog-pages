# 沿着海岸线讲历史——一个课程网站从零到一

> 栏目：Ai技术
> 日期：2026-06-13
> 阅读时间：7
> 标签：课程，静态站点，Python，历史，中国
> 排序：8
> 摘要：几个月前开始酝酿一套历史课程——以中国沿海城市为路线，从广州出发，一路向北走到大连，在每一座城市停留，讲一段中国与海洋打交道的故事。目标读者是十五岁以上的青少年，但深度接近大学预科水平。跟常见的通史不一样，这套课程有一个具体的空间线索：沿着海岸线走。广州的鸦片战争、汕头的移民潮、福州的马尾船政、温州


<hr/>
<p>几个月前开始酝酿一套历史课程——以中国沿海城市为路线，从广州出发，一路向北走到大连，在每一座城市停留，讲一段中国与海洋打交道的故事。目标读者是十五岁以上的青少年，但深度接近大学预科水平。</p>
<p>跟常见的通史不一样，这套课程有一个具体的空间线索：<strong>沿着海岸线走</strong>。广州的鸦片战争、汕头的移民潮、福州的马尾船政、温州的民间经济、台州的倭寇、杭州的南宋、上海的租界、连云港的铁路、青岛的殖民规划、天津的北洋、秦皇岛的长城、大连的三国占领史——每个城市都有自己的主题人物和核心问题。</p>
<p>内容攒到差不多十二站一百多章大纲的时候，觉得应该有一个专门的地方来放它。不是扔在博客里当普通文章，而是一个<strong>能让人按顺序走完一趟的沉浸式网站</strong>。</p>
<hr/>
<h2 id="_1">技术选型：继续零依赖路线</h2>
<p>上一次搭博客的时候定了一个原则：不引入框架，不用 node_modules，纯 Python + Markdown + Jinja2 模板，推到 GitHub Pages，目标是十年后回来还能跑。</p>
<p>这次延续这个路线。但课程网站跟博客的需求不一样：</p>
<ul>
<li>博客是扁平的文章列表</li>
<li>课程是<strong>树状结构</strong>：课程 → 城市 → 章节，每个层级都有独立页面</li>
<li>需要一条海岸线作为视觉导航</li>
<li>需要一个能标记写作状态的系统（大纲/草稿/完稿）</li>
</ul>
<p>于是就写了一个新的生成器 <code>build.py</code>。跟博客的 <code>publish.py</code> 共享同一个技术栈——<code>pyyaml</code> 解析前言元数据、<code>markdown</code> 转 HTML、<code>jinja2</code> 渲染模板——但架构完全不同。</p>
<p>博客生成器是<strong>扫描本地读取</strong>：遍历 <code>/articles/</code> 下每个子目录，找到 <code>draft.md</code> 就解析发布。课程生成器是<strong>按配置驱动</strong>：先读 <code>_config.yml</code> 里的城市列表，按顺序加载每个城市下的 <code>_index.md</code> 和编号章节文件，构建一个嵌套的数据结构，再渲染页面。</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># _config.yml（节选）</span>
<span class="nt">cities</span><span class="p">:</span>
<span class="w">  </span><span class="p p-Indicator">-</span><span class="w"> </span><span class="nt">slug</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">guangzhou</span>
<span class="w">    </span><span class="nt">name</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">广州</span>
<span class="w">    </span><span class="nt">order</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">1</span>
<span class="w">  </span><span class="p p-Indicator">-</span><span class="w"> </span><span class="nt">slug</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">shantou</span>
<span class="w">    </span><span class="nt">name</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">汕头</span>
<span class="w">    </span><span class="nt">order</span><span class="p">:</span><span class="w"> </span><span class="l l-Scalar l-Scalar-Plain">2</span>
<span class="w">  </span><span class="c1"># ...一路往北，到大连收尾</span>
</code></pre></div>
<div class="codehilite"><pre><span></span><code><span class="c1"># build.py 的核心逻辑</span>
<span class="k">for</span> <span class="n">city</span> <span class="ow">in</span> <span class="n">cities</span><span class="p">:</span>
    <span class="c1"># 加载城市概览（主题、人物、emoji、坐标）</span>
    <span class="c1"># 加载该城市下所有章节文件</span>
    <span class="c1"># 生成城市页、各章节页</span>
    <span class="c1"># 生成城市间导航链接（上一站/下一站）</span>
</code></pre></div>
<p>单个 <code>build.py</code> 大约 170 行，分布在 <code>_site/</code> 下生成近二百个 HTML 文件。</p>
<h2 id="_2">十二座城市及其坐标</h2>
<p>每个城市在数据里存了一组经纬度，方便以后升级到真实地图。当前版本用的是 SVG 方案 A——一条抽象海岸线弧线串联十二个点，从南到北依次排开。</p>
<p>坐标定了之后，城市间的距离感就出来了：广州和汕头只差一个纬度，但从上海到青岛突然跳了五个纬度。中国的人口重心、经济重心、历史重心，在这条线上不均匀地展开。</p>
<p>点开大连那一站，终章标题是「从广州到大连——沿着海岸线，我们看见了什么」。这个收尾问题是整个课程的出发点，到现在我也没有标准答案。</p>
<h2 id="_3">每章六个空白</h2>
<p>课程设计了一个内容分层结构：每章可以有故事层、年表层、深挖层、思考层、旅行层、推荐读物，六个层次。不是每章都必须全部填满，但结构先行。</p>
<p>所以一百多章 Markdown 文件现在全是这个状态：</p>
<div class="codehilite"><pre><span></span><code>---
title: "虎门销烟——已知场景，陌生问题"
city: "广州"
city_slug: "guangzhou"
chapter: 4
total_chapters: 7
<span class="gu">status: outline</span>
<span class="gu">---</span>

【故事层】空白待写
【年表层】空白待写
【深挖层】空白待写
【思考层】空白待写
【旅行层】空白待写
【推荐读物】空白待写
</code></pre></div>
<p>网站上线后，所有章节页会显示这个空白模板，标注「本章正在撰写中」。状态字段从 <code>outline</code> 改成 <code>draft</code> 再改成 <code>published</code>，对应大纲/草稿/完稿三种显示。</p>
<p>这是一种"先搭骨架后填肉"的策略。骨架先摆在那里，知道自己要填什么、填在哪。事实证明这是对的——如果没有这个框架，我可能会在某个细节里迷失方向，而不是清楚地看到整条海岸线。</p>
<h2 id="github-actions-python">部署：GitHub Actions 跑一个纯 Python 构建</h2>
<p>部署延续零门槛路线。<code>main</code> 分支接收源码，GitHub Actions 检出 → 装两个 Python 包 → <code>python3 build.py</code> → 上传 artifact → 推送到 Pages。</p>
<p>唯一遇到的问题是 GitHub Pages 的子路径。博客部署在 <code>username.github.io/blog-pages/</code>，课程部署在 <code>username.github.io/coastal-history/</code>。静态资源的路径必须带上子路径前缀，否则 CSS 和链接全部 404。</p>
<p>解决方法是解析 <code>_config.yml</code> 里的 <code>base_url</code>，自动提取路径前缀，在模板里用 <code>{{ prefix }}</code> 生成所有 URL：</p>
<div class="codehilite"><pre><span></span><code><span class="kn">from</span><span class="w"> </span><span class="nn">urllib.parse</span><span class="w"> </span><span class="kn">import</span> <span class="n">urlparse</span>
<span class="n">SITE_PREFIX</span> <span class="o">=</span> <span class="n">urlparse</span><span class="p">(</span><span class="n">SITE_URL</span><span class="p">)</span><span class="o">.</span><span class="n">path</span><span class="o">.</span><span class="n">rstrip</span><span class="p">(</span><span class="s2">"/"</span><span class="p">)</span> <span class="ow">or</span> <span class="s2">""</span>
</code></pre></div>
<p>然后在 <code>base.html</code> 里把 <code>&lt;link rel="stylesheet" href="{{ prefix }}/static/style.css"&gt;</code>。这个细节在本地开发时完全不会暴露，只有部署到 Pages 子路径下才会炸。炸了一次之后，所有链接都加上了前缀。</p>
<h2 id="_4">关于写作方法的题外话</h2>
<p>整套大纲——十二座城市、一百多章、每章的主题人物和标题——不是在编辑文档里敲出来的，而是在一个 Claude 自定义 skill 里跟 AI 对话式地、一站一站讨论出来的。</p>
<p>这个过程很有意思。它不是「提需求 → 生成结果」的单向输出，更像是一种协作编辑：我提出城市和主题，AI 根据已有的课程框架生成大纲草案，我再调整方向、补全缺失、串联跨城线索。广州的伍秉鉴和福州的林则徐是同一个人物在两个城市的不同面向，这种呼应是对话中自然长出来的。</p>
<p>Skill 文件里写清楚了课程的原则——优先使用非简体中文来源、呈现史学争议、标注叙事立场、不回避历史暗面。这些原则不是装饰，是写作过程中的真实约束。每次 AI 试图给出一个过于简化的叙述时，原则会把它拉回来：争议题不能跳过，多元视角不能省略。</p>
<p>最后形成了一份将近三百行的 SKILL.md，既是课程大纲，也是一套写作规范。建站的时候，直接把这份大纲解析成 Markdown 文件，变成了网站骨架。</p>
<h2 id="_5">接下来的计划</h2>
<p>网站现在只有骨架。接下来要一章一章写正文——从广州的伍秉鉴开始。汕头需要大量阅读海外华人档案，台州想实地走一趟，大连得补日俄战争的英文文献。保守估计，全部写完至少要一年。</p>
<p>但跟纯写作不一样的是，现在每写完一章，git push 一下，网站上就能看到更新。这种正反馈对长期写作来说很重要。</p>
<p>网站地址：<a href="https://daitree42.github.io/coastal-history/">https://daitree42.github.io/coastal-history/</a></p>
<p>如果也想聊聊历史或者有什么推荐读的书，可以给我发邮件（oytree@gmail.com）或在 GitHub 上开 issue。</p>