"""SQLite-backed OHLCV historical store with per-tier depth limits."""

import os
import sqlite3
from typing import List

from .ohlcv import Candle

# Storage directory — override with DATA_DIR env var
_DEFAULT_DATA_DIR = os.path.expanduser("~/.ark-market-data")
DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)
DB_PATH = os.path.join(DATA_DIR, "ohlcv.db")

# Maximum candles returned per query, keyed by tier
TIER_LIMITS = {
    "free": 200,   # ~3 h of 1 m candles
    "paid": 2000,  # ~33 h of 1 m candles
}

# Active tier — override with OHLCV_TIER env var (free | paid)
OHLCV_TIER: str = os.environ.get("OHLCV_TIER", "free")


def _row_to_dict(row: tuple) -> dict:
    return {
        "symbol": row[0],
        "resolution": row[1],
        "timestamp": row[2],
        "open": row[3],
        "high": row[4],
        "low": row[5],
        "close": row[6],
        "volume": row[7],
    }


class OHLCVStore:
    """Persists OHLCV candles to a local SQLite database.

    Thread-safe for single-process use (SQLite's default WAL mode handles
    concurrent reads from the MCP tool handlers).
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    symbol     TEXT    NOT NULL,
                    resolution TEXT    NOT NULL,
                    timestamp  INTEGER NOT NULL,
                    open       REAL    NOT NULL,
                    high       REAL    NOT NULL,
                    low        REAL    NOT NULL,
                    close      REAL    NOT NULL,
                    volume     REAL    NOT NULL,
                    PRIMARY KEY (symbol, resolution, timestamp)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup
                ON ohlcv (symbol, resolution, timestamp)
            """)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def save(self, candle: Candle) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?,?)",
                (candle.symbol, candle.resolution, candle.timestamp,
                 candle.open, candle.high, candle.low, candle.close, candle.volume),
            )

    def save_many(self, candles: List[Candle]) -> None:
        if not candles:
            return
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?,?)",
                [(c.symbol, c.resolution, c.timestamp,
                  c.open, c.high, c.low, c.close, c.volume) for c in candles],
            )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_recent(self, symbol: str, resolution: str, count: int) -> List[dict]:
        """Return the `count` most-recent closed candles (oldest-first)."""
        limit = min(count, TIER_LIMITS.get(OHLCV_TIER, TIER_LIMITS["free"]))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, resolution, timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND resolution = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (symbol, resolution, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in reversed(rows)]

    def get_range(
        self,
        symbol: str,
        resolution: str,
        start_ts: int,
        end_ts: int,
    ) -> List[dict]:
        """Return candles between start_ts and end_ts inclusive (oldest-first)."""
        limit = TIER_LIMITS.get(OHLCV_TIER, TIER_LIMITS["free"])
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, resolution, timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND resolution = ?
                  AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (symbol, resolution, start_ts, end_ts, limit),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
