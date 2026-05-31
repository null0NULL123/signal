# Signal

Automatically collect content from your information sources, generate structured summaries with AI, and deliver them to your preferred platforms.

English | [中文](../../README.md)

## Background

Do you also face these challenges:

- **Tech professionals**: Engineering blogs and open-source updates are scattered across a dozen sites, English content reads slowly, spending hours weekly browsing is unrealistic
- **Researchers**: Papers, industry reports, and domain news are spread everywhere, wanting to track but always missing key updates
- **Content creators**: Need to continuously track industry trends and hotspots, manual refreshing is too inefficient
- **Business professionals**: Industry news, competitor dynamics, and policy changes are drowned in information overload, can't find the key points

**Core problem**: Scattered information sources + language barriers + limited time = passively missing important content.

**Signal's approach**: Select your information sources → automatic fetching → AI-generated structured summaries → delivery to your preferred platforms. Data sources, processing logic, and delivery channels are fully decoupled, extensible on demand, not aiming for everything, but for precision.

## Architecture

```
Sources ──▶ Pipeline ◀──▶ KnowledgeStorage ◀──▶ Channels
                                ▲
                                │
                                ▼
                             Web UI
```

All components interact around KnowledgeStorage (signal.db), Pipeline handles fetching, deduplication, summarization, and delivery.

→ [Complete Architecture Design](../architecture.md)

## Quick Start

```bash
git clone <repo> && cd signal
pip install -r requirements.txt
cp .env.example .env
vi .env              # Fill in API_KEY and other configurations
python3 cli.py run   # Generate your first weekly report
```

Optional Web UI:

```bash
pip install -r requirements-ui.txt
streamlit run app.py
```

→ [Deployment Guide (GitHub Actions / Android / Configuration Details)](../deployment.md)

## Documentation

| Document | Content |
|---|---|
| [Architecture Design](../architecture.md) | Three-layer pipeline, feedback system, knowledge accumulation, implementation details |
| [Deployment Guide](../deployment.md) | GitHub Actions, local running, Android, configuration, subscription source management |
| [Competitive Analysis](../competitive-analysis.md) | Comparison with RSSHub / Folo / ClawFeed and other projects |

## Testing

```bash
python tests/runner.py          # Run all tests
python tests/runner.py storage  # Run only storage group
python tests/runner.py config   # Run only config group
```

## License

MIT
