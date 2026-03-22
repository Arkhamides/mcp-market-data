"""OHLCV candle aggregation from live market stream messages."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

RESOLUTIONS: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
}


@dataclass
class Candle:
    symbol: str
    resolution: str
    timestamp: int  # bucket start, Unix seconds
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "resolution": self.resolution,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class OHLCVAggregator:
    """Accumulates market stream messages into OHLCV candles.

    Call process_message() on each incoming parsed message.  Returns a list of
    completed candles whenever a time bucket rolls over (may be empty most of
    the time).  Incomplete in-progress candles are only emitted on rollover.
    """

    def __init__(self) -> None:
        # (symbol, resolution) -> in-progress bucket dict
        self._buckets: Dict[Tuple[str, str], dict] = {}

    def process_message(self, msg: dict) -> List[Candle]:
        """Process one parsed market message.

        Returns any candles that were completed (i.e. their bucket rolled over).
        """
        symbol: Optional[str] = msg.get("symbol")
        if not symbol:
            return []

        bids = msg.get("bids", [])
        asks = msg.get("asks", [])
        if not bids or not asks:
            return []

        try:
            best_bid = max(float(b["price"]) for b in bids)
            best_ask = min(float(a["price"]) for a in asks)
        except (ValueError, KeyError, TypeError):
            return []

        mid_price = (best_bid + best_ask) / 2.0
        volume = sum(float(b.get("quantity", 0)) for b in bids) + sum(float(a.get("quantity", 0)) for a in asks)

        now = int(time.time())
        completed: List[Candle] = []

        for res_name, bucket_size in RESOLUTIONS.items():
            bucket_ts = (now // bucket_size) * bucket_size
            key = (symbol, res_name)

            existing = self._buckets.get(key)

            if existing is not None and existing["timestamp"] != bucket_ts:
                # Bucket rolled over — emit the finished candle
                completed.append(Candle(
                    symbol=symbol,
                    resolution=res_name,
                    timestamp=existing["timestamp"],
                    open=existing["open"],
                    high=existing["high"],
                    low=existing["low"],
                    close=existing["close"],
                    volume=existing["volume"],
                ))
                existing = None

            if existing is None:
                self._buckets[key] = {
                    "timestamp": bucket_ts,
                    "open": mid_price,
                    "high": mid_price,
                    "low": mid_price,
                    "close": mid_price,
                    "volume": volume,
                }
            else:
                existing["high"] = max(existing["high"], mid_price)
                existing["low"] = min(existing["low"], mid_price)
                existing["close"] = mid_price
                existing["volume"] += volume

        return completed

    def get_open_candles(self) -> List[Candle]:
        """Return the current in-progress (incomplete) candle for every tracked bucket."""
        candles = []
        for (symbol, res_name), bucket in self._buckets.items():
            candles.append(Candle(
                symbol=symbol,
                resolution=res_name,
                timestamp=bucket["timestamp"],
                open=bucket["open"],
                high=bucket["high"],
                low=bucket["low"],
                close=bucket["close"],
                volume=bucket["volume"],
            ))
        return candles
