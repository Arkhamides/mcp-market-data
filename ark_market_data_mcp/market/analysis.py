"""Pure order book analysis functions."""
from collections.abc import Sequence
from typing import Any


def compute_summary(messages: Sequence[dict[str, Any]], symbol: str | None = None) -> dict[str, Any]:
    """
    Compute order book summary from recent buffer messages.

    Returns standardized dict with all derived fields:
    - best_bid, best_ask, mid_price, spread
    - bid_volume, ask_volume, book_imbalance
    - price_change_pct (over last 10 messages)
    """
    if not messages:
        return {
            "symbol": symbol or "UNKNOWN",
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread": None,
            "bid_volume": None,
            "ask_volume": None,
            "book_imbalance": None,
            "price_change_pct": None,
            "messages_analyzed": 0,
        }

    # Filter messages by symbol if provided
    if symbol:
        filtered = [m for m in messages if m.get("symbol") == symbol]
    else:
        # Default to most recent message's symbol
        if messages:
            symbol = messages[-1].get("symbol", "UNKNOWN")
        filtered = list(messages)

    if not filtered:
        return {
            "symbol": symbol or "UNKNOWN",
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread": None,
            "bid_volume": None,
            "ask_volume": None,
            "book_imbalance": None,
            "price_change_pct": None,
            "messages_analyzed": 0,
        }

    # Use latest message for order book data
    latest = filtered[-1]
    bids = latest.get("bids", [])
    asks = latest.get("asks", [])

    # Compute best bid/ask
    best_bid = max([b["price"] for b in bids]) if bids else None
    best_ask = min([a["price"] for a in asks]) if asks else None

    # Compute mid price and spread
    mid_price = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None
    spread = best_ask - best_bid if best_bid is not None and best_ask is not None else None

    # Compute volumes
    bid_volume = sum(b.get("quantity", 0) for b in bids) if bids else 0
    ask_volume = sum(a.get("quantity", 0) for a in asks) if asks else 0

    # Compute book imbalance (0=all asks, 1=all bids)
    total_volume = bid_volume + ask_volume
    book_imbalance = bid_volume / total_volume if total_volume > 0 else None

    # Compute price change % over last 10 messages
    price_change_pct = None
    if len(filtered) >= 2:
        window = min(10, len(filtered))
        current_bids = filtered[-1].get("bids", [])
        prior_bids = filtered[-window].get("bids", [])

        current_best_bid = max([b["price"] for b in current_bids]) if current_bids else None
        prior_best_bid = max([b["price"] for b in prior_bids]) if prior_bids else None

        if current_best_bid is not None and prior_best_bid is not None and prior_best_bid != 0:
            price_change_pct = ((current_best_bid - prior_best_bid) / prior_best_bid) * 100

    return {
        "symbol": symbol,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "spread": spread,
        "bid_volume": bid_volume,
        "ask_volume": ask_volume,
        "book_imbalance": book_imbalance,
        "price_change_pct": price_change_pct,
        "messages_analyzed": len(filtered),
    }
