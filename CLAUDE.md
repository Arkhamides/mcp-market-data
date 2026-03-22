# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

MCP server written in Python that bridges Claude to a real-time market data WebSocket stream. Exposes 8 MCP tools for reading buffered market data and setting price alerts.

- **Package**: `ark-market-data-mcp` / `mcp-market-data` (pyproject.toml name)
- **Python**: >= 3.8
- **Entry points**: `ark-market-data-mcp` (stdio) and `ark-market-data-mcp-http` (HTTP)

## Development Commands

```bash
# Install in editable mode (required before running)
pip install -e .

# Run stdio transport (for Claude Desktop / MCP CLI clients)
ark-market-data-mcp
# or
python -m ark_market_data_mcp

# Run HTTP transport (for Claude Code and modern MCP clients, binds to :3001)
ark-market-data-mcp-http

# Build distributable
python -m build

# Environment variables
WS_URI=ws://localhost:9002    # upstream market data WebSocket
HTTP_HOST=0.0.0.0             # HTTP transport bind address
HTTP_PORT=3001                # HTTP transport port
```

No test suite exists yet.

## Architecture

Two transports, one shared MCP app:

```
Claude (User)
    │
    ├─ MCP stdio (transports/stdio.py) ─────────────────┐
    │                                                    │
    └─ MCP HTTP/Streamable (transports/http.py, :3001) ─┤
              also exposes /websocket proxy              │
                                                         ▼
                                                  server.py
                                              (app + state singletons)
                                                    │         │
                                               tools.py   state.py
                                                              │
                                                        stream.py (background task)
                                                              │
                                                    Remote WebSocket (WS_URI)
```

**`server.py`** defines the `app` (MCP `Server` instance) and `state` (`MarketState`) as module-level singletons. Both transports import these singletons — startup orchestration (launching the stream task, serving) lives in the transport modules, not in `server.py`.

**`transports/http.py`** uses MCP 1.26+ Streamable HTTP (`StreamableHTTPSessionManager`) over a Starlette/uvicorn app. It also exposes a `/websocket` route that proxies raw WebSocket connections directly to `WS_URI` (bidirectional passthrough).

**`transports/stdio.py`** runs the MCP stdio server alongside the WebSocket stream task as two concurrent asyncio tasks.

## Key Modules

### `state.py` — `MarketState`
Shared state passed by reference between stream task and tool handlers:
- `buffer: deque[dict]` — circular buffer, max 500 messages
- `alert_manager: AlertManager` — price/percent-change alerts
- `ws_connection` — live WebSocket handle (or `None`)
- `message_count` — lifetime counter, never resets

### `market/stream.py` — `connect_and_stream(state)`
Background task: connects → subscribes (`subscribe_aggregated_market`) → buffers JSON → auto-reconnects with 3s/5s backoff. Checks `state.alert_manager` on each message.

### `market/alerts.py` — `AlertManager`
Holds price alerts (threshold crossing) and percent-change alerts (rolling window). Evaluated inline during stream ingestion.

### `market/analysis.py` — `compute_summary`
Computes order book statistics (best bid/ask, spread, volume imbalance, price change) from buffered messages for a given symbol.

### `tools.py`
All 8 MCP tools: `get_latest_message`, `get_recent_messages`, `get_stream_status`, `clear_buffer`, `get_market_summary`, `set_price_alert`, `set_percent_change_alert`, `get_alerts`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_URI` | `ws://localhost:9002` | Upstream market data WebSocket |
| `HTTP_HOST` | `0.0.0.0` | HTTP transport bind address |
| `HTTP_PORT` | `3001` | HTTP transport port |

## Dependencies

- `mcp >= 0.1.0` — MCP framework (`StreamableHTTPSessionManager` requires MCP 1.26+)
- `websockets >= 12.0` — WebSocket client
- `uvicorn >= 0.27.0` + `starlette >= 0.36.0` — HTTP transport only
