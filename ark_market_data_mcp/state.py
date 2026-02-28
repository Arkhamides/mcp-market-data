from collections.abc import Sequence
from typing import Any


class MarketState:
    """Shared state between the WebSocket stream and MCP tools."""

    def __init__(self) -> None:
        self.buffer: list[dict[str, Any]] = []
        self.latest_message: str | None = None
        self.ws_connection = None  # type: ignore[assignment]

    def add_message(self, raw: str, parsed: dict[str, Any], max_size: int) -> None:
        self.latest_message = raw
        self.buffer.append(parsed)
        if len(self.buffer) > max_size:
            self.buffer.pop(0)

    def get_latest(self) -> str | None:
        return self.latest_message

    def get_recent(self, count: int) -> Sequence[dict[str, Any]]:
        if not self.buffer:
            return []
        return self.buffer[-count:]

    def clear(self) -> None:
        self.buffer.clear()
