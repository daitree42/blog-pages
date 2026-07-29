# Claude Code + DeepSeek 完整解决方案文档

> 栏目：Ai技术
> 日期：2026-05-30
> 阅读时间：3
> 标签：Claude，Code，DeepSeek，Termux，Android，教程
> 排序：13
> 摘要：环境说明设备：Android 手机终端：Termux系统：Ubuntu（通过 proot-distro 安装）目标：用 DeepSeek API 驱动 Claude Code第一步：确认运行环境问题：Claude Code 在 Termux 里直接运行报错：Nativebinariesforlinu


<hr/>
<h2 id="_1">环境说明</h2>
<ul>
<li>设备：Android 手机</li>
<li>终端：Termux</li>
<li>系统：Ubuntu（通过 proot-distro 安装）</li>
<li>目标：用 DeepSeek API 驱动 Claude Code</li>
</ul>
<hr/>
<h2 id="_2">第一步：确认运行环境</h2>
<p><strong>问题：</strong> Claude Code 在 Termux 里直接运行报错：</p>
<div class="codehilite"><pre><span></span><code><span class="nv">Native</span><span class="w"> </span><span class="nv">binaries</span><span class="w"> </span><span class="k">for</span><span class="w"> </span><span class="nv">linux</span><span class="o">-</span><span class="nv">arm64</span><span class="o">-</span><span class="nv">android</span><span class="w"> </span><span class="nv">are</span><span class="w"> </span><span class="nv">not</span><span class="w"> </span><span class="nv">available</span>
</code></pre></div>
<p><strong>原因：</strong> Claude Code 官方不支持 Android 原生环境。</p>
<p><strong>解决：</strong> 必须在 Ubuntu 容器里运行：</p>
<div class="codehilite"><pre><span></span><code>pkg<span class="w"> </span>install<span class="w"> </span>proot-distro
proot-distro<span class="w"> </span>install<span class="w"> </span>ubuntu
proot-distro<span class="w"> </span>login<span class="w"> </span>ubuntu
</code></pre></div>
<p>以后每次都先进 Ubuntu：</p>
<div class="codehilite"><pre><span></span><code>proot-distro<span class="w"> </span>login<span class="w"> </span>ubuntu
</code></pre></div>
<hr/>
<h2 id="claude-code-ubuntu">第二步：安装 Claude Code（在 Ubuntu 里）</h2>
<div class="codehilite"><pre><span></span><code><span class="c1"># 安装 Node.js</span>
apt<span class="w"> </span>update<span class="w"> </span><span class="o">&amp;&amp;</span><span class="w"> </span>apt<span class="w"> </span>install<span class="w"> </span>nodejs<span class="w"> </span>npm<span class="w"> </span>-y

<span class="c1"># 安装 Claude Code</span>
npm<span class="w"> </span>install<span class="w"> </span>-g<span class="w"> </span>@anthropic-ai/claude-code

<span class="c1"># 验证</span>
claude<span class="w"> </span>--version
</code></pre></div>
<hr/>
<h2 id="_3">第三步：绕过登录验证</h2>
<p><strong>问题：</strong> Claude Code 要求登录 Anthropic 账号，免费账号不行，需要 Pro（$20/月）。</p>
<p><strong>解决：</strong> 直接修改配置文件伪造登录状态：</p>
<div class="codehilite"><pre><span></span><code>python3<span class="w"> </span><span class="s">&lt;&lt; 'EOF'</span>
<span class="s">import json</span>

<span class="s">with open('/root/.claude.json', 'r') as f:</span>
<span class="s">    config = json.load(f)</span>

<span class="s">config['oauthAccount'] = {</span>
<span class="s">    "accountUuid": "00000000-0000-0000-0000-000000000000",</span>
<span class="s">    "emailAddress": "user@deepseek.local",</span>
<span class="s">    "organizationUuid": "00000000-0000-0000-0000-000000000001",</span>
<span class="s">    "organizationName": "DeepSeek",</span>
<span class="s">    "displayName": "DeepSeek User"</span>
<span class="s">}</span>

<span class="s">with open('/root/.claude.json', 'w') as f:</span>
<span class="s">    json.dump(config, f, indent=2)</span>
<span class="s">print("Done!")</span>
<span class="s">EOF</span>
</code></pre></div>
<hr/>
<h2 id="deepseek">第四步：固定使用 DeepSeek 模型</h2>
<p><strong>问题：</strong> Claude Code 默认用 Opus 4.8，DeepSeek 不认这个模型名。</p>
<p><strong>解决：</strong> 直接写入 settings.json：</p>
<div class="codehilite"><pre><span></span><code><span class="nb">echo</span><span class="w"> </span><span class="s1">'{"hasCompletedOnboarding": true, "model": "deepseek-v4-flash"}'</span><span class="w"> </span>&gt;<span class="w"> </span>~/.claude/settings.json
</code></pre></div>
<hr/>
<h2 id="proxyjs">第五步：创建代理 proxy.js</h2>
<p><strong>问题一：</strong> Claude Code 发送多条 <code>system</code> 消息，DeepSeek 只接受一条，报 400 错误。</p>
<p><strong>问题二：</strong> Claude Code 发送路径是 <code>/v1/messages</code>，但 DeepSeek Anthropic 兼容接口路径是 <code>/anthropic/v1/messages</code>。</p>
<p><strong>解决：</strong> 创建本地代理，同时解决这两个问题：</p>
<div class="codehilite"><pre><span></span><code>cat<span class="w"> </span>&gt;<span class="w"> </span>/root/proxy.js<span class="w"> </span><span class="s">&lt;&lt; 'EOF'</span>
<span class="s">const http = require('http');</span>
<span class="s">const https = require('https');</span>

<span class="s">const PORT = 4000;</span>
<span class="s">const DEEPSEEK_HOST = 'api.deepseek.com';</span>
<span class="s">const DEEPSEEK_KEY = process.env.ANTHROPIC_API_KEY;</span>

<span class="s">const server = http.createServer((req, res) =&gt; {</span>
<span class="s">  let body = '';</span>
<span class="s">  req.on('data', chunk =&gt; body += chunk);</span>
<span class="s">  req.on('end', () =&gt; {</span>
<span class="s">    let payload = body;</span>

<span class="s">    // 修正路径：自动加上 /anthropic 前缀</span>
<span class="s">    let targetPath = '/anthropic' + req.url;</span>

<span class="s">    // 修正多条 system 消息问题</span>
<span class="s">    if (body &amp;&amp; req.url.includes('/messages')) {</span>
<span class="s">      try {</span>
<span class="s">        const parsed = JSON.parse(body);</span>
<span class="s">        if (Array.isArray(parsed.messages)) {</span>
<span class="s">          let sysCount = 0;</span>
<span class="s">          parsed.messages = parsed.messages.map(msg =&gt; {</span>
<span class="s">            if (msg.role === 'system') {</span>
<span class="s">              sysCount++;</span>
<span class="s">              if (sysCount &gt; 1) {</span>
<span class="s">                return { ...msg, role: 'user',</span>
<span class="s">                  content: '[System Note]: ' + msg.content };</span>
<span class="s">              }</span>
<span class="s">            }</span>
<span class="s">            return msg;</span>
<span class="s">          });</span>
<span class="s">          payload = JSON.stringify(parsed);</span>
<span class="s">        }</span>
<span class="s">      } catch (_) {}</span>
<span class="s">    }</span>

<span class="s">    const proxy = https.request({</span>
<span class="s">      hostname: DEEPSEEK_HOST,</span>
<span class="s">      path: targetPath,</span>
<span class="s">      method: req.method,</span>
<span class="s">      headers: {</span>
<span class="s">        ...req.headers,</span>
<span class="s">        host: DEEPSEEK_HOST,</span>
<span class="s">        authorization: 'Bearer ' + DEEPSEEK_KEY,</span>
<span class="s">        'content-length': Buffer.byteLength(payload)</span>
<span class="s">      },</span>
<span class="s">    }, proxyRes =&gt; {</span>
<span class="s">      res.writeHead(proxyRes.statusCode, proxyRes.headers);</span>
<span class="s">      proxyRes.pipe(res);</span>
<span class="s">    });</span>

<span class="s">    proxy.on('error', e =&gt; {</span>
<span class="s">      res.writeHead(502);</span>
<span class="s">      res.end('Bad Gateway: ' + e.message);</span>
<span class="s">    });</span>
<span class="s">    proxy.write(payload);</span>
<span class="s">    proxy.end();</span>
<span class="s">  });</span>
<span class="s">});</span>

<span class="s">server.listen(PORT, () =&gt; console.log('Proxy on port ' + PORT));</span>
<span class="s">EOF</span>
</code></pre></div>
<hr/>
<h2 id="_4">第六步：配置环境变量</h2>
<div class="codehilite"><pre><span></span><code>cat<span class="w"> </span>&gt;<span class="w"> </span>~/.bashrc<span class="w"> </span><span class="s">&lt;&lt; 'EOF'</span>
<span class="s">[ -z "$PS1" ] &amp;&amp; return</span>

<span class="s">export ANTHROPIC_API_KEY="sk-你的完整DeepSeek Key"</span>
<span class="s">export PATH="$HOME/.local/bin:$PATH"</span>

<span class="s">alias ds="pkill -f proxy.js 2&gt;/dev/null; node /root/proxy.js &amp; sleep 1 &amp;&amp; ANTHROPIC_BASE_URL=http://127.0.0.1:4000 claude"</span>
<span class="s">EOF</span>

<span class="nb">source</span><span class="w"> </span>~/.bashrc
</code></pre></div>
<hr/>
<h2 id="_5">日常使用方法</h2>
<p>每次打开手机后：</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># 1. 进入 Ubuntu</span>
proot-distro<span class="w"> </span>login<span class="w"> </span>ubuntu

<span class="c1"># 2. 一条命令启动（用别名）</span>
ds
</code></pre></div>
<p>或者手动：</p>
<div class="codehilite"><pre><span></span><code>pkill<span class="w"> </span>-f<span class="w"> </span>proxy.js<span class="w"> </span><span class="m">2</span>&gt;/dev/null
node<span class="w"> </span>/root/proxy.js<span class="w"> </span><span class="p">&amp;</span>
<span class="nv">ANTHROPIC_BASE_URL</span><span class="o">=</span><span class="s2">"http://127.0.0.1:4000"</span><span class="w"> </span>claude
</code></pre></div>
<hr/>
<h2 id="_6">故障排查速查表</h2>
<table>
<thead>
<tr>
<th>报错</th>
<th>原因</th>
<th>解决</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>cli.js not found</code></td>
<td>在 Termux 直接运行</td>
<td>进 Ubuntu 再运行</td>
</tr>
<tr>
<td><code>Not logged in</code></td>
<td>未登录/免费账号</td>
<td>修改 <code>.claude.json</code> 写入假账号</td>
</tr>
<tr>
<td><code>model not exist</code></td>
<td>模型名错误或未设置</td>
<td>修改 <code>settings.json</code></td>
</tr>
<tr>
<td><code>400 error</code></td>
<td>多条 system 消息</td>
<td>启动 proxy.js</td>
</tr>
<tr>
<td><code>502 Bad Gateway</code></td>
<td>代理未启动或 Key 错误</td>
<td>检查 proxy.js 和 API Key</td>
</tr>
<tr>
<td>代理端口占用 <code>EADDRINUSE</code></td>
<td>旧代理未关闭</td>
<td><code>pkill -f proxy.js</code></td>
</tr>
</tbody>
</table>
<hr/>
<h2 id="_7">核心原理</h2>
<div class="codehilite"><pre><span></span><code>Claude Code → proxy.js (本地4000端口)
                ↓
         修正路径 /v1 → /anthropic/v1
         合并多余 system 消息
         替换 API Key
                ↓
         DeepSeek API
</code></pre></div>
<p>DeepSeek 提供了 Anthropic 兼容接口，但有两处细节差异，proxy.js 就是专门弥补这两处差异的胶水层。</p>