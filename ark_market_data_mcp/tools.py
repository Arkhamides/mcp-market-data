import json
from typing import Any

from mcp.types import Tool, TextContent

from .config import WS_URI
from .state import MarketState


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
            "latest_message_preview": (state.get_latest()[:200] if state.get_latest() else None),
        }
        return [TextContent(type="text", text=json.dumps(status, indent=2))]

    elif name == "clear_buffer":
        state.clear()
        return [TextContent(type="text", text="Buffer cleared.")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
