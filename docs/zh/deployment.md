# 部署指南

## GitHub Actions（零运维）

Fork 项目后，在仓库 Settings → Secrets and variables → Actions 中添加以下 Secrets：

**必填：**

| Secret | 说明 | 示例 |
|---|---|---|
| `API_BASE_URL` | LLM API 地址 | `https://api.deepseek.com/v1` |
| `API_KEY` | API 密钥 | `sk-xxx` |
| `MODEL_NAME` | 模型名 | `deepseek-chat` |

**邮件推送（可选）：**

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

## 容器部署（Podman / Docker）

支持 Podman 和 Docker，镜像约 340MB（Python 3.12 slim + 依赖）。

**快速启动：**

```bash
# 构建镜像
podman build -t sift:latest .

# 运行（传入环境变量，挂载必要目录）
podman run --rm \
  --env-file .env \
  -v ./feeds.json:/app/feeds.json:ro \
  -v ./output:/app/output \
  -v ./knowledge:/app/knowledge \
  -v ./site:/app/site \
  sift:latest run
```

**使用 docker-compose：**

```bash
podman compose up
```

`docker-compose.yml` 已配置好环境变量和卷挂载。

**网络问题排查：**

如果容器内需要代理，在 `podman run` 时传入：

```bash
-e HTTP_PROXY=http://host.docker.internal:7897 \
-e HTTPS_PROXY=http://host.docker.internal:7897
```

**定时任务：**

```bash
# 每周一 17:00 北京时间运行
0 9 * * 1 podman run --rm --env-file .env \
  -v /path/to/feeds.json:/app/feeds.json:ro \
  -v /path/to/output:/app/output \
  -v /path/to/knowledge:/app/knowledge \
  sift:latest run
```

## 本地运行

```bash
git clone <repo> && cd sift
pip install -r requirements.txt        # 纯 CLI
# pip install -r requirements-ui.txt   # CLI + Web UI（可选）
cp .env.example .env
vi .env          # 填入你的配置
python3 sift/cli.py run
```

需要 Web UI 时安装 `requirements-ui.txt`，然后启动：

```bash
streamlit run app.py
```

Web UI 提供两个页面 + 侧边栏：
- **Dashboard**：周报时间线、话题趋势图、来源分布
- **文章浏览**：按关键词搜索、按来源筛选，每篇文章支持 👍/👎 反馈
- **侧边栏**：语言偏好、工作区切换

## Android（可选）

Termux 环境下可一键部署：

```bash
git clone <repo> sift && cd sift
bash scripts/setup-termux.sh
vi .env
.venv/bin/python3 sift/cli.py run
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
python3 sift/cli.py run --profile tech-weekly                    # 技术周报（默认源）
python3 sift/cli.py run --profile finance-weekly --feeds finance.json  # 投研周报
python3 sift/cli.py run --profile papers-weekly --feeds papers.json    # 论文周报
```

也可以设不同的发送时间：

```
0 8 * * 1   python3 sift/cli.py run --profile tech-weekly
0 9 * * 1   python3 sift/cli.py run --profile finance-weekly --feeds finance.json
0 8 * * 5   python3 sift/cli.py run --profile papers-weekly --feeds papers.json
```
