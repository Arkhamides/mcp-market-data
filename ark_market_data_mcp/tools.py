import json
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .config import WS_URI
from .state import MarketState, SessionRegistry
from .market.analysis import compute_summary
from .market.store import OHLCVStore, TIER_LIMITS, OHLCV_TIER
from .market.backtest import run_backtest, BacktestError

def _get_session_id(app: Server) -> str:
    try:
        ctx = app.request_context
        if ctx.request is not None:
            sid = ctx.request.headers.get("mcp-session-id")
            if sid:
                return sid
    except LookupError:
        pass
    return "stdio"


def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_latest_message",
            description="Get the most recent market message received from the WebSocket stream.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_recent_messages",
            description="Get the last N market messages from the stream buffer (max 500).",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of recent messages to return (default: 10, max: 500)",
                        "default": 10,
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="get_stream_status",
            description="Check the status of the WebSocket connection and how many messages have been buffered.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="clear_buffer",
            description="Clear the market data message buffer.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_market_summary",
            description="Get structured order book analysis (best bid/ask, spread, volumes, imbalance, price change).",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Market symbol (e.g., 'BTC-USD'). Defaults to most recent message's symbol.",
                        "default": "BTC-USD",
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="set_price_alert",
            description="Set a price alert that triggers when a symbol's price crosses a threshold.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Market symbol (e.g., 'BTC-USD')",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["above", "below"],
                        "description": "Trigger if price goes above or below threshold",
                    },
                    "price": {
                        "type": "number",
                        "description": "Price threshold",
                    },
                    "label": {
                        "type": "string",
                        "description": "Optional label for the alert",
                    },
                },
                "required": ["symbol", "direction", "price"],
            },
        ),
        Tool(
            name="set_percent_change_alert",
            description="Set a percent change alert that triggers when price movement exceeds a threshold.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Market symbol (e.g., 'BTC-USD')",
                    },
                    "threshold_pct": {
                        "type": "number",
                        "description": "Absolute percentage threshold (e.g., 2.5 for ±2.5%)",
                    },
                    "window": {
                        "type": "integer",
                        "description": "Number of messages to analyze (default 10)",
                        "default": 10,
                    },
                },
                "required": ["symbol", "threshold_pct"],
            },
        ),
        Tool(
            name="get_alerts",
            description="Get all active and triggered alerts with their current status.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_ohlcv",
            description=(
                "Get recent closed OHLCV candles for a symbol at a given resolution "
                "(1m or 5m). Returns candles oldest-first. "
                f"Free tier: up to {TIER_LIMITS['free']} candles."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Market symbol (e.g. 'BTC-USD')",
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["1m", "5m"],
                        "description": "Candle resolution (default: '1m')",
                        "default": "1m",
                    },
                    "count": {
                        "type": "integer",
                        "description": f"Number of candles to return (default: 50, max: {TIER_LIMITS[OHLCV_TIER]})",
                        "default": 50,
                    },
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_candles_range",
            description=(
                "Get OHLCV candles between two Unix timestamps (seconds, inclusive). "
                "Returns candles oldest-first. "
                f"Free tier: up to {TIER_LIMITS['free']} candles per query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Market symbol (e.g. 'BTC-USD')",
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["1m", "5m"],
                        "description": "Candle resolution (default: '1m')",
                        "default": "1m",
                    },
                    "start": {
                        "type": "integer",
                        "description": "Range start as Unix timestamp (seconds)",
                    },
                    "end": {
                        "type": "integer",
                        "description": "Range end as Unix timestamp (seconds)",
                    },
                },
                "required": ["symbol", "start", "end"],
            },
        ),
        Tool(
            name="run_backtest",
            description=(
                "Simulate a trading strategy against historical OHLCV candles. "
                "Accepts structured buy/sell rules with percent_change or price_threshold conditions. "
                "Conditions fire every candle the signal is true (not only on first crossing — "
                "a sustained move will trigger multiple trades, like DCA). "
                "Returns P&L, max drawdown, trade count, and full trade log. "
                f"Free tier: up to {TIER_LIMITS['free']} candles."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Market symbol (e.g. 'BTC-USD')",
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["1m", "5m"],
                        "description": "Candle resolution (default: '1m')",
                        "default": "1m",
                    },
                    "rules": {
                        "type": "array",
                        "description": (
                            "List of trading rules. Each rule has an action (buy/sell), "
                            "amount_usd (dollar amount per trigger), and a condition."
                        ),
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["buy", "sell"],
                                    "description": "Whether this rule triggers a buy or sell",
                                },
                                "amount_usd": {
                                    "type": "number",
                                    "description": "Dollar amount to buy or sell per trigger",
                                },
                                "condition": {
                                    "type": "object",
                                    "description": "The signal condition that triggers this rule",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["percent_change", "price_threshold"],
                                        },
                                        "direction": {
                                            "type": "string",
                                            "enum": ["up", "down"],
                                            "description": "Used with percent_change",
                                        },
                                        "percent": {
                                            "type": "number",
                                            "description": "Used with percent_change: threshold % (e.g. 10.0 for 10%)",
                                        },
                                        "window": {
                                            "type": "integer",
                                            "description": "Used with percent_change: candles to look back (default: 1)",
                                            "default": 1,
                                        },
                                        "cross": {
                                            "type": "string",
                                            "enum": ["above", "below"],
                                            "description": "Used with price_threshold",
                                        },
                                        "threshold": {
                                            "type": "number",
                                            "description": "Used with price_threshold: absolute price level",
                                        },
                                    },
                                    "required": ["type"],
                                },
                            },
                            "required": ["action", "amount_usd", "condition"],
                        },
                    },
                    "count": {
                        "type": "integer",
                        "description": f"Number of recent candles to use (default: 200, max: {TIER_LIMITS[OHLCV_TIER]})",
                        "default": 200,
                    },
                    "start": {
                        "type": "integer",
                        "description": "Range start as Unix timestamp (seconds). If provided, end is also required.",
                    },
                    "end": {
                        "type": "integer",
                        "description": "Range end as Unix timestamp (seconds). If provided, start is also required.",
                    },
                    "initial_capital": {
                        "type": "number",
                        "description": "Starting cash in USD (default: 1000.0)",
                        "default": 1000.0,
                    },
                },
                "required": ["symbol", "rules"],
            },
        ),
    ]


async def call_tool(
    name: str,
    arguments: dict[str, Any],
    app: Server,
    state: MarketState,
    session_registry: SessionRegistry,
    ohlcv_store: OHLCVStore = None,
) -> list[TextContent]:
    if name == "get_latest_message":
        latest = state.get_latest()
        if latest is None:
            return [TextContent(type="text", text="No messages received yet.")]
        return [TextContent(type="text", text=f"Latest message:\n{latest}")]

    elif name == "get_recent_messages":
        count = int(arguments.get("count", 10))
        if count < 1:
            count = 1
        if count > 500:
            count = 500

        recent = state.get_recent(count)
        if not recent:
            return [TextContent(type="text", text="Buffer is empty. No messages received yet.")]
        formatted = json.dumps(list(recent), indent=2)
        return [TextContent(type="text", text=f"Last {len(recent)} message(s):\n{formatted}")]

    elif name == "get_stream_status":
        status = {
            "connected": state.ws_connection is not None,
            "uri": WS_URI,
            "buffered_messages": len(state.buffer),
            "message_count": state.message_count,
            "latest_message_preview": (state.get_latest()[:200] if state.get_latest() else None),
        }
        return [TextContent(type="text", text=json.dumps(status, indent=2))]

    elif name == "clear_buffer":
        state.clear()
        return [TextContent(type="text", text="Buffer cleared.")]

    elif name == "get_market_summary":
        symbol = arguments.get("symbol")
        summary = compute_summary(list(state.buffer), symbol)
        formatted = json.dumps(summary, indent=2)
        return [TextContent(type="text", text=f"Market Summary:\n{formatted}")]

    elif name == "set_price_alert":
        symbol = arguments.get("symbol")
        direction = arguments.get("direction")
        price = float(arguments.get("price"))
        label = arguments.get("label", "")

        if direction not in ("above", "below"):
            return [TextContent(type="text", text="Error: direction must be 'above' or 'below'")]

        alert_manager = session_registry.get_or_create(_get_session_id(app))
        alert_id = alert_manager.add_price_alert(symbol, direction, price, label)
        return [TextContent(type="text", text=json.dumps({
            "alert_id": alert_id,
            "message": f"Price alert set for {symbol} (trigger if price goes {direction} {price})"
        }, indent=2))]

    elif name == "set_percent_change_alert":
        symbol = arguments.get("symbol")
        threshold_pct = float(arguments.get("threshold_pct"))
        window = int(arguments.get("window", 10))

        alert_manager = session_registry.get_or_create(_get_session_id(app))
        alert_id = alert_manager.add_percent_change_alert(symbol, threshold_pct, window)
        return [TextContent(type="text", text=json.dumps({
            "alert_id": alert_id,
            "message": f"Percent change alert set for {symbol} (trigger if change >= ±{threshold_pct}% over {window} messages)"
        }, indent=2))]

    elif name == "get_alerts":
        alert_manager = session_registry.get_or_create(_get_session_id(app))
        alerts = alert_manager.get_all()
        formatted = json.dumps(alerts, indent=2, default=str)
        return [TextContent(type="text", text=f"All Alerts ({len(alerts)} total):\n{formatted}")]

    elif name == "get_ohlcv":
        if ohlcv_store is None:
            return [TextContent(type="text", text="Historical store not available.")]
        symbol = arguments.get("symbol", "")
        if not symbol:
            return [TextContent(type="text", text="Error: symbol is required.")]
        resolution = arguments.get("resolution", "1m")
        count = int(arguments.get("count", 50))
        candles = ohlcv_store.get_recent(symbol, resolution, count)
        if not candles:
            return [TextContent(type="text", text=f"No {resolution} candles found for {symbol} yet. Data accumulates as the stream runs.")]
        return [TextContent(type="text", text=json.dumps(candles, indent=2))]

    elif name == "get_candles_range":
        if ohlcv_store is None:
            return [TextContent(type="text", text="Historical store not available.")]
        symbol = arguments.get("symbol", "")
        if not symbol:
            return [TextContent(type="text", text="Error: symbol is required.")]
        resolution = arguments.get("resolution", "1m")
        start = arguments.get("start")
        end = arguments.get("end")
        if start is None or end is None:
            return [TextContent(type="text", text="Error: start and end timestamps are required.")]
        start, end = int(start), int(end)
        if start > end:
            return [TextContent(type="text", text="Error: start must be <= end.")]
        candles = ohlcv_store.get_range(symbol, resolution, start, end)
        if not candles:
            return [TextContent(type="text", text=f"No {resolution} candles found for {symbol} in the requested range.")]
        return [TextContent(type="text", text=json.dumps(candles, indent=2))]

    elif name == "run_backtest":
        if ohlcv_store is None:
            return [TextContent(type="text", text="Historical store not available.")]
        symbol = arguments.get("symbol", "")
        if not symbol:
            return [TextContent(type="text", text="Error: symbol is required.")]
        resolution = arguments.get("resolution", "1m")
        rules = arguments.get("rules")
        if not rules:
            return [TextContent(type="text", text="Error: rules array is required.")]
        initial_capital = float(arguments.get("initial_capital", 1000.0))
        if initial_capital <= 0:
            return [TextContent(type="text", text="Error: initial_capital must be positive.")]
        start = arguments.get("start")
        end = arguments.get("end")
        if start is not None and end is not None:
            start, end = int(start), int(end)
            if start > end:
                return [TextContent(type="text", text="Error: start must be <= end.")]
            candles = ohlcv_store.get_range(symbol, resolution, start, end)
        else:
            count = int(arguments.get("count", 200))
            candles = ohlcv_store.get_recent(symbol, resolution, count)
        if not candles:
            return [TextContent(type="text", text=(
                f"No {resolution} candles found for {symbol}. "
                "Seed historical data first: python scripts/seed_historical.py"
            ))]
        try:
            result = run_backtest(
                candles=candles,
                rules=rules,
                initial_capital=initial_capital,
                symbol=symbol,
                resolution=resolution,
            )
        except BacktestError as exc:
            return [TextContent(type="text", text=f"Backtest configuration error: {exc}")]
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
