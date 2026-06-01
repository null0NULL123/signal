# 竞品对比

开源 AI 信息聚合领域有不少优秀项目，Sift 的定位是**轻量、零依赖、可扩展的 CLI 工具**。

## 主要对比

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
| **Sift** | — | **✅** | **✅ RSS + Web 爬虫** | **Python/cron/GitHub Actions + 可选 Web UI** | **想要零基础设施、CLI 优先、可编程的信息管道** |

## Sift 的差异点

- **零基础设施**：不需要 Docker、数据库服务器或 Web 服务。一个 Python 脚本 + cron（或 GitHub Actions）就能跑
- **CLI 优先 + 可选 Web UI**：默认纯 CLI，需要可视化时可选启用 Streamlit UI（Dashboard + 文章浏览 + 反馈驱动偏好）
- **知识积累**：不只是生成周报就丢掉——文章自动入库，支持趋势追踪和语义搜索，越用越有价值
- **领域无关**：换数据源和 prompt 就能变成金融投研周报、AI 论文速递、行业动态等，不限于技术博客
- **可编程管道**：三层解耦架构（数据源 → 处理 → 投递），新增源或渠道只需实现一个接口

## 与 ClawFeed 的详细对比

ClawFeed 是功能最接近的竞品（多源聚合 + AI 摘要），两者的核心差异：

| 维度 | ClawFeed | Sift |
|---|---|---|
| **部署** | Node.js + Docker + Web SPA，需要服务器 | Python 脚本 + cron/GitHub Actions，零服务器 |
| **前端维护** | 需要维护 SPA 仪表盘 | 无前端，GitHub Pages 静态页面自动生成 |
| **架构** | 单体应用 | 三层解耦（Sources → Pipeline → Channels），各层独立扩展 |
| **知识积累** | 生成 digest 后数据沉淀有限 | SQLite 入库 + 趋势追踪 + 语义搜索，越用越有价值 |
| **领域通用性** | 定位为新闻聚合 | 换数据源和 prompt 可变成投研周报、论文速递等任意领域 |
| **Web 爬虫** | 依赖平台 API（Twitter/Reddit 等） | 内置 CSS 选择器爬虫，无 RSS 的网站也能抓 |
| **成本** | 需要持续运行的服务器 | GitHub Actions 免费额度内完全零成本 |

**总结**：ClawFeed 是功能更全的产品（Twitter/Reddit/HN 源 + Web 仪表盘），Sift 是更轻的工具（零运维、可编程、有知识积累）。如果需要 Twitter/Reddit 数据源和漂亮的 Web 界面，ClawFeed 更合适；如果想要零成本、可扩展、越用越有积累的信息管道，Sift 更合适。

## 什么时候不选 Sift

- 需要功能丰富的 Web 阅读器界面 → 选 **Folo** 或 **Glance**（Sift 提供轻量 Dashboard，但不是完整阅读器）
- 需要移动端原生体验 → 选 **Folo**
- 需要 500+ 站点的 RSS 生成能力 → 选 **RSSHub** 作为上游数据源
- 需要完整的知识库 + 对话式查询 → 选 **zenfeed**
- 需要团队协作和社交功能 → 选 **NewsBlur** 或 **FreshRSS**
