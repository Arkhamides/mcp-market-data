"""Alert management system for price and percent change alerts."""
from collections.abc import Sequence
from typing import Any
import time
import uuid

from .analysis import compute_summary


class AlertManager:
    """Manages price and percent change alerts, checks them against incoming messages."""

    def __init__(self) -> None:
        self._alerts: dict[str, dict[str, Any]] = {}  # {alert_id: alert_dict}

    def add_price_alert(self, symbol: str, direction: str, price: float, label: str = "") -> str:
        """
        Add a price alert.

        Args:
            symbol: Market symbol (e.g., "BTC-USD")
            direction: "above" or "below"
            price: Price threshold
            label: Optional label for the alert

        Returns:
            alert_id
        """
        alert_id = str(uuid.uuid4())
        self._alerts[alert_id] = {
            "id": alert_id,
            "type": "price",
            "symbol": symbol,
            "direction": direction,
            "price": price,
            "label": label,
            "triggered": False,
            "triggered_at": None,
            "created_at": time.time(),
        }
        return alert_id

    def add_percent_change_alert(self, symbol: str, threshold_pct: float, window: int = 10) -> str:
        """
        Add a percent change alert.

        Args:
            symbol: Market symbol (e.g., "BTC-USD")
            threshold_pct: Absolute percentage threshold (e.g., 2.5)
            window: Number of messages to look back (default 10)

        Returns:
            alert_id
        """
        alert_id = str(uuid.uuid4())
        self._alerts[alert_id] = {
            "id": alert_id,
            "type": "percent_change",
            "symbol": symbol,
            "threshold_pct": threshold_pct,
            "window": window,
            "triggered": False,
            "triggered_at": None,
            "created_at": time.time(),
        }
        return alert_id

    def check(self, messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Check all active alerts against current buffer.

        Returns list of newly triggered alerts.
        """
        newly_triggered = []

        for alert_id, alert in self._alerts.items():
            # Skip already triggered alerts
            if alert["triggered"]:
                continue

            symbol = alert["symbol"]
            triggered = False

            if alert["type"] == "price":
                # Check price threshold alert
                summary = compute_summary(messages, symbol)
                best_bid = summary.get("best_bid")
                best_ask = summary.get("best_ask")

                direction = alert["direction"]
                price = alert["price"]

                if direction == "above" and best_bid is not None and best_bid > price:
                    triggered = True
                elif direction == "below" and best_ask is not None and best_ask < price:
                    triggered = True

            elif alert["type"] == "percent_change":
                # Check percent change alert
                threshold_pct = alert["threshold_pct"]
                window = alert["window"]

                summary = compute_summary(messages, symbol)
                price_change_pct = summary.get("price_change_pct")

                if price_change_pct is not None and abs(price_change_pct) >= threshold_pct:
                    triggered = True

            # Mark as triggered if condition met
            if triggered:
                alert["triggered"] = True
                alert["triggered_at"] = time.time()
                newly_triggered.append(alert)

        return newly_triggered

    def get_all(self) -> list[dict[str, Any]]:
        """Return all alerts (active + triggered) with status."""
        return list(self._alerts.values())

    def clear_triggered(self) -> int:
        """Remove triggered alerts, return count removed."""
        to_remove = [aid for aid, a in self._alerts.items() if a["triggered"]]
        for aid in to_remove:
            del self._alerts[aid]
        return len(to_remove)
