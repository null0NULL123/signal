# Deployment Guide

## GitHub Actions (Zero Operations)

After forking the project, add the following Secrets in repository Settings → Secrets and variables → Actions:

**Required:**

| Secret | Description | Example |
|---|---|---|
| `API_BASE_URL` | LLM API address | `https://api.deepseek.com/v1` |
| `API_KEY` | API key | `sk-xxx` |
| `MODEL_NAME` | Model name | `deepseek-chat` |

**Email delivery (optional):**

By default, no emails are sent. To enable email delivery, add the following Secrets and add `--email` parameter when running:

| Secret | Description |
|---|---|
| `SMTP_SERVER` | SMTP server, e.g., `smtp.qq.com` |
| `SMTP_PORT` | SMTP port, e.g., `587` |
| `SMTP_SENDER` | Sender email |
| `SMTP_AUTH_CODE` | Email authorization code |
| `SMTP_RECEIVER` | Receiver email |

After configuration, it automatically runs every Monday at 17:00 Beijing time. Can also be manually triggered on the Actions page.

To enable GitHub Pages for displaying report pages, select `gh-pages` branch in repository Settings → Pages.

## Container Deployment (Podman / Docker)

Podman and Docker are supported. Image size ~340MB (Python 3.12 slim + dependencies).

**Quick start:**

```bash
# Build image
podman build -t sift:latest .

# Run (pass env vars, mount necessary directories)
podman run --rm \
  --env-file .env \
  -v ./feeds.json:/app/feeds.json:ro \
  -v ./output:/app/output \
  -v ./knowledge:/app/knowledge \
  -v ./site:/app/site \
  sift:latest run
```

**Using docker-compose:**

```bash
podman compose up
```

`docker-compose.yml` has env vars and volume mounts pre-configured.

**Network troubleshooting:**

If the container needs a proxy, pass it via:

```bash
-e HTTP_PROXY=http://host.docker.internal:7897 \
-e HTTPS_PROXY=http://host.docker.internal:7897
```

**Scheduled tasks:**

```bash
# Run every Monday 17:00 Beijing time (09:00 UTC)
0 9 * * 1 podman run --rm --env-file .env \
  -v /path/to/feeds.json:/app/feeds.json:ro \
  -v /path/to/output:/app/output \
  -v /path/to/knowledge:/app/knowledge \
  sift:latest run
```

## Local Running

```bash
git clone <repo> && cd sift
pip install -r requirements.txt        # CLI only
# pip install -r requirements-ui.txt   # CLI + Web UI (optional)
cp .env.example .env
vi .env          # Fill in your configuration
python3 cli.py run
```

When you need Web UI, install `requirements-ui.txt`, then start:

```bash
streamlit run app.py
```

Web UI provides two pages + sidebar:
- **Dashboard**: Report timeline, topic trend charts, source distribution
- **Article Browsing**: Search by keywords, filter by source, each article supports 👍/👎 feedback
- **Sidebar**: Language preference, workspace switching

## Android (Optional)

One-click deployment under Termux environment:

```bash
git clone <repo> sift && cd sift
bash setup.sh
vi .env
.venv/bin/python3 cli.py run
crond  # Start scheduled tasks
```

## Configuration

`.env` file:

| Variable | Description | Example |
|---|---|---|
| `API_BASE_URL` | LLM API address | `https://api.deepseek.com/v1` |
| `API_KEY` | API key | `sk-xxx` |
| `MODEL_NAME` | Model name | `deepseek-chat` |
| `SMTP_SENDER` | Sender QQ email | `123456@qq.com` |
| `SMTP_AUTH_CODE` | QQ email authorization code | See below |
| `SMTP_RECEIVER` | Receiver email | `123456@qq.com` |
| `SUMMARY_DAYS` | Lookback days | `7` |
| `EMBEDDING_MODEL` | Embedding model name (enable semantic search) | `text-embedding-v3` |

Complete configuration items see `.env.example`.

**QQ email authorization code acquisition**: QQ Mail → Settings → Account → POP3/SMTP Service → Enable → Generate authorization code

## Add/Delete Subscription Sources

Edit `feeds.json`:

```json
{
  "name": "Cloudflare Blog",
  "url": "https://blog.cloudflare.com/rss/",
  "lang": "en"
}
```

Adding a line creates a new source, deleting a line unsubscribes. Supports `source_type: "web"` for websites without RSS.

## Extension: Beyond Tech Reports

The core pipeline (data source → filtering → AI summary → delivery) is domain-agnostic. Switch to a different set of data sources and prompts, and it becomes a completely different report:

| Scenario | Data Source Examples | Summary Focus |
|---|---|---|
| **Tech Report** (default) | GitHub Blog, Meta Engineering, Netflix Tech Blog... | Technical highlights, architecture practices |
| **Financial Research** | Bloomberg Opinion, FT Markets, Wall Street Journal... | Macro signals, policy changes, asset impact |
| **AI Papers** | arXiv (cs.AI/cs.CL/cs.LG), Papers With Code... | New architectures, SOTA breakthroughs, open-source releases |
| **Industry News** | 36Kr, TechCrunch, Product Hunt... | Product launches, financing, market trends |

Implementation: Switch prompt templates via `--profile`, switch data sources via `--feeds`:

```bash
python3 cli.py run --profile tech-weekly                    # Tech report (default sources)
python3 cli.py run --profile finance-weekly --feeds finance.json  # Financial research report
python3 cli.py run --profile papers-weekly --feeds papers.json    # Paper report
```

You can also set different sending times:

```
0 8 * * 1   python3 cli.py run --profile tech-weekly
0 9 * * 1   python3 cli.py run --profile finance-weekly --feeds finance.json
0 8 * * 5   python3 cli.py run --profile papers-weekly --feeds papers.json
```
