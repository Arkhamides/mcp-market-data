"""Seed the local OHLCV database with historical candles from Binance.

Fetches OHLCV data via ccxt (no API key required for public market data)
and writes it to the same SQLite store used by the MCP server.

Usage examples
--------------
# Default: BTC/USDT, 1m resolution, last 6 months
python scripts/seed_historical.py

# Custom symbol and resolution
python scripts/seed_historical.py --symbol ETH/USDT --resolution 5m

# Custom time range (ISO dates)
python scripts/seed_historical.py --start 2024-01-01 --end 2024-06-01

# Custom look-back window
python scripts/seed_historical.py --days 90

# Override the symbol name stored in the DB (to match your live stream format)
python scripts/seed_historical.py --symbol BTC/USDT --store-symbol BTC-USD

# Override DB path
python scripts/seed_historical.py --db /custom/path/ohlcv.db

Notes
-----
- Binance returns up to 1 000 candles per request; this script paginates
  automatically.
- Rate limiting is handled by ccxt (enableRateLimit=True).
- Already-existing candles are upserted (INSERT OR REPLACE), so re-running
  is safe and will fill any gaps.
- This script is intentionally standalone — it does not import the running
  MCP server and can be run while the server is live.

Startup-routine note
--------------------
To auto-seed on server startup, call `run_seed()` from a transport's
lifespan after the DB is initialised but before the stream task starts.
Pass `days=180` (or read from env) and only run if the DB has fewer
candles than expected for the requested window.
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    import ccxt
except ImportError:
    print(
        "ccxt is required for this script.\n"
        "Install it with:  pip install ccxt\n"
        "Or install the full extras:  pip install ark-market-data-mcp[historical]",
        file=sys.stderr,
    )
    sys.exit(1)

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ark_market_data_mcp.market.ohlcv import Candle
from ark_market_data_mcp.market.store import OHLCVStore, DB_PATH

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_SYMBOL = "BTC/USDT"
DEFAULT_RESOLUTION = "1m"
DEFAULT_DAYS = 180
BATCH_SIZE = 1000  # Binance max candles per request

CCXT_TIMEFRAME = {
    "1m": "1m",
    "5m": "5m",
}

# Milliseconds per candle
MS_PER_CANDLE = {
    "1m": 60_000,
    "5m": 300_000,
}


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------

def fetch_and_seed(
    symbol: str,
    store_symbol: str,
    resolution: str,
    since_ms: int,
    until_ms: int,
    store: OHLCVStore,
) -> int:
    """Fetch candles from Binance and write them to `store`.

    Returns the total number of candles written.
    """
    exchange = ccxt.binance({"enableRateLimit": True})
    timeframe = CCXT_TIMEFRAME[resolution]
    ms_step = MS_PER_CANDLE[resolution] * BATCH_SIZE

    total_written = 0
    cursor = since_ms

    print(
        f"Fetching {store_symbol} {resolution} candles from "
        f"{_ms_to_iso(since_ms)} → {_ms_to_iso(until_ms)} …"
    )

    while cursor < until_ms:
        batch = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=cursor,
            limit=BATCH_SIZE,
        )

        if not batch:
            break

        candles = []
        for row in batch:
            ts_ms, o, h, l, c, v = row
            if ts_ms > until_ms:
                break
            candles.append(Candle(
                symbol=store_symbol,
                resolution=resolution,
                timestamp=ts_ms // 1000,  # store as Unix seconds
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v),
            ))

        if candles:
            store.save_many(candles)
            total_written += len(candles)
            last_ts = candles[-1].timestamp
            print(
                f"  Wrote {len(candles):>5} candles  "
                f"up to {datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC  "
                f"({total_written} total)",
                end="\r",
            )

        # Advance cursor past this batch
        cursor = batch[-1][0] + MS_PER_CANDLE[resolution]

    print()  # newline after \r progress
    return total_written


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _parse_date(s: str) -> int:
    """Parse an ISO date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS) to Unix ms."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s!r}  (expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")


# ---------------------------------------------------------------------------
# Public entry point (usable as a library for the startup-routine path)
# ---------------------------------------------------------------------------

def run_seed(
    symbol: str = DEFAULT_SYMBOL,
    store_symbol: str | None = None,
    resolution: str = DEFAULT_RESOLUTION,
    days: int = DEFAULT_DAYS,
    start: str | None = None,
    end: str | None = None,
    db_path: str = DB_PATH,
) -> int:
    """Seed the DB programmatically (e.g. from a server startup routine).

    Returns the number of candles written.
    """
    store_symbol = store_symbol or symbol

    now_ms = int(time.time() * 1000)
    until_ms = _parse_date(end) if end else now_ms
    since_ms = _parse_date(start) if start else until_ms - days * 24 * 3600 * 1000

    store = OHLCVStore(db_path)
    return fetch_and_seed(symbol, store_symbol, resolution, since_ms, until_ms, store)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Seed the local OHLCV database with historical Binance candles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--symbol",
        default=DEFAULT_SYMBOL,
        help="Binance ccxt symbol to fetch (default: %(default)s)",
    )
    p.add_argument(
        "--store-symbol",
        default=None,
        dest="store_symbol",
        help=(
            "Symbol name to store in the DB. Use this to match your live stream "
            "format if it differs from the Binance symbol "
            "(e.g. --store-symbol BTC-USD). Defaults to --symbol."
        ),
    )
    p.add_argument(
        "--resolution",
        default=DEFAULT_RESOLUTION,
        choices=list(CCXT_TIMEFRAME.keys()),
        help="Candle resolution (default: %(default)s)",
    )
    p.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Number of days to look back from --end (default: %(default)s). Ignored if --start is set.",
    )
    p.add_argument(
        "--start",
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (UTC). Overrides --days.",
    )
    p.add_argument(
        "--end",
        default=None,
        metavar="YYYY-MM-DD",
        help="End date (UTC, default: now).",
    )
    p.add_argument(
        "--db",
        default=DB_PATH,
        metavar="PATH",
        help=f"Path to the SQLite database (default: {DB_PATH})",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    t0 = time.time()
    written = run_seed(
        symbol=args.symbol,
        store_symbol=args.store_symbol,
        resolution=args.resolution,
        days=args.days,
        start=args.start,
        end=args.end,
        db_path=args.db,
    )
    elapsed = time.time() - t0

    if written:
        print(f"\nDone. {written:,} candles written in {elapsed:.1f}s.")
    else:
        print("\nNo new candles written (DB may already be up to date).")


if __name__ == "__main__":
    main()
