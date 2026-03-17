from collections import deque
from collections.abc import Sequence
from typing import Any

from .market.alerts import AlertManager
from .config import MAX_BUFFER_SIZE, logger


class MarketState:
    """Shared state between the WebSocket stream and MCP tools."""

    def __init__(self) -> None:
        self.buffer: deque[dict[str, Any]] = deque(maxlen=MAX_BUFFER_SIZE)
        self.latest_message: str | None = None
        self.ws_connection = None  # type: ignore[assignment]
        self.message_count: int = 0  # Lifetime counter, never resets

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


class SessionRegistry:
    """Maps MCP session IDs to per-session AlertManagers."""

    def __init__(self) -> None:
        self._sessions: dict[str, AlertManager] = {}

    def get_or_create(self, session_id: str) -> AlertManager:
        if session_id not in self._sessions:
            self._sessions[session_id] = AlertManager()
        return self._sessions[session_id]

    def check_all(self, messages: list[dict[str, Any]]) -> None:
        for session_id, alert_manager in self._sessions.items():
            triggered = alert_manager.check(messages)
            for alert in triggered:
                logger.info(f"[ALERT TRIGGERED] session={session_id} {alert}")
