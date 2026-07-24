# 给 Claude Code 装上「眼睛」和「云盘」：一次完整的 Agent 工具链配置记录

> 栏目：Ai技术
> 日期：2026-06-15
> 阅读时间：6
> 标签：Claude，Code，Agent-Reach，Exa，rclone，MCP，工具链
> 排序：6
> 摘要：引子Claude Code 是一个强大的终端 AI 编程助手，但它有一个先天局限：它没有眼睛。它无法直接搜索互联网，无法读取 GitHub 仓库的代码，更无法访问你的云盘文件。这篇文章记录了我为 Claude Code 配置完整工具链的过程。装完之后，它既能全网搜索、看 GitHub 代码，也能读写

<div class="post-body">
<hr/>
<h2 id="_1">引子</h2>
<p>Claude Code 是一个强大的终端 AI 编程助手，但它有一个先天局限：<strong>它没有眼睛</strong>。它无法直接搜索互联网，无法读取 GitHub 仓库的代码，更无法访问你的云盘文件。</p>
<p>这篇文章记录了我为 Claude Code 配置完整工具链的过程。装完之后，它既能全网搜索、看 GitHub 代码，也能读写 Google Drive 和 Dropbox 里的文件。整个过程绕过了 npm 环境损坏等若干坑，可以作为同类环境的参考。</p>
<hr/>
<h2 id="agent-reach13">一、Agent-Reach：13 个平台的统一入口</h2>
<p>第一个装的是 <a href="https://github.com/Panniantong/Agent-Reach">Agent-Reach</a>，一个为 AI Agent 提供互联网接入能力的工具层。</p>
<p>它的设计理念很有意思：<strong>不自己实现抓取，而是做选型、安装、体检和路由</strong>。每个平台维护一个「首选 + 备选」后端列表，当首选挂掉时自动切换到备用方案，用户无感知。</p>
<p>安装非常简单，一句话搞定：</p>
<div class="codehilite"><pre><span></span><code>pip<span class="w"> </span>install<span class="w"> </span>https://github.com/Panniantong/agent-reach/archive/main.zip
</code></pre></div>
<p>装完跑 <code>agent-reach doctor</code> 即可查看各渠道状态。我当前有 6 个渠道零配置即用：</p>
<table>
<thead>
<tr>
<th>渠道</th>
<th>状态</th>
</tr>
</thead>
<tbody>
<tr>
<td>YouTube 字幕（yt-dlp）</td>
<td>✅</td>
</tr>
<tr>
<td>任意网页（Jina Reader）</td>
<td>✅</td>
</tr>
<tr>
<td>V2EX 公开 API</td>
<td>✅</td>
</tr>
<tr>
<td>RSS/Atom 订阅</td>
<td>✅</td>
</tr>
<tr>
<td>B站搜索</td>
<td>✅</td>
</tr>
<tr>
<td>小宇宙播客转录</td>
<td>✅</td>
</tr>
</tbody>
</table>
<p>另外两个渠道需要额外配置：Exa 全网搜索和 GitHub CLI，后文详述。</p>
<hr/>
<h2 id="exa">二、Exa 搜索：全网语义搜索</h2>
<p>Exa（原 Metaphor）是一个 AI 搜索引擎，擅长语义搜索而不是关键词匹配。对深度报道的调研来说非常有用——你可以搜「深度报道 非虚构写作 方法」而不是精确的关键词组合。</p>
<p>配置需要两步：拿到 API Key，然后把它存入配置文件。</p>
<p><strong>获取 Key</strong>：在 <a href="https://dashboard.exa.ai/api-keys">Exa Dashboard</a> 注册后即可拿到。</p>
<p><strong>写入配置</strong>：</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># ~/.agent-reach/config.yaml</span>
exa_api_key:<span class="w"> </span>你的key
</code></pre></div>
<p>然后我写了一个命令行工具 <code>exa-search</code>，方便在终端直接调用：</p>
<div class="codehilite"><pre><span></span><code>exa-search<span class="w"> </span><span class="s2">"你想要搜索的内容"</span><span class="w">                  </span><span class="c1"># 基础搜索</span>
exa-search<span class="w"> </span><span class="s2">"芯片 出口管制 2025"</span><span class="w"> </span>--news<span class="w">          </span><span class="c1"># 近30天新闻</span>
exa-search<span class="w"> </span><span class="s2">"小红书 商业模式"</span><span class="w"> </span>--domain<span class="w"> </span>36kr.com<span class="w"> </span>--text<span class="w">  </span><span class="c1"># 限定域名+正文</span>
exa-search<span class="w"> </span><span class="s2">"AI startup funding"</span><span class="w"> </span>-n<span class="w"> </span><span class="m">20</span><span class="w"> </span>--json<span class="w">    </span><span class="c1"># 20条+JSON输出</span>
</code></pre></div>
<p>单次搜索成本约 $0.007，很便宜。用 <code>--json</code> 输出可以方便地喂给后续处理流程。</p>
<hr/>
<h2 id="github-cli">三、GitHub CLI：代码库的大门</h2>
<p>GitHub 是技术调研绕不开的平台。gh CLI 已经预装，但需要认证。</p>
<p><code>agent-reach doctor</code> 给出的提示是：</p>
<div class="codehilite"><pre><span></span><code>[!] GitHub 仓库和代码 — gh CLI 已安装但未认证
</code></pre></div>
<p>认证方式是用 Personal Access Token（PAT）：</p>
<div class="codehilite"><pre><span></span><code><span class="nb">echo</span><span class="w"> </span><span class="s2">"你的github_pat_token"</span><span class="w"> </span><span class="p">|</span><span class="w"> </span>gh<span class="w"> </span>auth<span class="w"> </span>login<span class="w"> </span>--with-token
</code></pre></div>
<p>验证：</p>
<div class="codehilite"><pre><span></span><code>gh<span class="w"> </span>auth<span class="w"> </span>status
<span class="c1"># → Logged in to github.com account yourname</span>
</code></pre></div>
<p>之后就能在 Claude Code 里直接搜索仓库、查看 Issues、读取代码内容了。</p>
<hr/>
<h2 id="rclone-mcp">四、rclone + MCP：云盘文件随时读写</h2>
<p>写作中最大的痛点是文件管理：草稿存在本地 Termux 里，一旦设备清理或丢失就全没了。需要把文章同步到云盘。</p>
<h3 id="rclone">安装 rclone</h3>
<p>rclone 是云存储界的瑞士军刀，支持 40+ 种后端。直接用 apt 装：</p>
<div class="codehilite"><pre><span></span><code>apt<span class="w"> </span>install<span class="w"> </span>rclone
</code></pre></div>
<p>当前版本是 v1.69.2。</p>
<h3 id="_2">配置云盘</h3>
<p><code>rclone config</code> 交互式配置，也可以用已有配置。我目前挂了两个云盘：</p>
<ul>
<li><strong>gdrive</strong> — Google Drive</li>
<li><strong>dropbox</strong> — Dropbox</li>
</ul>
<h3 id="rc">启动 RC 服务</h3>
<p>rclone 提供 Remote Control（RC）模式，通过 HTTP API 调用所有功能：</p>
<div class="codehilite"><pre><span></span><code>rclone<span class="w"> </span>rcd<span class="w"> </span>--rc-no-auth<span class="w"> </span>--rc-addr<span class="w"> </span>localhost:5572<span class="w"> </span><span class="p">&amp;</span>
</code></pre></div>
<p>验证：</p>
<div class="codehilite"><pre><span></span><code>curl<span class="w"> </span>-X<span class="w"> </span>POST<span class="w"> </span>http://localhost:5572/core/version
<span class="c1"># → {"version": "v1.69.2", ...}</span>
curl<span class="w"> </span>-X<span class="w"> </span>POST<span class="w"> </span>-H<span class="w"> </span><span class="s2">"Content-Type: application/json"</span><span class="w"> </span><span class="se">\</span>
<span class="w">  </span>-d<span class="w"> </span><span class="s1">'{"fs": "gdrive:", "remote": "/"}'</span><span class="w"> </span><span class="se">\</span>
<span class="w">  </span>http://localhost:5572/operations/list
<span class="c1"># → {"list": [...]}</span>
</code></pre></div>
<h3 id="mcp">写一个 MCP 服务器</h3>
<p>这里遇到了一个问题。原计划是用 npm 装 <code>rclone-mcp</code>，但 Termux 环境中的 npm 因为 glob 模块损坏完全无法使用。于是我手动写了一个 Python MCP 服务器，通过 rclone 的 RC API 暴露了 6 个工具：</p>
<table>
<thead>
<tr>
<th>MCP 工具</th>
<th>功能</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>rclone_ls</code></td>
<td>浏览云盘目录</td>
</tr>
<tr>
<td><code>rclone_read</code></td>
<td>读取云盘文件内容</td>
</tr>
<tr>
<td><code>rclone_write</code></td>
<td>写入文件到云盘</td>
</tr>
<tr>
<td><code>rclone_copy</code></td>
<td>云盘与本地之间复制</td>
</tr>
<tr>
<td><code>rclone_remotes</code></td>
<td>列出所有云盘</td>
</tr>
<tr>
<td><code>rclone_mount_info</code></td>
<td>查看服务状态</td>
</tr>
</tbody>
</table>
<p>注册到 Claude Code 配置后，重启即可在对话中使用。</p>
<hr/>
<h2 id="_3">五、踩坑记录</h2>
<h3 id="npm">npm 环境损坏</h3>
<div class="codehilite"><pre><span></span><code><span class="n">Error</span><span class="o">:</span><span class="w"> </span><span class="n">Cannot</span><span class="w"> </span><span class="n">find</span><span class="w"> </span><span class="n">module</span><span class="w"> </span><span class="s1">'glob/dist/cjs/src/index.js'</span>
</code></pre></div>
<p>这是本次配置中最大的障碍。npm 依赖 glob 模块，而该模块的路径存在符号链接循环。尝试重装 npm、手动修复 glob 均无效——因为 npm 自己坏了，无法用 npm 修 npm。</p>
<p><strong>解决方案</strong>：放弃 npm/MCP 生态，改用 Python 直连 REST API。对 Exa 搜索，直接调用 <code>api.exa.ai</code> 的 HTTP 接口；对 rclone 云盘操作，利用 rclone 自带的 RC HTTP API 写一个轻量 MCP 代理。</p>
<h3 id="python">多 Python 版本冲突</h3>
<p>系统有 Python 3.14 和 Termux 的 3.13 两套环境。<code>exa-py</code> SDK 装在 3.13 下，但 <code>python3</code> 默认指向 3.14。修复方式是指定 shebang：</p>
<div class="codehilite"><pre><span></span><code><span class="ch">#!/data/data/com.termux/files/usr/bin/python3.13</span>
</code></pre></div>
<h3 id="pydantic-core">pydantic-core 编译失败</h3>
<p>这个包的 Rust 编译依赖在环境里缺失，导致多个 Python 包（包括 MCP SDK、exa-py）安装失败。<strong>终极方案</strong>：避免依赖 pydantic-core 的包，用 requests 直连 API。</p>
<hr/>
<h2 id="_4">六、最终的工具链全景</h2>
<div class="codehilite"><pre><span></span><code>Claude Code
  ├── Agent-Reach       → 13 平台路由 + 体检
  │   ├── Exa 搜索       → 全网语义搜索（REST API）
  │   ├── gh CLI (GitHub) → 代码库访问（已认证）
  │   ├── Jina Reader    → 任意网页内容提取
  │   ├── yt-dlp         → YouTube 字幕
  │   └── ...            → 更多可选渠道
  │
  └── rclone MCP Server  → 云盘文件操作
      ├── Google Drive
      └── Dropbox
</code></pre></div>
<p>可以做的操作：</p>
<div class="codehilite"><pre><span></span><code>「帮我搜一下 AI 芯片出口管制的最新进展」
  → exa-search 搜 → 返回结果摘要

「看看 GitHub 上这个项目有多少 star」
  → gh search repos → 返回项目信息

「把采访稿存到 Dropbox」
  → rclone copy → 文件同步到云盘

「帮我调研一下这个话题，全网搜 + GitHub + 云盘资料」
  → 组合调用 → 综合报告
</code></pre></div>
<hr/>
<h2 id="_5">七、下一步</h2>
<p>还有一些可选渠道可以解锁：</p>
<ul>
<li>Twitter/X — 搜索功能需 Cookie 配置</li>
<li>小红书 — 通过 OpenCLI 或扫码登录</li>
<li>Reddit — 需要登录态</li>
</ul>
<p>如果 npm 能修好，还可以装上完整的 <code>rclone-mcp</code>，获得 55 个内置工具（比我自己写的 Python 版完整得多）。</p>
<hr/>
<p><em>工具是延伸，不是替代。一个好的工具链，应该让自己忘记工具的存在。</em></p>
</div>