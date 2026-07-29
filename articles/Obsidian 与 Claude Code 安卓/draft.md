# 在同一台 Android 手机上打通 Obsidian 和 Claude Code

> 栏目：未分类
> 日期：2026-06-16
> 阅读时间：7
> 排序：4
> 摘要：记者的工作流里有一件事是确定的——笔记在哪里写，文章最终也在哪里写。但当笔记用 Obsidian、写作用 Claude Code，两者又都在同一台 Android 手机上时，中间需要一座桥。这篇文章记录的就是这座桥怎么搭起来的。两个工具，一台手机Obsidian 是移动端最好的笔记工具之一：本地存储


<p>记者的工作流里有一件事是确定的——笔记在哪里写，文章最终也在哪里写。但当笔记用 Obsidian、写作用 Claude Code，两者又都在同一台 Android 手机上时，中间需要一座桥。</p>
<p>这篇文章记录的就是这座桥怎么搭起来的。</p>
<h2 id="_1">两个工具，一台手机</h2>
<p>Obsidian 是移动端最好的笔记工具之一：本地存储、双向链接、Markdown 原生支持。Claude Code 则是命令行里的 AI 编程助手——但它能做的事情远不限于写代码：写深度报道、梳理采访笔记、润色段落，它都胜任。</p>
<p>问题在于，Obsidian 在 Android 的图形界面里运行，Claude Code 在 Termux 的命令行里运行。Android 从 11 版本开始引入了 Scoped Storage 机制，每个应用只能访问自己的沙盒目录，不能随意读写手机的共享存储——至少在默认情况下不行。</p>
<p>要让两个工具读写同一份文件，需要理解这层限制，然后绕过它。</p>
<h2 id="_2">环境概览</h2>
<p>先列出整个链条上的组件：</p>
<ul>
<li><strong>手机</strong>：Android 系统</li>
<li><strong>终端模拟器</strong>：Termux，Android 上最成熟的 Linux 环境</li>
<li><strong>Linux 发行版</strong>：PRoot Distro（在 Termux 之上运行一个完整的 Linux 发行版）</li>
<li><strong>笔记工具</strong>：Obsidian Android 版</li>
<li><strong>写作工具</strong>：Claude Code，运行在 Termux 的 PRoot Distro 里</li>
</ul>
<p>PRoot Distro 是一个容器方案，它在不 root 手机的前提下，让 Termux 里能跑一个完整的 Linux 环境（比如 Ubuntu）。Claude Code 只能运行在完整 Linux 环境里，所以必须在 PRoot Distro 中启动。而这个容器有自己的文件系统，默认看不到 Android 共享存储里的文件。</p>
<h2 id="termux-setup-storage">第一步：termux-setup-storage</h2>
<p>Termux 提供了一个工具叫 <code>termux-setup-storage</code>。在 Termux 本体中运行一次，会在 Termux 主目录下创建 <code>~/storage/</code> 文件夹，里面是一系列符号链接：</p>
<div class="codehilite"><pre><span></span><code><span class="n">storage</span><span class="o">/</span>
<span class="err">├──</span><span class="w"> </span><span class="n">shared</span><span class="w"> </span><span class="o">-&gt;</span><span class="w"> </span><span class="o">/</span><span class="n">storage</span><span class="o">/</span><span class="n">emulated</span><span class="o">/</span><span class="mi">0</span>
<span class="err">├──</span><span class="w"> </span><span class="n">documents</span><span class="w"> </span><span class="o">-&gt;</span><span class="w"> </span><span class="o">/</span><span class="n">storage</span><span class="o">/</span><span class="n">emulated</span><span class="o">/</span><span class="mi">0</span><span class="o">/</span><span class="n">Documents</span>
<span class="err">├──</span><span class="w"> </span><span class="n">downloads</span><span class="w"> </span><span class="o">-&gt;</span><span class="w"> </span><span class="o">/</span><span class="n">storage</span><span class="o">/</span><span class="n">emulated</span><span class="o">/</span><span class="mi">0</span><span class="o">/</span><span class="n">Download</span>
<span class="err">├──</span><span class="w"> </span><span class="n">dcim</span><span class="w"> </span><span class="o">-&gt;</span><span class="w"> </span><span class="o">/</span><span class="n">storage</span><span class="o">/</span><span class="n">emulated</span><span class="o">/</span><span class="mi">0</span><span class="o">/</span><span class="n">DCIM</span>
<span class="err">├──</span><span class="w"> </span><span class="n">pictures</span><span class="w"> </span><span class="o">-&gt;</span><span class="w"> </span><span class="o">/</span><span class="n">storage</span><span class="o">/</span><span class="n">emulated</span><span class="o">/</span><span class="mi">0</span><span class="o">/</span><span class="n">Pictures</span>
<span class="err">└──</span><span class="w"> </span><span class="o">...</span>
</code></pre></div>
<p>这个命令授权 Termux 读取 Android 的共享存储。<code>/storage/emulated/0/</code> 是所有 Android 应用共享的存储区域——Obsidian 的笔记文件也保存在这里。</p>
<p>但在 PRoot Distro 容器内，<code>/data/data/com.termux/files/home/storage/</code> 这个路径不直接可见。好在容器能访问外部的 <code>/storage/emulated/0/</code> 路径，这是 Android 系统层面的挂载点，不会被容器隔离。</p>
<h2 id="obsidian-vault">第二步：找到 Obsidian 的 vault</h2>
<p>在 Obsidian 里新建 vault 时，可以选择保存位置。为了让 Claude Code 也能访问到，把 vault 建在共享存储下：</p>
<div class="codehilite"><pre><span></span><code>/storage/emulated/0/Documents/obsidian/Claude/
</code></pre></div>
<p>这个路径从 PRoot Distro 容器内可以直接访问。验证方法很简单——在 Termux 里用 <code>cat</code> 读一个 Obsidian 里写的笔记，如果内容正确显示，说明连通了。</p>
<h2 id="_3">第三步：符号链接打通工作目录</h2>
<p>Claude Code 的工作目录按照项目规范设在 <code>/root/articles/</code>。但这个路径在 PRoot Distro 容器内部，Obsidian 看不到。</p>
<p>解决方法是在容器里创建一个软链接，把 <code>/root/articles/</code> 指向 Obsidian vault 里的 <code>articles/</code> 文件夹：</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># 在 Termux 主目录建一个 vault 的快捷方式</span>
ln<span class="w"> </span>-sf<span class="w"> </span>/storage/emulated/0/Documents/obsidian/Claude<span class="w"> </span>~/obsidian-vault

<span class="c1"># 在 vault 里建 articles 文件夹</span>
mkdir<span class="w"> </span>-p<span class="w"> </span>~/obsidian-vault/articles

<span class="c1"># 把已有的文章目录指向这个文件夹</span>
mv<span class="w"> </span>/root/articles<span class="w"> </span>/root/articles.bak
ln<span class="w"> </span>-sf<span class="w"> </span>~/obsidian-vault/articles<span class="w"> </span>/root/articles
</code></pre></div>
<p>做好之后，效果是这样的：</p>
<div class="codehilite"><pre><span></span><code>手机 Obsidian                        Termux (PRoot Distro)
       │                                   │
       ▼                                   ▼
/storage/emulated/0/                /root/articles
  Documents/                              │
    obsidian/                              │ (软链接)
      Claude/                              │
        articles/ ◄───────────────────────┘
</code></pre></div>
<p>如果之前已经有文章，把它们复制到 <code>articles/</code> 目录下。我迁移的时候有 25 个选题，全部保留。</p>
<h2 id="_4">工作流：一次打通，三端协同</h2>
<p>打通之后，工作流变成了闭环：</p>
<ol>
<li><strong>外出采访时</strong>：打开手机 Obsidian，在 <code>articles/某个选题/notes/</code> 下记录采访笔记</li>
<li><strong>回到写作时</strong>：在 Termux 里启动 Claude Code，运行 <code>claude</code>，说「看看 notes/ 里的采访笔记，按提纲整理」</li>
<li><strong>需要修改时</strong>：Claude Code 写到 <code>draft.md</code>，然后在 Obsidian 里打开同一份文件继续修改</li>
<li><strong>需要发布时</strong>：在 Termux 里说「publish」</li>
</ol>
<p>因为双方读写的是同一个文件系统的同一份文件，没有同步延迟，没有冲突风险。一方写了，另一方立刻看得到。</p>
<h2 id="_5">拓展：网盘同步</h2>
<p>打通本地还不够，文章还需要备份到网盘。</p>
<p>用 rclone 把 Obsidian 库同步到 Dropbox 和 Google Drive。确认机器上 rclone 已安装，并且配置了两个 remote：</p>
<div class="codehilite"><pre><span></span><code>rclone<span class="w"> </span>listremotes
dropbox:
gdrive:
</code></pre></div>
<p>同步命令：</p>
<div class="codehilite"><pre><span></span><code><span class="c1"># 同步到 Dropbox</span>
rclone<span class="w"> </span>sync<span class="w"> </span>/storage/emulated/0/Documents/obsidian/<span class="w"> </span>dropbox:obsidian-notes<span class="w"> </span>--progress

<span class="c1"># 同步到 Google Drive</span>
rclone<span class="w"> </span>sync<span class="w"> </span>/storage/emulated/0/Documents/obsidian/<span class="w"> </span>gdrive:obsidian-notes<span class="w"> </span>--progress
</code></pre></div>
<p>这样，一篇文章同时存在于三个地方：手机本地（Obsidian + Termux）、Dropbox、Google Drive。任何一个设备出问题，数据都不会丢。</p>
<h2 id="_6">发布闭环</h2>
<p>文章写完、网盘备份之后，最后一步是发布到博客。</p>
<p>博客基于 Python 静态站点生成器（<code>/root/blog/publish.py</code>），模板使用 Jinja2，部署在 GitHub Pages 上。运行发布命令：</p>
<div class="codehilite"><pre><span></span><code>bash<span class="w"> </span>/root/blog/deploy.sh
</code></pre></div>
<p>发布后访问：<a href="https://daitree42.github.io/blog-pages/">https://daitree42.github.io/blog-pages/</a></p>
<p>从在 Obsidian 里写下第一个字开始，到文章出现在博客上，整个过程不离开手机。</p>
<h2 id="_7">一些建议</h2>
<p>这套方案依赖几个关键节点，每个节点都有一些值得注意的地方。</p>
<ul>
<li><strong>先跑 termux-setup-storage</strong>：这是所有后续操作的前提。如果报错说目录已存在，先检查 Termux 本体 <code>~/storage/</code> 下的符号链接是否完整，可能需要清理后再跑一次。</li>
<li><strong>PRoot Distro 内路径一致</strong>：在容器里尽量使用绝对路径（<code>/storage/emulated/0/...</code>），而不是依赖终端模拟器里的相对路径或者 <code>~</code> 展开，因为容器里 <code>~</code> 指向的是 <code>/root/</code>，不是 Termux 的主目录。</li>
<li><strong>不要直接编辑 .obsidian 配置</strong>：Obsidian 在 vault 根目录下有一个 <code>.obsidian/</code> 文件夹，保存配置和缓存。不要删除或修改它，否则 Obsidian 可能打不开 vault。</li>
<li><strong>rclone 配置用 <code>sync</code> 而非 <code>copy</code></strong>：<code>sync</code> 会双向比对，确保目标端与源端完全一致，删除目标端多余的旧文件。<code>copy</code> 不会做清理，时间长了网盘里会有大量已废弃的旧版本。</li>
<li><strong>网盘同步时机</strong>：建议每次写完一个完整段落或完成一次修改后手动同步。也可以写一个简单的脚本，把文章保存、网盘同步和发布合并为一个命令。</li>
</ul>
<h2 id="_8">局限与可能的改进</h2>
<p>这套方案基于 Android 的共享存储路径访问。如果未来 Android 版本的 Scoped Storage 进一步收紧这个路径的访问权限，方案可能需要调整。一种可选的备选方案是走 SyncThing，通过局域网同步来替代直接文件系统共享。</p>
<p>另一个局限是 PRoot Distro 的性能开销——容器化运行 Claude Code 比原生 Termux 应用慢一些，但对写作工作流来说几乎不可感知。</p>
<p>连接 Obsidian 和 Claude Code 这件事本身并不复杂，核心在于理解文件系统在 Android、Termux 和容器之间的映射关系。一旦理解了这层映射，能做的事情就不只是记笔记和写文章——同样的原理可以扩展到任何需要在命令行和图形界面之间共享文件的场景。</p>
<hr/>
<p><em>这篇文章本身就是用打通后的工作流写成的：采访笔记在 Obsidian 里记录，正文由 Claude Code 生成，保存到 Obsidian、「发布」命令部署到博客，再通过 rclone 备份到网盘。</em></p>