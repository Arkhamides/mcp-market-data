# ARK Market Data MCP — Project Context

## Overview

This is a **Model Context Protocol (MCP) server** written in Python that bridges Claude (or any MCP client) to a real-time market data WebSocket stream. It continuously receives market data from a remote WebSocket server and exposes it to Claude via MCP tools.

- **Package**: `ark-market-data-mcp`
- **Version**: 0.1.1
- **Python**: >= 3.8
- **Entry point**: `ark_market_data_mcp.transports.stdio:main`

## Architecture

```
Claude (User)
    │  MCP Protocol (stdio)
    ▼
MCP Server (server.py)
    ├── Shared State (state.py)   ← in-memory circular buffer
    ├── Tools (tools.py)          ← 8 MCP tools exposed to Claude
    └── WebSocket Task (stream.py)
            │  WebSocket (WS_URI)
            ▼
    Remote Market Data Server
```

Two concurrent async tasks run inside the server:
1. **WebSocket streaming** (background) — connects, subscribes, and buffers incoming messages
2. **MCP stdio server** (foreground) — handles Claude tool calls

## Directory Structure

```
ark_market_data_mcp/
├── __init__.py          # Package init
├── __main__.py          # Async entry point (python -m ark_market_data_mcp)
├── config.py            # Environment config & constants
├── server.py            # MCP server orchestration + main()
├── state.py             # MarketState class (shared in-memory state)
├── tools.py             # MCP tool definitions and handlers
├── market/
│   ├── __init__.py      # Market subpackage
│   ├── stream.py        # WebSocket connection + auto-reconnect loop
│   ├── alerts.py        # AlertManager class for price/percent change alerts
│   └── analysis.py      # Market analysis functions (compute_summary)
└── transports/
    ├── __init__.py      # Transports subpackage
    ├── stdio.py         # Stdio transport entry point
    └── http.py          # HTTP transport (alternative transport)
```

## Key Modules

### `config.py`
Reads environment variables and defines constants:
- `WS_URI` — WebSocket endpoint
- `SUBSCRIBE_MSG` — subscription payload sent on connect
- `MAX_BUFFER_SIZE` — circular buffer cap (500 messages)

### `state.py` — `MarketState`
Shared state object passed between the streaming task and tool handlers:
- `buffer: deque[dict]` — circular buffer of parsed messages (max 500)
- `latest_message: str` — raw text of the most recent message
- `ws_connection` — active WebSocket connection (or `None`)
- `message_count: int` — lifetime message counter (never resets)
- `alert_manager: AlertManager` — manages price and percent change alerts
- Methods: `add_message()`, `get_latest()`, `get_recent(count)`, `clear()`

### `stream.py` — `connect_and_stream(state)`
Background async task:
1. Connects to `WS_URI`
2. Sends `{"event": "subscribe_aggregated_market"}`
3. Parses and buffers incoming JSON messages into `MarketState`
4. Auto-reconnects with exponential backoff on failure (3s / 5s delays)

### `tools.py` — MCP Tools
Exposes 8 tools to Claude:

| Tool | Input | Description |
|------|-------|-------------|
| `get_latest_message` | — | Returns the most recent raw message |
| `get_recent_messages` | `count` (1–500, default 10) | Returns last N buffered messages as JSON |
| `get_stream_status` | — | Returns connection status and buffer info |
| `clear_buffer` | — | Clears the in-memory message buffer |
| `get_market_summary` | `symbol` (e.g., 'BTC-USD', defaults to most recent) | Returns structured order book analysis (best bid/ask, spread, volumes, imbalance, price change) |
| `set_price_alert` | `symbol`, `direction` ("above"/"below"), `price`, optional `label` | Sets a price alert that triggers when price crosses threshold |
| `set_percent_change_alert` | `symbol`, `threshold_pct`, optional `window` (default 10) | Sets a percent change alert that triggers on price movement |
| `get_alerts` | — | Returns all active and triggered alerts with their current status |

### `server.py` — `main()`
Orchestrates startup:
1. Instantiates `MarketState`
2. Launches `connect_and_stream` as a background asyncio task
3. Starts the MCP stdio server (`mcp.run_stdio_async`)
4. Handles graceful shutdown on cancellation

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_URI` | `ws://localhost:9002` | WebSocket market data endpoint |

## Dependencies

- `mcp >= 0.1.0` — Anthropic's MCP framework
- `websockets >= 12.0` — WebSocket client

## Design Patterns

- **Async/Await** throughout using `asyncio`
- **Circular buffer** for bounded memory usage (max 500 messages)
- **Separation of concerns**: server / stream / state / tools / config are each isolated
- **Auto-reconnect** with backoff for resilient WebSocket handling
- **Shared mutable state** passed by reference between tasks (no queues needed at this scale)
