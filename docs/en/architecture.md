# Architecture Design

## Three-Layer Pipeline + Feedback Loop

Sift adopts a three-layer pipeline architecture where data sources, processing logic, and delivery channels are fully decoupled, with user feedback automatically driving preference evolution:

```
Sources ──▶ Pipeline ◀──▶ KnowledgeStorage ◀──▶ Channels
                                ▲
                                │
                                ▼
                             Web UI
```

All components interact around KnowledgeStorage (knowledge.db), Pipeline handles fetching, deduplication, summarization, and delivery.

## Data Source Layer (Sources)

Each source only needs to implement the `fetch(since) -> FeedResult` interface:

| Source Type | Status | Description |
|---|---|---|
| **RSS/Atom** | ✅ Implemented | Supports all standard RSS/Atom sources |
| **Web Crawler** | ✅ Implemented | CSS selector extraction, adapts to websites without RSS |
| **API Interface** | 🔜 Extensible | Access to platforms requiring APIs like Twitter/Telegram/Zhihu |

## Delivery Layer (Channels)

Each channel only needs to implement the `send(digest) -> bool` interface:

| Channel | Status | Description |
|---|---|---|
| **Email** | ✅ Implemented | SMTP sending, supports QQ Mail / Gmail etc. |
| **File** | ✅ Implemented | Save as local Markdown file |
| **GitHub Pages** | ✅ Implemented | Automatically generate static website |
| **WeChat Official Account** | 🔜 Extensible | Requires certified service account + template message API |
| **Xiaohongshu** | 🔜 Extible | Requires reverse API or RPA solution |
| **Telegram Bot** | 🔜 Extensible | Bot API direct sending, low integration cost |
| **Discord / Slack** | 🔜 Extensible | Webhook sending, low integration cost |

## Extension Method

Adding a new channel only requires 3 steps:

```python
# 1. Create channels/wechat.py
class WechatChannel(BaseChannel):
    @property
    def name(self) -> str:
        return "wechat"

    def send(self, digest: Digest) -> bool:
        # Call WeChat Official Account template message API
        ...

# 2. Register in sift/cli.py's cmd_run
channels=[FileChannel(), EmailChannel(), WechatChannel()]

# 3. Add configuration in .env
# WECHAT_APPID=your-appid
# WECHAT_SECRET=your-secret
```

Adding a data source is similar, just implement the `BaseSource.fetch()` interface.

## Technical Solution

```
Data source fetching (parallel) → Filter recent N days → Store in knowledge base → Inject historical trends → LLM generates Chinese summary → Deliver to channels
```

**Why start with email?** SMTP is the most mature automated sending solution, can run with just a few lines of code, zero maintenance cost, viewable on both phone and computer. But the architecture is not tied to email—other channels (WeChat Official Account, Telegram, etc.) are also plugins that can be added anytime.

## Feedback-Driven Preference System

Sift doesn't require manual selection of "focus areas"—the system automatically learns preferences from your behavior.

### How It Works

```
User browses article → Clicks 👍/👎 → Feedback written to DB
                                        │
                                        ▼
                              Feedback Engine summarizes
                              ├── Topic weights (topics with more 👍 → higher weight)
                              ├── Source weights (sources with more 👍 → higher weight)
                              └── Negative signals (topics/sources with more 👍 → downweighted)
                                        │
                                        ▼
                              Next report generation
                              ├── Topic weights injected into prompt (focus on user-interested areas)
                              ├── Source weights affect sorting (high-weight sources shown first)
                              └── Downweighted content appears less frequently
```

### Feedback Sifts

| Interaction | What's Learned |
|---|---|
| 👍 | This topic/source is valuable, give more related content next time |
| 👎 | Not interested in this topic/source, reduce frequency |
| No action | Neutral, doesn't affect weights |

### Difference from Manual Settings

| | Manual Settings (Old) | Feedback-Driven (New) |
|---|---|---|
| User burden | Select from 15 topics | Just click 👍/👎 on articles |
| Accuracy | Users aren't sure what they want | Inferred from actual reading behavior |
| Adaptability | Static, doesn't change after selection | Dynamic, weights follow interest changes |
| Cold start | None (manual selection works) | No feedback in early periods, uses default strategy |

## Knowledge Accumulation

Each time a report is generated, the system automatically stores articles in a local SQLite database (`workspaces/default/knowledge.db`), gradually building your technical knowledge base:

- **Article storage**: All fetched articles are automatically stored, deduplicated by hash, no duplicate storage
- **Feedback accumulation**: User's 👍/👎 on articles persistently stored, forming preference profile
- **Trend tracking**: Automatically extract topic keywords, track frequency by week, detect rising trend topics
- **Semantic search**: After configuring embedding model, supports natural language similarity search (e.g., "LLM security related articles")
- **Trend injection**: When generating reports, the system injects historical high-frequency topics and rising trends as context into LLM, allowing summaries to reference long-term trends and avoid starting from scratch each time
- **Preference injection**: When generating reports, Feedback Engine's aggregated topic/source weights are automatically injected into prompt, making summaries align with user interests

**Why use SQLite + sqlite-vec?**
- Single file storage (`workspaces/default/knowledge.db`), zero operations, can run directly on phone
- Structured queries (filter by time, source) and vector search (semantic similarity) share the same database
- sqlite-vec is an official SQLite extension, pure C implementation, no external dependencies

**Configure embedding (optional)**: Set `EMBEDDING_MODEL` in `.env` to point to the embedding model name supported by your API to enable semantic search. Not configuring it doesn't affect core functionality—article storage, trend analysis, and report generation work as usual.

## Implementation Details

### Database Schema Changes

Add `feedback` table in `knowledge.db`:

```sql
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL REFERENCES articles(id),
    signal INTEGER NOT NULL,  -- +1 = 👍, -1 = 👎
    created_at TEXT DEFAULT datetime('now'),
    UNIQUE(article_id)        -- Each article can only have one feedback (overwritable)
);
CREATE INDEX IF NOT EXISTS idx_feedback_article ON feedback(article_id);
```

`articles` table unchanged—`tags` field already stores article topics, used for weight aggregation during JOIN.

### Feedback Engine

Add `processors/feedback.py`, responsible for:

```python
class FeedbackEngine:
    def get_topic_weights(self) -> dict[str, float]:
        """Summarize topic weights: Σ(feedback.signal) GROUP BY tag, normalized to [-1, 1]."""

    def get_source_weights(self) -> dict[str, float]:
        """Summarize source weights: Σ(feedback.signal) GROUP BY source, normalized to [-1, 1]."""

    def build_preference_context(self) -> str:
        """Generate preference context text, injected into prompt.
        Positive weight topics: 'User is more interested in XX direction, can focus more'
        Negative weight topics: 'User has lower interest in XX direction, reduce coverage'
        """
```

### Pipeline Integration

In `pipeline.py`'s `run()` method, inject preference context before generating summary:

```python
# Existing: trend context
trend_ctx = self.storage.generate_trend_context()

# New: preference context
preference_ctx = self.storage.build_preference_context()

# Merge and inject into prompt
context = "\n\n".join(filter(None, [trend_ctx, preference_ctx]))
digest = self.summarize_processor.process(results, trend_context=context)
```

### Web UI Changes

| Page | Changes |
|---|---|
| **Dashboard** | Unchanged |
| **Article Browsing** | Add 👍/👎 buttons to each article card, click to write to `feedback` table |
| **Settings Page** | Removed (manual checkbox preferences removed) |
| **Sidebar** | Keep language selection, workspace switching |

### Changed Files List

| File | Changes |
|---|---|
| `storage/knowledge.py` | Add `save_feedback()`, `get_topic_weights()`, `get_source_weights()`, `build_preference_context()` |
| `processors/feedback.py` | New file, Feedback Engine logic |
| `pipeline.py` | Inject preference context in `run()` |
| `pages/articles.py` | Add 👍/👎 buttons to each article |
| `pages/settings.py` | Remove |
| `app.py` | Remove settings page navigation |
| `tests/test_all.py` | Add feedback related tests |

### Cold Start Strategy

When there's no feedback in the first N periods, the system uses the default strategy (current full summary). After feedback accumulates to threshold (e.g., ≥10 items), preference injection is automatically enabled. Configurable via environment variable `FEEDBACK_THRESHOLD`.
