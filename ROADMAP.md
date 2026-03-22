# Roadmap

## Strategic Vision

**Position:** AI-native backtesting and live validation for crypto strategies, via MCP.

**Promise:** Describe a strategy in chat, get instant backtests on historical data and live forward tests with HFT-grade feeds.

---

## 🔲 Phase A — Historical Data Layer

**Goal:** Give Claude access to enough history to run basic backtests.

- OHLCV ingestion for 1–3 major pairs (BTC, ETH) at 1m/5m resolution
- Local or Supabase-backed historical store
- MCP tools: `get_ohlcv`, `get_historical_range`
- Configurable depth limits per tier (free = shallow, paid = deeper)

---

## 🔲 Phase B — Backtesting Engine

**Goal:** Let Claude run a strategy spec against historical data and return meaningful metrics.

- MCP tool: `run_backtest` — accepts strategy rules (entry/exit conditions as structured input), returns P&L, drawdown, win rate, trade log
- Strategy input format: simple threshold/signal rules expressible from natural language (no arbitrary code execution)
- Run results stored per session; persisted for authenticated users (builds on v0.2 auth)

---

## 🔲 Phase C — Live Forward Testing (Paper Trading)

**Goal:** Forward-test a strategy against the live stream without real execution.

- MCP tool: `start_paper_test` — runs a strategy against incoming stream messages in real time
- MCP tool: `get_paper_test_status` — returns open positions, running P&L, signal log
- MCP tool: `stop_paper_test`
- Multiple concurrent paper tests per session (limit enforced per tier)

---

## 🔲 Phase D — Execution Integrations (BYO-keys)

**Goal:** Let users route validated strategies to their own broker or bot.

- MCP tool: `connect_exchange` — accepts CCXT-compatible credentials (stored encrypted, never logged)
- MCP tool: `place_order` / `cancel_order` — thin wrapper over CCXT, scoped to the session's connected exchange
- Freqtrade strategy export: serialize a backtest-validated strategy to a Freqtrade-compatible config
- Rate limits and safeguards enforced at the MCP layer (max order size, daily loss cap)

---

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