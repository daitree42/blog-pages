# 小宇宙播客极速转录工作流

> 栏目：未分类
> 日期：2026-06-22
> 阅读时间：4
> 排序：2
> 摘要：痛点做深度报道经常需要处理播客素材——把一期对话转成文字稿，整理归档，发布到博客。以前这套流程走下来，瓶颈很明显：录屏/下载音频需要手动操作语音转文字用 whisper.cpp small 模型，22 分钟音频要跑40 分钟整个过程缺乏自动化最近用一集 14 分钟的「聊15块钱儿的」做试验，把流程优


<h2 id="_1">痛点</h2>
<p>做深度报道经常需要处理播客素材——把一期对话转成文字稿，整理归档，发布到博客。以前这套流程走下来，瓶颈很明显：</p>
<ul>
<li>录屏/下载音频需要手动操作</li>
<li>语音转文字用 whisper.cpp small 模型，22 分钟音频要跑 <strong>40 分钟</strong></li>
<li>整个过程缺乏自动化</li>
</ul>
<p>最近用一集 14 分钟的「聊15块钱儿的」做试验，把流程优化了一遍，<strong>从拿到链接到部署发布不到 3 分钟</strong>。</p>
<h2 id="_2">流程全景</h2>
<div class="codehilite"><pre><span></span><code>播客链接
    │
    ▼
curl 提取 __NEXT_DATA__ 中的音频 URL
    │
    ├── 并行 ──→ curl 下载 .m4a 音频
    │
    ├── 并行 ──→ curl 下载 whisper 模型（首次）
    │
    ▼
ffmpeg 转码为 16kHz 单声道 WAV
    │
    ▼
whisper-cli tiny 模型转录
    │
    ▼
Python 批量清理同音错字
    │
    ▼
写入文章目录 + deploy.sh 发布
</code></pre></div>
<h2 id="_3">步骤详解</h2>
<h3 id="1">1. 获取音频地址（零等待）</h3>
<p>小宇宙的音频地址藏在页面 <code>__NEXT_DATA__</code> 的 <code>pageProps.episode.enclosure.url</code> 中。以前用 Playwright 渲染页面提取，启动浏览器就要 10 秒。直接用 curl 取即可：</p>
<div class="codehilite"><pre><span></span><code>curl<span class="w"> </span>-s<span class="w"> </span><span class="s2">"https://www.xiaoyuzhoufm.com/episode/&lt;eid&gt;"</span><span class="w"> </span><span class="p">|</span><span class="w"> </span>python3<span class="w"> </span>-c<span class="w"> </span><span class="s2">"</span>
<span class="s2">import sys, json, re</span>
<span class="s2">html = sys.stdin.read()</span>
<span class="s2">m = re.search(r'enclosure.*?url.*?(https:[^"</span><span class="se">\\</span><span class="o">]</span>+<span class="o">)</span><span class="err">'</span>,<span class="w"> </span>html<span class="o">)</span>
<span class="k">if</span><span class="w"> </span>m:<span class="w"> </span>print<span class="o">(</span>m.group<span class="o">(</span><span class="m">1</span><span class="o">))</span>
<span class="s2">"</span>
</code></pre></div>
<p>音频地址格式：<code>https://media.xyzcdn.net/&lt;pid&gt;/&lt;mediaKey&gt;.m4a</code></p>
<h3 id="2">2. 并行下载音频和模型</h3>
<p>音频和模型互不依赖，发起两个后台任务同时下载，互不等待：</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># 后台1：下载音频</span>
curl<span class="w"> </span>-L<span class="w"> </span>-o<span class="w"> </span>/tmp/podcast.m4a<span class="w"> </span><span class="s2">"https://media.xyzcdn.net/..."</span>

<span class="c1"># 后台2：下载 whisper 模型（仅首次需要）</span>
curl<span class="w"> </span>-L<span class="w"> </span>-o<span class="w"> </span>models/ggml-tiny.bin<span class="w"> </span><span class="se">\</span>
<span class="w">  </span><span class="s2">"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"</span>
</code></pre></div>
<p>tiny 模型只有 75MB，下载比 small 模型（460MB）快得多。设备条件允许的话，两块下载可以完全并发。</p>
<h3 id="3">3. 转码</h3>
<p>whisper.cpp 不支持直接输入 m4a，需要用 ffmpeg 转为 16kHz 单声道 WAV：</p>
<div class="codehilite"><pre><span></span><code>ffmpeg<span class="w"> </span>-y<span class="w"> </span>-i<span class="w"> </span>/tmp/podcast.m4a<span class="w"> </span>-ar<span class="w"> </span><span class="m">16000</span><span class="w"> </span>-ac<span class="w"> </span><span class="m">1</span><span class="w"> </span>/tmp/podcast.wav
</code></pre></div>
<p>14 分钟的音源转码约 <strong>4 秒</strong>，ffmpeg 跑在 196x 速度。</p>
<h3 id="4">4. 语音转文字</h3>
<p>核心命令：</p>
<div class="codehilite"><pre><span></span><code>whisper-cli<span class="w"> </span>-m<span class="w"> </span>/root/whisper-models/ggml-tiny.bin<span class="w"> </span><span class="se">\</span>
<span class="w">  </span>-f<span class="w"> </span>/tmp/podcast.wav<span class="w"> </span><span class="se">\</span>
<span class="w">  </span>-l<span class="w"> </span>zh<span class="w"> </span><span class="se">\</span>
<span class="w">  </span>--output-txt<span class="w"> </span><span class="se">\</span>
<span class="w">  </span>-of<span class="w"> </span>/tmp/transcript<span class="w"> </span><span class="se">\</span>
<span class="w">  </span>-np
</code></pre></div>
<p>模型选型对比：</p>
<table>
<thead>
<tr>
<th>模型</th>
<th>大小</th>
<th>14min 转录耗时</th>
<th>中文精度</th>
</tr>
</thead>
<tbody>
<tr>
<td>ggml-tiny</td>
<td>75MB</td>
<td>~1 分钟</td>
<td>可接受，同音错字较多</td>
</tr>
<tr>
<td>ggml-small</td>
<td>460MB</td>
<td>~5-8 分钟</td>
<td>较好，专有名词更准</td>
</tr>
</tbody>
</table>
<h3 id="5">5. 清理文稿</h3>
<p>tiny 模型的中文同音错字比较典型，比如：雄饰→熊市、货木资→霍尔木兹、美连处→美联储。用 Python 批量替换清理，比逐句校对快得多：</p>
<div class="codehilite"><pre><span></span><code><span class="n">fixes</span> <span class="o">=</span> <span class="p">[</span>
    <span class="p">(</span><span class="s2">"雄饰"</span><span class="p">,</span> <span class="s2">"熊市"</span><span class="p">),</span>
    <span class="p">(</span><span class="s2">"货木资"</span><span class="p">,</span> <span class="s2">"霍尔木兹"</span><span class="p">),</span>
    <span class="p">(</span><span class="s2">"美连处"</span><span class="p">,</span> <span class="s2">"美联储"</span><span class="p">),</span>
    <span class="c1"># ... 几十条替换规则</span>
<span class="p">]</span>
<span class="k">for</span> <span class="n">old</span><span class="p">,</span> <span class="n">new</span> <span class="ow">in</span> <span class="n">fixes</span><span class="p">:</span>
    <span class="n">text</span> <span class="o">=</span> <span class="n">text</span><span class="o">.</span><span class="n">replace</span><span class="p">(</span><span class="n">old</span><span class="p">,</span> <span class="n">new</span><span class="p">)</span>
</code></pre></div>
<h3 id="6">6. 发布</h3>
<p>项目使用纯 Python 静态站点生成器，运行部署脚本一键构建并推送到 GitHub Pages：</p>
<div class="codehilite"><pre><span></span><code>bash<span class="w"> </span>/root/blog/deploy.sh
</code></pre></div>
<h2 id="_4">全流程耗时对比</h2>
<table>
<thead>
<tr>
<th>步骤</th>
<th>旧流程（small 模型）</th>
<th>优化流程（tiny 模型）</th>
</tr>
</thead>
<tbody>
<tr>
<td>获取音频</td>
<td>~10s（Playwright）</td>
<td>即时（curl）</td>
</tr>
<tr>
<td>下载音频</td>
<td>~30s</td>
<td>~30s（并行）</td>
</tr>
<tr>
<td>下载模型</td>
<td>~2min（首次）</td>
<td>~30s（并行）</td>
</tr>
<tr>
<td>转码</td>
<td>~5s</td>
<td>~4s</td>
</tr>
<tr>
<td>转录（14min）</td>
<td>~15min</td>
<td>~1min</td>
</tr>
<tr>
<td>清理文稿</td>
<td>~2min 手动</td>
<td>即时（批量替换）</td>
</tr>
<tr>
<td>写入+发布</td>
<td>~10s</td>
<td>~10s</td>
</tr>
<tr>
<td><strong>总计</strong></td>
<td><strong>~18min</strong></td>
<td><strong>~3min</strong></td>
</tr>
</tbody>
</table>
<h2 id="_5">适用场景与局限</h2>
<p><strong>适合</strong>：
- 日常快速存档，获取可检索的文字稿
- 思路梗概和关键引语提取
- 多期播客的批量转录建索引</p>
<p><strong>需注意</strong>：
- tiny 模型对生僻专有名词、英文术语、口音较重者精度下降明显
- 如需对外发布的正式文稿，建议用 small 模型 + 人工校对
- 整个流程依赖命令行环境（curl / ffmpeg / whisper-cli 需预先安装）</p>
<h2 id="_6">源码</h2>
<p>上述流程已整理为项目标准工作流，记录在项目 CLAUDE.md 中。后续可用一句话触发：</p>
<blockquote>
<p>「帮我把这个播客链接转成文字保存并发布」</p>
</blockquote>
<p>即可自动完成采集→转写→清理→发布全流程。</p>