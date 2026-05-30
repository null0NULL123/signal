# Signal

自动从你关注的信息源收集内容，用 AI 生成结构化摘要，投递到你常用的平台。

## 背景

你是否也有这样的困扰：

- **技术从业者**：关注的工程博客、开源动态分散在十几个站点，英文内容读得慢，每周花几小时浏览不现实
- **研究人员**：论文、行业报告、领域新闻散落各处，想追踪却总错过关键更新
- **内容创作者**：需要持续跟踪行业趋势和热点，手动刷新效率太低
- **商务人士**：行业资讯、竞品动态、政策变化淹没在信息洪流里，找不到重点
- **任何信息焦虑者**：RSS 阅读器只聚合不摘要，公众号转述二手信息，社交平台噪音太大

**核心问题**：信息源分散 + 语言障碍 + 时间有限 = 被动错过重要内容。

**Signal 的思路**：选定你的信息源 → 自动抓取 → AI 生成结构化摘要 → 投递到你常用的平台。数据源、处理逻辑、投递渠道完全解耦，按需扩展，不做大而全，做小而精。

## 竞品对比

开源 AI 信息聚合领域有不少优秀项目，Signal 的定位是**轻量、零依赖、可扩展的 CLI 工具**。以下是主要对比：

| 项目 | ⭐ Stars | AI 摘要 | 多源聚合 | 部署方式 | 适合谁 |
|---|---|---|---|---|---|
| [RSSHub](https://github.com/DIYgod/RSSHub) | 44k | ❌ | ✅ 500+ 站点 | Docker | 需要大量信息源生成能力，配合阅读器使用 |
| [Folo](https://github.com/RSSNext/Folo) | 38k | ✅ | ❌ 仅 RSS | 桌面/移动端 App | 想要跨平台 AI 阅读器体验 |
| [Glance](https://github.com/glanceapp/glance) | 35k | ❌ | ✅ HN/Reddit/YouTube 等 | 单二进制 | 想要多源聚合仪表盘，不需要 AI |
| [FreshRSS](https://github.com/FreshRSS/FreshRSS) | 15k | ❌ | ❌ 仅 RSS | PHP/Docker | 经典自托管 RSS 阅读器 |
| [zenfeed](https://github.com/glidea/zenfeed) | 1.7k | ✅ | ❌ 仅 RSS | Go/Docker | 想要完整 AI+RSS 知识库，接受自托管 |
| [ClawFeed](https://github.com/kevinho/clawfeed) | 2.2k | ✅ | ✅ HN/Reddit/GitHub | Node.js/Docker | 想要多源 + AI，接受较重的部署 |
| [CondenseIt](https://github.com/wildlifechorus/condenseit) | 53 | ✅ | ✅ 多源 + 个性化排名 | Python/Docker | 想要个性化推荐，接受早期项目 |
| [osmos::feed](https://github.com/osmoscraft/osmosfeed) | 993 | ❌ | ❌ 仅 RSS | GitHub Pages | 零成本静态 RSS 站点，不需要 AI |
| **Signal** | — | **✅** | **✅ RSS + Web 爬虫** | **Python/cron/GitHub Actions + 可选 Web UI** | **想要零基础设施、CLI 优先、可编程的信息管道** |

### Signal 的差异点

- **零基础设施**：不需要 Docker、数据库服务器或 Web 服务。一个 Python 脚本 + cron（或 GitHub Actions）就能跑
- **CLI 优先 + 可选 Web UI**：默认纯 CLI，需要可视化时可选启用 Streamlit UI（Dashboard + 偏好设置 + 文章浏览）
- **知识积累**：不只是生成周报就丢掉——文章自动入库，支持趋势追踪和语义搜索，越用越有价值
- **领域无关**：换数据源和 prompt 就能变成金融投研周报、AI 论文速递、行业动态等，不限于技术博客
- **可编程管道**：三层解耦架构（数据源 → 处理 → 投递），新增源或渠道只需实现一个接口

### 与 ClawFeed 的详细对比

ClawFeed 是功能最接近的竞品（多源聚合 + AI 摘要），两者的核心差异：

| 维度 | ClawFeed | Signal |
|---|---|---|
| **部署** | Node.js + Docker + Web SPA，需要服务器 | Python 脚本 + cron/GitHub Actions，零服务器 |
| **前端维护** | 需要维护 SPA 仪表盘 | 无前端，GitHub Pages 静态页面自动生成 |
| **架构** | 单体应用 | 三层解耦（Sources → Pipeline → Channels），各层独立扩展 |
| **知识积累** | 生成 digest 后数据沉淀有限 | SQLite 入库 + 趋势追踪 + 语义搜索，越用越有价值 |
| **领域通用性** | 定位为新闻聚合 | 换数据源和 prompt 可变成投研周报、论文速递等任意领域 |
| **Web 爬虫** | 依赖平台 API（Twitter/Reddit 等） | 内置 CSS 选择器爬虫，无 RSS 的网站也能抓 |
| **成本** | 需要持续运行的服务器 | GitHub Actions 免费额度内完全零成本 |

**总结**：ClawFeed 是功能更全的产品（Twitter/Reddit/HN 源 + Web 仪表盘），Signal 是更轻的工具（零运维、可编程、有知识积累）。如果需要 Twitter/Reddit 数据源和漂亮的 Web 界面，ClawFeed 更合适；如果想要零成本、可扩展、越用越有积累的信息管道，Signal 更合适。

### 什么时候不选 Signal

- 需要功能丰富的 Web 阅读器界面 → 选 **Folo** 或 **Glance**（Signal 提供轻量 Dashboard，但不是完整阅读器）
- 需要移动端原生体验 → 选 **Folo**
- 需要 500+ 站点的 RSS 生成能力 → 选 **RSSHub** 作为上游数据源
- 需要完整的知识库 + 对话式查询 → 选 **zenfeed**
- 需要团队协作和社交功能 → 选 **NewsBlur** 或 **FreshRSS**

## 架构设计

Signal 采用**三层管道架构**，数据源、处理逻辑、投递渠道完全解耦，各层可独立扩展：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Sources    │───▶│  Pipeline   │───▶│  Channels   │
│  (数据源层)  │    │  (处理层)    │    │  (投递层)    │
└─────────────┘    └─────────────┘    └─────────────┘
  RSS Source          Dedup              Email
  Web Source          Store              File
  (+ 未来: API        Summarize          GitHub Pages
   Telegram,          Trend inject       (+ 未来: 微信公众号
   微信读书,                            小红书, Telegram,
   arXiv...)                            Discord...)

                    ┌─────────────┐
                    │  Web UI     │  ← 可选（Streamlit）
                    │  Dashboard  │
                    │  设置/浏览   │
                    └─────────────┘
```

### 数据源层（Sources）

每个源只需实现 `fetch(since) -> FeedResult` 接口：

| 源类型 | 状态 | 说明 |
|---|---|---|
| **RSS/Atom** | ✅ 已实现 | 支持所有标准 RSS/Atom 源 |
| **Web 爬虫** | ✅ 已实现 | CSS 选择器提取，适配无 RSS 的网站 |
| **API 接口** | 🔜 可扩展 | 接入 Twitter/Telegram/知乎等需要 API 的平台 |

### 投递层（Channels）

每个渠道只需实现 `send(digest) -> bool` 接口：

| 渠道 | 状态 | 说明 |
|---|---|---|
| **Email** | ✅ 已实现 | SMTP 发送，支持 QQ 邮箱 / Gmail 等 |
| **文件** | ✅ 已实现 | 保存为本地 Markdown 文件 |
| **GitHub Pages** | ✅ 已实现 | 自动生成静态网站 |
| **微信公众号** | 🔜 可扩展 | 需认证服务号 + 模板消息 API |
| **小红书** | 🔜 可扩展 | 需逆向 API 或 RPA 方案 |
| **Telegram Bot** | 🔜 可扩展 | Bot API 直接发送，接入成本低 |
| **Discord / Slack** | 🔜 可扩展 | Webhook 发送，接入成本低 |

### 扩展方式

新增一个渠道只需 3 步：

```python
# 1. 创建 channels/wechat.py
class WechatChannel(BaseChannel):
    @property
    def name(self) -> str:
        return "wechat"

    def send(self, digest: Digest) -> bool:
        # 调用微信公众号模板消息 API
        ...

# 2. 在 cli.py 的 cmd_run 中注册
channels=[FileChannel(), EmailChannel(), WechatChannel()]

# 3. 在 .env 中添加配置
# WECHAT_APPID=your-appid
# WECHAT_SECRET=your-secret
```

新增数据源同理，实现 `BaseSource.fetch()` 接口即可。

## 技术方案

```
数据源抓取（并行） → 过滤最近 N 天 → 存入知识库 → 注入历史趋势 → LLM 生成中文摘要 → 投递到各渠道
```

**为什么先做邮件？** SMTP 是最成熟的自动化发送方案，几行代码就能跑，零维护成本，手机电脑都能看。但架构不绑定邮件——其他渠道（微信公众号、Telegram 等）同样是插件，随时可以加。

## 知识积累

每次运行周报，系统会自动将文章存入本地 SQLite 数据库（`knowledge/signal.db`），逐步构建你的技术知识库：

- **文章存储**：所有抓取的文章自动入库，按 hash 去重，不会重复存储
- **趋势追踪**：自动提取话题关键词，按周统计频率，检测上升趋势话题
- **语义搜索**：配置 embedding 模型后，支持自然语言相似度搜索（如"LLM 安全相关文章"）
- **趋势注入**：生成周报时，系统会把历史高频话题和上升趋势作为上下文注入 LLM，让摘要能参考长期趋势，避免每次都从零开始

**为什么用 SQLite + sqlite-vec？**
- 单文件存储（`knowledge/signal.db`），零运维，手机上直接跑
- 结构化查询（按时间、来源过滤）和向量搜索（语义相似度）共用一个数据库
- sqlite-vec 是 SQLite 官方扩展，纯 C 实现，无外部依赖

**配置 embedding（可选）**：在 `.env` 中设置 `EMBEDDING_MODEL` 指向你的 API 支持的 embedding 模型名，即可启用语义搜索。不配置也不影响核心功能——文章存储、趋势分析、周报生成照常运行。

## 部署

### GitHub Actions（零运维）

Fork 项目后，在仓库 Settings → Secrets and variables → Actions 中添加以下 Secrets：

**必填：**

| Secret | 说明 | 示例 |
|---|---|---|
| `API_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `API_KEY` | API 密钥 | `sk-xxx` |
| `MODEL_NAME` | 模型名 | `deepseek-chat` |

### 邮件推送（可选）

默认不发邮件。需要邮件推送时，添加以下 Secrets 并在运行时加 `--email` 参数：

| Secret | 说明 |
|---|---|
| `SMTP_SERVER` | SMTP 服务器，如 `smtp.qq.com` |
| `SMTP_PORT` | SMTP 端口，如 `587` |
| `SMTP_SENDER` | 发件邮箱 |
| `SMTP_AUTH_CODE` | 邮箱授权码 |
| `SMTP_RECEIVER` | 收件邮箱 |

配置完成后，每周一北京时间 17:00 自动运行。也可在 Actions 页面手动触发。

如需启用 GitHub Pages 展示周报页面，在仓库 Settings → Pages 中选择 `gh-pages` 分支。

### 本地运行

```bash
git clone <repo> && cd signal
pip install -r requirements.txt        # 纯 CLI
# pip install -r requirements-ui.txt   # CLI + Web UI（可选）
cp .env.example .env
vi .env          # 填入你的配置
python3 cli.py run
```

需要 Web UI 时安装 `requirements-ui.txt`，然后启动：

```bash
streamlit run app.py
```

Web UI 提供三个页面：
- **Dashboard**：周报时间线、话题趋势图、来源分布
- **文章浏览**：按关键词搜索、按来源筛选
- **设置**：选择关注领域和偏好，系统据此定制周报内容

### Android（可选）

Termux 环境下可一键部署：

```bash
git clone <repo> signal && cd signal
bash setup.sh
vi .env
.venv/bin/python3 cli.py run
crond  # 启动定时任务
```

## 配置

`.env` 文件：

| 变量 | 说明 | 示例 |
|---|---|---|
| `API_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `API_KEY` | API 密钥 | `sk-xxx` |
| `MODEL_NAME` | 模型名 | `deepseek-chat` |
| `SMTP_SENDER` | 发件 QQ 邮箱 | `123456@qq.com` |
| `SMTP_AUTH_CODE` | QQ 邮箱授权码 | 见下方说明 |
| `SMTP_RECEIVER` | 收件邮箱 | `123456@qq.com` |
| `SUMMARY_DAYS` | 回溯天数 | `7` |
| `EMBEDDING_MODEL` | embedding 模型名（启用语义搜索） | `text-embedding-v3` |

完整配置项见 `.env.example`。

**QQ 邮箱授权码获取**：QQ 邮箱 → 设置 → 账户 → POP3/SMTP 服务 → 开启 → 生成授权码

## 添加/删除订阅源

编辑 `feeds.json`：

```json
{
  "name": "Cloudflare Blog",
  "url": "https://blog.cloudflare.com/rss/",
  "lang": "en"
}
```

加一行就是一个新源，删一行就取消订阅。支持 `source_type: "web"` 用于无 RSS 的网站。

## 扩展：不止于技术周报

核心管道（数据源 → 过滤 → AI 摘要 → 投递）是领域无关的。换一套数据源和 prompt，就能变成完全不同的周报：

| 场景 | 数据源示例 | 摘要重点 |
|---|---|---|
| **技术周报**（默认） | GitHub Blog、Meta Engineering、Netflix Tech Blog... | 技术要点、架构实践 |
| **金融投研** | Bloomberg Opinion、FT Markets、华尔街见闻... | 宏观信号、政策变化、资产影响 |
| **AI 论文** | arXiv (cs.AI/cs.CL/cs.LG)、Papers With Code... | 新架构、SOTA 突破、开源发布 |
| **行业动态** | 36氪、TechCrunch、Product Hunt... | 产品发布、融资、市场趋势 |

实现方式：通过 `--profile` 切换 prompt 模板，通过 `--feeds` 切换数据源：

```bash
python3 cli.py run --profile tech-weekly                    # 技术周报（默认源）
python3 cli.py run --profile finance-weekly --feeds finance.json  # 投研周报
python3 cli.py run --profile papers-weekly --feeds papers.json    # 论文周报
```

也可以设不同的发送时间：

```
0 8 * * 1   python3 cli.py run --profile tech-weekly
0 9 * * 1   python3 cli.py run --profile finance-weekly --feeds finance.json
0 8 * * 5   python3 cli.py run --profile papers-weekly --feeds papers.json
```

## 测试

```bash
python tests/test_all.py          # 运行全部测试（27 个）
python tests/test_all.py storage  # 只运行 storage 组
python tests/test_all.py config   # 只运行 config 组
```

## 许可

MIT
