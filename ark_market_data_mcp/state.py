from collections import deque
from collections.abc import Sequence
from typing import Any

from .market.alerts import AlertManager
from .config import MAX_BUFFER_SIZE


class MarketState:
    """Shared state between the WebSocket stream and MCP tools."""

    def __init__(self) -> None:
        self.buffer: deque[dict[str, Any]] = deque(maxlen=MAX_BUFFER_SIZE)
        self.latest_message: str | None = None
        self.ws_connection = None  # type: ignore[assignment]
        self.message_count: int = 0  # Lifetime counter, never resets
        self.alert_manager: AlertManager = AlertManager()

    def add_message(self, raw: str, parsed: dict[str, Any], max_size: int = MAX_BUFFER_SIZE) -> None:
        self.latest_message = raw
        self.buffer.append(parsed)
        self.message_count += 1
        # max_size is kept for backwards compat but deque handles it automatically

    def get_latest(self) -> str | None:
        return self.latest_message

    def get_recent(self, count: int) -> Sequence[dict[str, Any]]:
        if not self.buffer:
            return []
        return list(self.buffer)[-count:]

    def clear(self) -> None:
        self.buffer.clear()
