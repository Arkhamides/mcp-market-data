# Roadmap

## ✅ v0.1 — Core MCP Server (Done)

**Goal:** Working MCP server that streams real-time market data to Claude via WebSocket.

- stdio transport (`transports/stdio.py`)
- HTTP/Streamable transport — MCP 1.26+ (`transports/http.py`) with WebSocket proxy at `/websocket`
- Circular buffer (500 messages)
- Tools: `get_latest_message`, `get_recent_messages`, `get_stream_status`, `clear_buffer`
- Tools: `get_market_summary`, `set_price_alert`, `set_percent_change_alert`, `get_alerts`
- `AlertManager` — price threshold and percent-change alerts
- Auto-reconnect with exponential backoff

---

## 🔲 v0.2 — Session Isolation, Auth & Persistence

**Goal:** Users can try the app immediately with no friction. Authenticated users get persistent state across sessions.

**Phase 1 — Anonymous experience (MCP server)** ✅

- ~~Per-session `AlertManager` and state (keyed by session ID)~~ (done — `SessionRegistry` in `state.py`)
- Session cleanup on disconnect (deferred to Phase 2)

**Phase 2 — Auth & persistence (SvelteKit + MCP server)**

- **SvelteKit** owns the auth flow: Google OAuth via Supabase Auth, session cookies, redirects
- **MCP server** owns persistent data: reads/writes alerts and user preferences to Supabase using the `user_id` from the JWT passed by SvelteKit on each request. Alert evaluation must stay in the MCP server since it runs inside the stream loop.
- On auth: promote the current ephemeral session state to the user's Supabase record
- On return visit: load persisted alerts from Supabase into the new session

---

## 🔲 v0.3 — Market Analysis & Alerts

**Goal:** Make Claude genuinely useful for trading decisions.

**Analysis tools**
- `get_market_summary` — bid/ask/spread/imbalance/price change (implemented, needs data quality improvements and additional fields e.g. 24hr change, VWAP)
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