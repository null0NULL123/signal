# Signal

每周自动从顶级工程博客收集文章，用 AI 生成中文技术周报，发送到你的邮箱。

## 背景

追技术博客的痛点：信息源分散、英文阅读慢、每周花 2-3 小时逐个浏览不现实。现有方案要么只聚合不摘要（RSS 阅读器），要么转述二手信息（公众号），要么噪音太大（Hacker News）。

**Signal**：选定几个高质量源 → 自动抓取 → AI 生成中文摘要 → 投递到你常用的平台。不做大而全，做小而精。

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

每次运行周报，系统会自动将文章存入本地 SQLite 数据库（`knowledge/pulse.db`），逐步构建你的技术知识库：

- **文章存储**：所有抓取的文章自动入库，按 hash 去重，不会重复存储
- **趋势追踪**：自动提取话题关键词，按周统计频率，检测上升趋势话题
- **语义搜索**：配置 embedding 模型后，支持自然语言相似度搜索（如"LLM 安全相关文章"）
- **趋势注入**：生成周报时，系统会把历史高频话题和上升趋势作为上下文注入 LLM，让摘要能参考长期趋势，避免每次都从零开始

**为什么用 SQLite + sqlite-vec？**
- 单文件存储（`knowledge/pulse.db`），零运维，手机上直接跑
- 结构化查询（按时间、来源过滤）和向量搜索（语义相似度）共用一个数据库
- sqlite-vec 是 SQLite 官方扩展，纯 C 实现，无外部依赖

**配置 embedding（可选）**：在 `.env` 中设置 `EMBEDDING_MODEL` 指向你的 API 支持的 embedding 模型名，即可启用语义搜索。不配置也不影响核心功能——文章存储、趋势分析、周报生成照常运行。

## 部署

### Android（推荐）

```bash
# 1. 安装 Termux (F-Droid 版本)
# 2. 克隆项目
git clone <repo> signal && cd signal
# 3. 一键安装
bash setup.sh
# 4. 编辑 .env 填入密钥和邮箱
vi .env
# 5. 手动测试
.venv/bin/python3 cli.py
# 6. 启动定时任务
crond
```

### 任何有 Python 3.10+ 的环境

```bash
pip install -r requirements.txt
cp .env.example .env
vi .env
python3 cli.py
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
