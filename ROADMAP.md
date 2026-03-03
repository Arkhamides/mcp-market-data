# Roadmap

## ✅ v0.1 — Core MCP Server (Done)

**Goal:** Working MCP server that streams real-time market data to Claude via WebSocket.

- stdio transport (local Claude integration)
- Circular buffer (500 messages)
- Tools: `get_latest_message`, `get_recent_messages`, `get_stream_status`, `clear_buffer`
- Auto-reconnect with exponential backoff

---

## ✅ v0.1.1 — HTTP Transport & Docker (Done)

**Goal:** Enable remote access and containerised deployment.

- HTTP/SSE transport (`transports/http.py`)
- `Dockerfile` using `python:3.11-slim`
- Entry point: `ark-market-data-mcp-http`
- Environment config: `HTTP_HOST`, `HTTP_PORT`, `WS_URI`

---

## 🔲 v0.2 — Auth & Security

**Goal:** Protect the hosted HTTP/SSE endpoint so only authenticated SaaS customers can connect.

- Validate API keys on every `/sse` connection via an external auth service
- Reject unauthenticated requests with `401 Unauthorized`
- API key passed as query parameter: `/sse?api=YOUR_KEY`
- Document auth flow in README

---

## 🔲 v0.3 — Market Analysis & Alerts

**Goal:** Make Claude genuinely useful for trading decisions.

**Analysis tools**
- `get_market_summary` — bid/ask/spread/imbalance/price change (implemented, needs polish)
- Volatility metrics
- Volume spike detection
- Trend direction

**Alert management**
- `set_price_alert`, `set_percent_change_alert` (implemented)
- `get_alerts` (implemented)
- `delete_alert` — cancel a specific alert by ID
- `clear_triggered_alerts` — remove all fired alerts

**Alert delivery**
- MCP tool polling (implemented)
- Email notifications
- Telegram notifications

---

## 🔲 v0.4 — Multi-asset / Multi-feed Support

**Goal:** Monitor multiple symbols or data sources simultaneously.

- Symbol filtering in buffer queries
- Subscribe to multiple symbols on a single WebSocket feed
- (Design spec TBD)

---

## 🔲 v0.5 — PyPI Release & SaaS Hardening

**Goal:** Public release and production-ready hosted service.

- Publish to PyPI (`pip install ark-market-data-mcp`)
- GitHub Actions CI: lint, test, publish on tag
- `docker-compose.yml` for self-hosting
- Changelog and release notes
- Polish `pyproject.toml` metadata
