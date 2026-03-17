# Roadmap

## ✅ v0.1 — Core MCP Server (Done)

**Goal:** Working MCP server that streams real-time market data to Claude via WebSocket.

- stdio transport (`transports/stdio.py`)
- HTTP/SSE transport (`transports/http.py`)
- Circular buffer (500 messages)
- Tools: `get_latest_message`, `get_recent_messages`, `get_stream_status`, `clear_buffer`
- Auto-reconnect with exponential backoff

---

---

## 🔲 v0.2 — Auth & supabase

**Goal:** Have people auth and connect via gmail or something like that.

**Issues:** There is no persistent database, for example, the alerts that are created are created server wide, meaning the alerts are created for everyone who enters the website. I want people to be able to test out the website immediately once they try it out. I also want people to have a persistent database.

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

**Goal:** Monitor multiple symbols or data sources simultaneously. (Need to do that on the cpp server side)

- Symbol filtering in buffer queries
- Subscribe to multiple symbols on a single WebSocket feed
- (Design spec TBD)

---

## 🔲 v0.5 — PyPI Release & SaaS Hardening

**Goal:** Public release and production-ready hosted service.

- Publish to PyPI (`pip install ark-market-data-mcp`) (done)
- GitHub Actions CI: lint, test, publish on tag
- `docker-compose.yml` for self-hosting
- Changelog and release notes
- Polish `pyproject.toml` metadata