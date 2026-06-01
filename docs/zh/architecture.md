# 架构设计

## 三层管道 + 反馈闭环

Sift 采用三层管道架构，数据源、处理逻辑、投递渠道完全解耦，用户反馈自动驱动偏好演进：

```
Sources ──▶ Pipeline ◀──▶ KnowledgeStorage ◀──▶ Channels
                                ▲
                                │
                                ▼
                             Web UI
```

所有组件围绕 KnowledgeStorage（knowledge.db）交互，Pipeline 负责抓取、去重、摘要、投递。

## 数据源层（Sources）

每个源只需实现 `fetch(since) -> FeedResult` 接口：

| 源类型 | 状态 | 说明 |
|---|---|---|
| **RSS/Atom** | ✅ 已实现 | 支持所有标准 RSS/Atom 源 |
| **Web 爬虫** | ✅ 已实现 | CSS 选择器提取，适配无 RSS 的网站 |
| **API 接口** | 🔜 可扩展 | 接入 Twitter/Telegram/知乎等需要 API 的平台 |

## 投递层（Channels）

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

## 扩展方式

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

## 反馈驱动的偏好系统

Sift 不需要手动选择"关注领域"——系统从你的行为中自动学习偏好。

### 工作原理

```
用户浏览文章 → 点击 👍/👎 → 反馈写入 DB
                                    │
                                    ▼
                          Feedback Engine 汇总
                          ├── 话题权重（哪些话题 👍 多 → 权重高）
                          ├── 来源权重（哪些来源 👍 多 → 权重高）
                          └── 负面信号（👎 多的话题/来源 → 降权）
                                    │
                                    ▼
                          下一期周报生成时
                          ├── 话题权重注入 prompt（侧重用户感兴趣的方向）
                          ├── 来源权重影响排序（高权重来源优先展示）
                          └── 降权内容减少出现频率
```

### 反馈信号

| 交互 | 学到什么 |
|---|---|
| 👍 | 这个话题/来源有价值，下期多给相关内容 |
| 👎 | 这个话题/来源不感兴趣，降低出现频率 |
| 不操作 | 中性，不影响权重 |

### 与手动设置的区别

| | 手动设置（旧） | 反馈驱动（新） |
|---|---|---|
| 用户负担 | 要从 15 个话题里选 | 只需对文章点 👍/👎 |
| 准确度 | 用户自己也不确定想看什么 | 从实际阅读行为推断 |
| 适应性 | 静态，选完就不变 | 动态，兴趣变了权重自动跟上 |
| 冷启动 | 无（手动选就行） | 前几期无反馈，走默认策略 |

## 知识积累

每次运行周报，系统会自动将文章存入本地 SQLite 数据库（`knowledge/knowledge.db`），逐步构建你的技术知识库：

- **文章存储**：所有抓取的文章自动入库，按 hash 去重，不会重复存储
- **反馈累积**：用户对文章的 👍/👎 持久化存储，形成偏好画像
- **趋势追踪**：自动提取话题关键词，按周统计频率，检测上升趋势话题
- **语义搜索**：配置 embedding 模型后，支持自然语言相似度搜索（如"LLM 安全相关文章"）
- **趋势注入**：生成周报时，系统会把历史高频话题和上升趋势作为上下文注入 LLM，让摘要能参考长期趋势，避免每次都从零开始
- **偏好注入**：生成周报时，Feedback Engine 汇总的话题/来源权重自动注入 prompt，让摘要贴合用户兴趣

**为什么用 SQLite + sqlite-vec？**
- 单文件存储（`knowledge/knowledge.db`），零运维，手机上直接跑
- 结构化查询（按时间、来源过滤）和向量搜索（语义相似度）共用一个数据库
- sqlite-vec 是 SQLite 官方扩展，纯 C 实现，无外部依赖

**配置 embedding（可选）**：在 `.env` 中设置 `EMBEDDING_MODEL` 指向你的 API 支持的 embedding 模型名，即可启用语义搜索。不配置也不影响核心功能——文章存储、趋势分析、周报生成照常运行。

## 实现方案

### 数据库 Schema 变更

在 `knowledge.db` 中新增 `feedback` 表：

```sql
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    signal INTEGER NOT NULL,  -- +1 = 👍, -1 = 👎
    created_at TEXT DEFAULT datetime('now'),
    UNIQUE(article_id)        -- 每篇文章只能有一次反馈（可覆盖）
);
CREATE INDEX IF NOT EXISTS idx_feedback_article ON feedback(article_id);
```

`articles` 表不变——`tags` 字段已存储文章话题，用于权重汇总时 JOIN。

### Feedback Engine

新增 `processors/feedback.py`，负责：

```python
class FeedbackEngine:
    def get_topic_weights(self) -> dict[str, float]:
        """汇总话题权重：Σ(feedback.signal) GROUP BY tag，归一化到 [-1, 1]。"""

    def get_source_weights(self) -> dict[str, float]:
        """汇总来源权重：Σ(feedback.signal) GROUP BY source，归一化到 [-1, 1]。"""

    def build_preference_context(self) -> str:
        """生成偏好上下文文本，注入 prompt。
        正权重话题：'用户对 XX 方向较感兴趣，可适当侧重'
        负权重话题：'用户对 XX 方向关注度较低，减少篇幅'
        """
```

### Pipeline 集成

`pipeline.py` 的 `run()` 方法中，在生成摘要前注入偏好上下文：

```python
# 现有：趋势上下文
trend_ctx = self.storage.generate_trend_context()

# 新增：偏好上下文
preference_ctx = self.storage.build_preference_context()

# 合并注入 prompt
context = "\n\n".join(filter(None, [trend_ctx, preference_ctx]))
digest = self.summarize_processor.process(results, trend_context=context)
```

### Web UI 变更

| 页面 | 变更 |
|---|---|
| **Dashboard** | 不变 |
| **文章浏览** | 每篇文章卡片增加 👍/👎 按钮，点击后写入 `feedback` 表 |
| **设置页** | 删除（手动 checkbox 偏好移除） |
| **侧边栏** | 保留语言选择、工作区切换 |

### 改动文件清单

| 文件 | 改动 |
|---|---|
| `storage/knowledge.py` | 新增 `save_feedback()`、`get_topic_weights()`、`get_source_weights()`、`build_preference_context()` |
| `processors/feedback.py` | 新建，Feedback Engine 逻辑 |
| `pipeline.py` | `run()` 中注入偏好上下文 |
| `pages/articles.py` | 每篇文章加 👍/👎 按钮 |
| `pages/settings.py` | 删除 |
| `app.py` | 移除 settings 页面导航 |
| `tests/test_all.py` | 新增 feedback 相关测试 |

### 冷启动策略

前 N 期无反馈时，系统使用默认策略（当前的全量摘要）。当反馈积累到阈值（如 ≥10 条）后，自动启用偏好注入。可通过环境变量 `FEEDBACK_THRESHOLD` 配置。
