# Sift

自动从你关注的信息源收集内容，用 AI 生成结构化摘要，投递到你常用的平台。

[English](docs/en/README.md) | **中文**

## 背景

你是否也有这样的困扰：

- **技术从业者**：关注的工程博客、开源动态分散在十几个站点，英文内容读得慢，每周花几小时浏览不现实
- **研究人员**：论文、行业报告、领域新闻散落各处，想追踪却总错过关键更新
- **内容创作者**：需要持续跟踪行业趋势和热点，手动刷新效率太低
- **商务人士**：行业资讯、竞品动态、政策变化淹没在信息洪流里，找不到重点

**核心问题**：信息源分散 + 语言障碍 + 时间有限 = 被动错过重要内容。

**Sift 的思路**：选定你的信息源 → 自动抓取 → AI 生成结构化摘要 → 投递到你常用的平台。数据源、处理逻辑、投递渠道完全解耦，按需扩展，不做大而全，做小而精。

## 架构

```
Sources ──▶ Pipeline ◀──▶ KnowledgeStorage ◀──▶ Channels
                                ▲
                                │
                                ▼
                             Web UI
```

所有组件围绕 KnowledgeStorage（knowledge.db）交互，Pipeline 负责抓取、去重、摘要、投递。

→ [完整架构设计](docs/zh/architecture.md)

## 快速开始

```bash
git clone <repo> && cd sift
pip install -r requirements.txt
cp .env.example .env
vi .env              # 填入 API_KEY 等配置
python3 cli.py run   # 生成第一期周报
```

容器部署（Podman / Docker）：

```bash
podman build -t sift:latest .
podman run --rm --env-file .env \
  -v ./feeds.json:/app/feeds.json:ro \
  -v ./output:/app/output \
  -v ./knowledge:/app/knowledge \
  sift:latest run
```

可选 Web UI：

```bash
pip install -r requirements-ui.txt
streamlit run app.py
```

→ [部署指南（GitHub Actions / 容器 / Android / 配置详解）](docs/zh/deployment.md)

## 文档

| 文档 | 内容 |
|---|---|
| [架构设计](docs/zh/architecture.md) | 三层管道、反馈系统、知识积累、实现方案 |
| [部署指南](docs/zh/deployment.md) | GitHub Actions、本地运行、Android、配置、订阅源管理 |
| [竞品对比](docs/zh/competitive-analysis.md) | 与 RSSHub / Folo / ClawFeed 等项目的对比 |

## Documentation (English)

| Document | Content |
|---|---|
| [Architecture Design](docs/en/architecture.md) | Three-layer pipeline, feedback system, knowledge accumulation, implementation details |
| [Deployment Guide](docs/en/deployment.md) | GitHub Actions, local running, Android, configuration, subscription source management |
| [Competitive Analysis](docs/en/competitive-analysis.md) | Comparison with RSSHub / Folo / ClawFeed and other projects |

## 测试

```bash
python tests/test_all.py          # 运行全部测试
python tests/test_all.py storage  # 只运行 storage 组
python tests/test_all.py config   # 只运行 config 组
```

## 许可

MIT
