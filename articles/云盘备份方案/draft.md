# 云盘保存方案总结：从本地到 Dropbox 和 Google Drive

> 栏目：Ai技术
> 日期：2026-05-01
> 阅读时间：6
> 排序：26
> 摘要：一、为什么需要这套方案在终端环境（如 Android Termux、远程服务器）中写作，文件默认只存在本地。一旦设备丢失、数据清理或环境重置，所有稿件都会丢失。建立一套云盘备份机制，可以确保文章安全，也能在多个设备间同步。本文总结两种云盘的连接方式和一个一键同步脚本的使用方法。二、整体架构本地文件 

<div class="post-body">
<hr/>
<h2 id="_1">一、为什么需要这套方案</h2>
<p>在终端环境（如 Android Termux、远程服务器）中写作，文件默认只存在本地。一旦设备丢失、数据清理或环境重置，所有稿件都会丢失。建立一套云盘备份机制，可以确保文章安全，也能在多个设备间同步。</p>
<p>本文总结两种云盘的连接方式和一个一键同步脚本的使用方法。</p>
<hr/>
<h2 id="_2">二、整体架构</h2>
<div class="codehilite"><pre><span></span><code>本地文件                       云盘
─────────────────────────────────────────────
/root/articles/                Dropbox:/Articles/
  ├── out-of-eden-walk/   →    Google Drive:/Articles/
  │   ├── notes/
  │   ├── sources/
  │   ├── outline.md
  │   └── draft.md
  ├── cloud-backup-guide/
  └── ...
</code></pre></div>
<p>通过 rclone 这个统一的命令行工具，同时管理 Dropbox 和 Google Drive 两个云端的文件传输。</p>
<hr/>
<h2 id="rclone">三、前置准备：安装 rclone</h2>
<div class="codehilite"><pre><span></span><code><span class="c1"># Ubuntu/Debian</span>
apt-get<span class="w"> </span>install<span class="w"> </span>-y<span class="w"> </span>rclone

<span class="c1"># 验证安装</span>
rclone<span class="w"> </span>version
</code></pre></div>
<p>rclone 是一个开源的云存储命令行工具，支持 40+ 种云存储服务，包括 Dropbox、Google Drive、OneDrive、Amazon S3 等。</p>
<hr/>
<h2 id="dropbox">四、连接 Dropbox</h2>
<h3 id="41">4.1 原理</h3>
<p>rclone 通过 OAuth 2.0 协议连接 Dropbox。在无图形界面的终端中，rclone 会启动一个本地 Web 服务器（端口 53682），用户需要在浏览器中访问它来完成授权。</p>
<h3 id="42">4.2 操作步骤</h3>
<p><strong>第一步</strong>：运行授权命令</p>
<div class="codehilite"><pre><span></span><code>rclone<span class="w"> </span>authorize<span class="w"> </span><span class="s2">"dropbox"</span>
</code></pre></div>
<p>终端会输出类似：</p>
<div class="codehilite"><pre><span></span><code><span class="n">NOTICE</span><span class="o">:</span><span class="w"> </span><span class="n">If</span><span class="w"> </span><span class="n">your</span><span class="w"> </span><span class="n">browser</span><span class="w"> </span><span class="n">doesn</span><span class="err">'</span><span class="n">t</span><span class="w"> </span><span class="n">open</span><span class="w"> </span><span class="n">automatically</span><span class="w"> </span><span class="n">go</span><span class="w"> </span><span class="n">to</span><span class="w"> </span><span class="n">the</span><span class="w"> </span><span class="n">following</span><span class="w"> </span><span class="n">link</span><span class="o">:</span>
<span class="n">http</span><span class="o">://</span><span class="mf">127.0</span><span class="o">.</span><span class="mf">0.1</span><span class="o">:</span><span class="mi">53682</span><span class="o">/</span><span class="n">auth</span><span class="o">?</span><span class="n">state</span><span class="o">=</span><span class="n">xxxxxxxxxx</span>
<span class="n">NOTICE</span><span class="o">:</span><span class="w"> </span><span class="n">Waiting</span><span class="w"> </span><span class="k">for</span><span class="w"> </span><span class="n">code</span><span class="o">...</span>
</code></pre></div>
<p><strong>第二步</strong>：在手机或电脑的浏览器中打开上述链接。</p>
<p><strong>第三步</strong>：登录 Dropbox 账号，点击"授权"。</p>
<p><strong>第四步</strong>：授权成功后，终端会收到 token。rclone 自动保存配置，或在终端输出 token JSON：</p>
<div class="codehilite"><pre><span></span><code><span class="nx">Paste</span><span class="w"> </span><span class="nx">the</span><span class="w"> </span><span class="nx">following</span><span class="w"> </span><span class="nx">into</span><span class="w"> </span><span class="nx">your</span><span class="w"> </span><span class="nx">remote</span><span class="w"> </span><span class="nx">machine</span><span class="w"> </span><span class="o">---&gt;</span>
<span class="p">{</span><span class="s">"access_token"</span><span class="p">:</span><span class="s">"sl.u.xxx..."</span><span class="p">,</span><span class="s">"token_type"</span><span class="p">:</span><span class="s">"bearer"</span><span class="p">,</span><span class="s">"refresh_token"</span><span class="p">:</span><span class="s">"xxx..."</span><span class="p">,</span><span class="s">"expiry"</span><span class="p">:</span><span class="s">"..."</span><span class="p">}</span>
<span class="p">&lt;</span><span class="o">---</span><span class="nx">End</span><span class="w"> </span><span class="nx">paste</span>
</code></pre></div>
<p><strong>第五步</strong>：验证连接</p>
<div class="codehilite"><pre><span></span><code>rclone<span class="w"> </span>listremotes
<span class="c1"># 应显示：dropbox:</span>

rclone<span class="w"> </span>mkdir<span class="w"> </span>dropbox:/Test
rclone<span class="w"> </span>ls<span class="w"> </span>dropbox:/
</code></pre></div>
<h3 id="43">4.3 配置文件位置</h3>
<p>rclone 的配置文件保存在 <code>~/.config/rclone/rclone.conf</code>，格式如下：</p>
<div class="codehilite"><pre><span></span><code><span class="k">[dropbox]</span>
<span class="na">type</span><span class="w"> </span><span class="o">=</span><span class="w"> </span><span class="s">dropbox</span>
<span class="na">token = {"access_token"</span><span class="o">:</span><span class="s">"sl.u.xxx..."</span><span class="na">,"token_type"</span><span class="o">:</span><span class="s">"bearer"</span><span class="na">,"refresh_token"</span><span class="o">:</span><span class="s">"xxx..."</span><span class="na">,"expiry"</span><span class="o">:</span><span class="s">"..."</span><span class="na">}</span>
</code></pre></div>
<p>这个文件包含 access token 和 refresh token。access token 过期后，rclone 会自动用 refresh token 刷新，无需重新授权。</p>
<hr/>
<h2 id="google-drive">五、连接 Google Drive</h2>
<h3 id="51">5.1 操作步骤</h3>
<p>与 Dropbox 类似，只是把 <code>"dropbox"</code> 换成 <code>"drive"</code>：</p>
<div class="codehilite"><pre><span></span><code>rclone<span class="w"> </span>authorize<span class="w"> </span><span class="s2">"drive"</span>
</code></pre></div>
<p>在浏览器中打开终端输出的 <code>http://127.0.0.1:53682/auth?state=xxx</code>，登录 Google 账号完成授权。</p>
<h3 id="52">5.2 配置示例</h3>
<div class="codehilite"><pre><span></span><code><span class="k">[gdrive]</span>
<span class="na">type</span><span class="w"> </span><span class="o">=</span><span class="w"> </span><span class="s">drive</span>
<span class="na">scope</span><span class="w"> </span><span class="o">=</span><span class="w"> </span><span class="s">drive</span>
<span class="na">token = {"access_token"</span><span class="o">:</span><span class="s">"ya29.xxx..."</span><span class="na">,"token_type"</span><span class="o">:</span><span class="s">"Bearer"</span><span class="na">,"refresh_token"</span><span class="o">:</span><span class="s">"1//xxx..."</span><span class="na">,"expiry"</span><span class="o">:</span><span class="s">"..."</span><span class="na">}</span>
</code></pre></div>
<p><code>scope = drive</code> 表示完整的 Google Drive 文件访问权限。</p>
<h3 id="53">5.3 验证</h3>
<div class="codehilite"><pre><span></span><code>rclone<span class="w"> </span>listremotes
<span class="c1"># 应显示：gdrive:</span>

rclone<span class="w"> </span>mkdir<span class="w"> </span>gdrive:/Test
rclone<span class="w"> </span>ls<span class="w"> </span>gdrive:/
</code></pre></div>
<hr/>
<h2 id="_3">六、注意事项</h2>
<h3 id="61-oauth">6.1 关于 OAuth 授权</h3>
<ul>
<li>每次 <code>rclone authorize</code> 命令都会在 <code>127.0.0.1:53682</code> 启动一个临时 Web 服务器</li>
<li><code>state</code> 参数每次不同，用于 CSRF 防护</li>
<li>授权流程：打开链接 → 跳转至云盘登录页 → 登录并授权 → 跳转回 <code>127.0.0.1:53682</code> → rclone 获取 code → 交换为 token</li>
<li>在手机 Termux 环境中，用同一台手机的浏览器打开 <code>127.0.0.1</code> 链接即可，因为 localhost 指向本机</li>
</ul>
<h3 id="62-token">6.2 Token 类型</h3>
<ul>
<li><strong>Access token</strong>：短期有效（约 4 小时），用于实际 API 调用</li>
<li><strong>Refresh token</strong>：长期有效，用于自动获取新的 access token</li>
<li>rclone 会自动管理 token 刷新，用户无需手动处理</li>
</ul>
<h3 id="63">6.3 安全提醒</h3>
<ul>
<li><code>rclone.conf</code> 包含云盘访问凭证，不要提交到公开仓库</li>
<li>Token 泄露意味着他人可以访问你的云盘文件</li>
<li>如果怀疑 token 泄露，可以在云盘设置中撤销应用授权</li>
</ul>
<hr/>
<h2 id="_4">七、一键同步脚本</h2>
<h3 id="71">7.1 脚本内容</h3>
<p>在 <code>/root/sync-cloud</code> 位置创建了自动同步脚本，内容如下：</p>
<div class="codehilite"><pre><span></span><code><span class="ch">#!/bin/bash</span>
<span class="c1"># 同步 /root/articles/ 到 Dropbox 和 Google Drive</span>

<span class="nb">set</span><span class="w"> </span>-e

<span class="nv">ARTICLES_DIR</span><span class="o">=</span><span class="s2">"/root/articles"</span>
<span class="nv">DROPBOX_DEST</span><span class="o">=</span><span class="s2">"dropbox:/Articles"</span>
<span class="nv">GDRIVE_DEST</span><span class="o">=</span><span class="s2">"gdrive:/Articles"</span>

<span class="nb">echo</span><span class="w"> </span><span class="s2">"===== 开始同步到云盘 ====="</span>

<span class="nb">echo</span><span class="w"> </span><span class="s2">""</span>
<span class="nb">echo</span><span class="w"> </span><span class="s2">"--- Dropbox ---"</span>
<span class="k">if</span><span class="w"> </span>rclone<span class="w"> </span>ls<span class="w"> </span>dropbox:<span class="w"> </span><span class="p">&amp;</span>&gt;/dev/null<span class="p">;</span><span class="w"> </span><span class="k">then</span>
<span class="w">  </span>rclone<span class="w"> </span>sync<span class="w"> </span><span class="s2">"</span><span class="nv">$ARTICLES_DIR</span><span class="s2">"</span><span class="w"> </span><span class="s2">"</span><span class="nv">$DROPBOX_DEST</span><span class="s2">"</span><span class="w"> </span>--progress<span class="w"> </span>--ignore-existing
<span class="w">  </span><span class="nb">echo</span><span class="w"> </span><span class="s2">"[</span><span class="k">$(</span>date<span class="w"> </span><span class="s1">'+%H:%M:%S'</span><span class="k">)</span><span class="s2">] Dropbox 同步完成"</span>
<span class="k">else</span>
<span class="w">  </span><span class="nb">echo</span><span class="w"> </span><span class="s2">"[</span><span class="k">$(</span>date<span class="w"> </span><span class="s1">'+%H:%M:%S'</span><span class="k">)</span><span class="s2">] ⚠️  Dropbox 未配置，跳过"</span>
<span class="k">fi</span>

<span class="nb">echo</span><span class="w"> </span><span class="s2">""</span>
<span class="nb">echo</span><span class="w"> </span><span class="s2">"--- Google Drive ---"</span>
<span class="k">if</span><span class="w"> </span>rclone<span class="w"> </span>ls<span class="w"> </span>gdrive:<span class="w"> </span><span class="p">&amp;</span>&gt;/dev/null<span class="p">;</span><span class="w"> </span><span class="k">then</span>
<span class="w">  </span>rclone<span class="w"> </span>sync<span class="w"> </span><span class="s2">"</span><span class="nv">$ARTICLES_DIR</span><span class="s2">"</span><span class="w"> </span><span class="s2">"</span><span class="nv">$GDRIVE_DEST</span><span class="s2">"</span><span class="w"> </span>--progress<span class="w"> </span>--ignore-existing
<span class="w">  </span><span class="nb">echo</span><span class="w"> </span><span class="s2">"[</span><span class="k">$(</span>date<span class="w"> </span><span class="s1">'+%H:%M:%S'</span><span class="k">)</span><span class="s2">] Google Drive 同步完成"</span>
<span class="k">else</span>
<span class="w">  </span><span class="nb">echo</span><span class="w"> </span><span class="s2">"[</span><span class="k">$(</span>date<span class="w"> </span><span class="s1">'+%H:%M:%S'</span><span class="k">)</span><span class="s2">] ⚠️  Google Drive 未配置，跳过"</span>
<span class="k">fi</span>

<span class="nb">echo</span><span class="w"> </span><span class="s2">""</span>
<span class="nb">echo</span><span class="w"> </span><span class="s2">"===== 同步完成 ====="</span>
<span class="nb">echo</span><span class="w"> </span><span class="s2">"已同步到:"</span>
<span class="nb">echo</span><span class="w"> </span><span class="s2">"  Dropbox     -&gt; </span><span class="nv">$DROPBOX_DEST</span><span class="s2">"</span>
<span class="nb">echo</span><span class="w"> </span><span class="s2">"  Google Drive -&gt; </span><span class="nv">$GDRIVE_DEST</span><span class="s2">"</span>
</code></pre></div>
<h3 id="72">7.2 使用方法</h3>
<div class="codehilite"><pre><span></span><code><span class="c1"># 赋予执行权限（只需要一次）</span>
chmod<span class="w"> </span>+x<span class="w"> </span>/root/sync-cloud

<span class="c1"># 一键同步</span>
./sync-cloud
</code></pre></div>
<h3 id="73">7.3 脚本特性</h3>
<ul>
<li><strong>增量同步</strong>：只上传新增文件，已有文件不受影响（<code>--ignore-existing</code>）</li>
<li><strong>容错处理</strong>：如果某个云盘未配置或 token 过期，脚本会跳过该目标，不会中断</li>
<li><strong>范围明确</strong>：只同步 <code>/root/articles/</code> 目录下的写作内容</li>
</ul>
<h3 id="74">7.4 应用场景</h3>
<ul>
<li>完成一篇文章或笔记后，运行 <code>./sync-cloud</code> 备份</li>
<li>新建选题后运行，确保云盘与本地一致</li>
<li>可以设置 cron 定时任务定期同步（视需求而定）</li>
</ul>
<hr/>
<h2 id="_5">八、文件管理建议</h2>
<h3 id="81">8.1 本地项目结构</h3>
<p>每个选题在 <code>/root/articles/</code> 下独立建目录：</p>
<div class="codehilite"><pre><span></span><code>选题英文slug/
├── outline.md           ← 大纲
├── draft.md             ← 草稿
├── notes/               ← 采访笔记、资料
│   └── research.md
└── sources/             ← 参考来源
    └── links.md
</code></pre></div>
<h3 id="82">8.2 云盘目录结构</h3>
<p>同步到云盘后，目录结构保持与本地一致：</p>
<div class="codehilite"><pre><span></span><code>Articles/
├── out-of-eden-walk/
│   ├── notes/
│   ├── sources/
│   ├── outline.md
│   └── draft.md
├── cloud-backup-guide/
└── ...
</code></pre></div>
<h3 id="83">8.3 后续扩展</h3>
<ul>
<li>如果新增云盘（如 OneDrive），只需用 <code>rclone authorize "onedrive"</code> 配置新的 remote，然后在脚本中增加同步目标</li>
<li>如果想同步更多目录，修改脚本中的 <code>ARTICLES_DIR</code> 和对应的目标路径即可</li>
</ul>
<hr/>
<h2 id="_6">九、常见问题</h2>
<p><strong>Q：rclone authorize 提示端口被占用？</strong>
A：上一次授权进程未退出，等几秒重试即可。端口 53682 是 rclone 的默认 OAuth 回调端口。</p>
<p><strong>Q：Google Drive 提示"应用未验证"？</strong>
A：rclone 使用内置的 OAuth 客户端 ID，Google 可能会显示安全警告。点击"继续"即可，这是已知的开源应用。</p>
<p><strong>Q：token 过期了怎么办？</strong>
A：rclone 会自动使用 refresh token 刷新。如果 refresh token 也失效，只需重新运行 <code>rclone authorize</code>。</p>
<p><strong>Q：如何撤销已授权的应用？</strong>
A：Dropbox：用户设置 → 已连接的应用 → 移除应用。Google Drive：Google 账号 → 安全 → 第三方应用 → 移除。</p>
<p><strong>Q：上传速度慢？</strong>
A：Termux 环境下网速取决于当前网络。小型文本文件通常几秒内完成。</p>
<hr/>
<h2 id="_7">十、总结</h2>
<p>这套方案的核心价值在于：</p>
<ol>
<li><strong>一次配置，长期使用</strong>：OAuth 授权完成后，rclone 自动管理 token 刷新</li>
<li><strong>双云盘冗余</strong>：同时备份到 Dropbox 和 Google Drive，任一平台出问题不影响数据安全</li>
<li><strong>一键操作</strong>：<code>./sync-cloud</code> 完成全部同步，无需分别操作两个云盘</li>
<li><strong>保持结构</strong>：云盘目录结构与本地一致，便于查找和管理</li>
</ol>
<p>对于在终端环境中进行写作的用户来说，这是一个轻量、可靠、免费的云备份方案。</p>
</div>