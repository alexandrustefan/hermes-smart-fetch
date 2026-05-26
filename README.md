# hermes-smart-fetch

**Smart web extraction for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — browser-grade TLS fingerprinting + Defuddle content cleanup. No API key required.**

Hermes Agent plugin that wraps [@thinkscape/smart-fetch](https://github.com/Thinkscape/agent-smart-fetch) CLI to give your agent a local, unlimited, Cloudflare-friendly web extraction backend.

| | Tavily | Firecrawl | http-fetch | **hermes-smart-fetch** |
|---|---|---|---|---|
| **Cloudflare bypass** | ❌ | ✅ (headless Chrome) | ❌ | ✅ (TLS fingerprinting) |
| **Clean extraction** | ✅ | ✅ | ✅ (bs4) | ✅ (Defuddle) |
| **API key required** | ✅ | ✅ | ❌ | ❌ |
| **Rate limits** | 1,000/mo free | 500/mo free | Unlimited | Unlimited |
| **Cost** | Paid tiers | Paid tiers | Free | Free |
| **Runs locally** | ❌ | ❌ | ✅ | ✅ |

## Features

- 🔐 **Browser-like TLS/SSL + HTTP fingerprints** — bypasses Cloudflare, Akamai, and other bot defenses
- 🧹 **Defuddle extraction** — clean, readable markdown (strips nav, sidebars, footers, share widgets)
- 🧠 **Rich metadata** — title, author, published date, language, word count
- 📦 **Batch fetch** — multiple URLs with bounded concurrency
- 📝 **Multiple output formats** — markdown (default), html, text, raw
- 🚫 **Zero config** — no API keys, no accounts, no credits
- 🔌 **Dual integration** — works as both `web_extract` backend AND standalone `web_fetch` tool

## Architecture

```
hermes-smart-fetch/
├── __init__.py              # Plugin entry point (register function)
├── provider.py              # WebSearchProvider — web_extract backend
├── smart_fetch_client.py    # CLI bridge to @thinkscape/smart-fetch
├── tools.py                 # Standalone web_fetch + batch_web_fetch tools
└── plugin.yaml              # Hermes plugin manifest
```

Same pattern as [pi-smart-fetch](https://github.com/Thinkscape/agent-smart-fetch/tree/main/packages/pi-smart-fetch) and [openclaw-smart-fetch](https://github.com/Thinkscape/agent-smart-fetch/tree/main/packages/openclaw-smart-fetch) — a thin adapter around the `smart-fetch-core` engine, adapted for the Hermes Agent plugin API.

## Quick Start

### 1. Install the smart-fetch CLI

```bash
npm install -g @thinkscape/smart-fetch
# Provides both `smart-fetch` and `sf` binaries
```

### 2. Install the plugin

**Option A — Symlink (recommended for development):**
```bash
ln -s ~/Documents/projects/hermes-smart-fetch ~/.hermes/plugins/hermes-smart-fetch
```

**Option B — hermes plugins install:**
```bash
hermes plugins install ~/Documents/projects/hermes-smart-fetch --enable
```

### 3. Configure as extract backend

```yaml
# ~/.hermes/config.yaml
web:
  backend: ddgs                # search backend (stays as-is)
  extract_backend: hermes-smartfetch  # extract via smart-fetch
```

### 4. Restart Hermes

```bash
# CLI: exit and restart hermes
# Gateway: /restart, then /reset
```

## Usage

### As `web_extract` backend (transparent)

Once configured, `web_extract` calls route through smart-fetch automatically:

```
User: "What's on this page? https://example.com/article"
Agent: [calls web_extract → smart-fetch → returns clean content]
```

### Standalone `web_fetch` tool

For direct control over browser profile, format, etc.:

```python
web_fetch(url="https://example.com")
web_fetch(url="https://example.com", browser="firefox_147", os="linux")
web_fetch(url="https://example.com", format="text", maxChars=10000)
```

### Batch `batch_web_fetch` tool

Fetch multiple URLs concurrently:

```python
batch_web_fetch(
    urls=["https://example.com/a", "https://example.com/b"],
    concurrency=4,
)
```

## Configuration

### Environment variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_FETCH_BROWSER` | `chrome_145` | Default browser profile |
| `SMART_FETCH_OS` | `macos` | Default OS profile |
| `SMART_FETCH_MAX_CHARS` | `50000` | Max characters per fetch |
| `SMART_FETCH_TIMEOUT_MS` | `15000` | Request timeout |

### Per-capability split

Use different providers for search vs extract:

```yaml
web:
  search_backend: ddgs           # DuckDuckGo for search (free)
  extract_backend: smartfetch    # smart-fetch for extraction (free)
```

Or combine with Tavily for search and smart-fetch for extraction:

```yaml
web:
  search_backend: tavily         # Tavily for search
  extract_backend: smartfetch    # smart-fetch for extraction
```

## How it works

```
web_extract(urls)
  │
  ├─ provider.py: SmartFetchWebSearchProvider.extract()
  ├─ smart_fetch_client.py: smart_fetch(urls)
  │   ├─ Locate smart-fetch / sf binary (or npx fallback)
  │   ├─ Build CLI args (browser, os, format, max-chars, ...)
  │   ├─ subprocess.run(smart-fetch --verbose --format markdown <urls>)
  │   └─ Parse verbose output → FetchResult per URL
  └─ Return standard Hermes response shape [{url, title, content, ...}]
```

## Supported browser profiles

| Profile | TLS fingerprint |
|---------|----------------|
| `chrome_145` | Chrome 145 on Windows (default) |
| `firefox_147` | Firefox 147 |
| `safari_26` | Safari 26 |
| `edge_145` | Edge 145 |
| `opera_127` | Opera 127 |

## Site optimizations

Defuddle has specialized extractors for:

- YouTube pages and transcripts
- Reddit posts and comment threads
- X / Twitter posts
- GitHub pages, issues, PRs, and discussions
- Hacker News threads
- Substack posts
- Pages with code blocks, footnotes, math, and callouts

## Troubleshooting

### "smart-fetch CLI not found"

Install the CLI:
```bash
npm install -g @thinkscape/smart-fetch
```

Or verify npx works:
```bash
npx @thinkscape/smart-fetch https://example.com
```

### Cloudflare-protected pages still blocked

Try a different browser profile:
```bash
smart-fetch https://target-site.com --browser firefox_147 --os linux
```

Or set via environment:
```bash
export SMART_FETCH_BROWSER=firefox_147
export SMART_FETCH_OS=linux
```

### Slow first run

The first `npx` invocation downloads the package (~5MB). Subsequent runs are instant. Global install avoids this entirely.

## License

MIT — same as [@thinkscape/smart-fetch](https://github.com/Thinkscape/agent-smart-fetch).
