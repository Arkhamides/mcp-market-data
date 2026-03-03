import json
from typing import Any

from mcp.types import Tool, TextContent

from .config import WS_URI, MAX_ALERTS
from .state import MarketState
from .market.analysis import compute_summary


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
    ]


async def call_tool(name: str, arguments: dict[str, Any], state: MarketState) -> list[TextContent]:
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

        alert_id = state.alert_manager.add_price_alert(symbol, direction, price, label)
        return [TextContent(type="text", text=json.dumps({
            "alert_id": alert_id,
            "message": f"Price alert set for {symbol} (trigger if price goes {direction} {price})"
        }, indent=2))]

    elif name == "set_percent_change_alert":
        symbol = arguments.get("symbol")
        threshold_pct = float(arguments.get("threshold_pct"))
        window = int(arguments.get("window", 10))

        alert_id = state.alert_manager.add_percent_change_alert(symbol, threshold_pct, window)
        return [TextContent(type="text", text=json.dumps({
            "alert_id": alert_id,
            "message": f"Percent change alert set for {symbol} (trigger if change >= ±{threshold_pct}% over {window} messages)"
        }, indent=2))]

    elif name == "get_alerts":
        alerts = state.alert_manager.get_all()
        formatted = json.dumps(alerts, indent=2, default=str)
        return [TextContent(type="text", text=f"All Alerts ({len(alerts)} total):\n{formatted}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
