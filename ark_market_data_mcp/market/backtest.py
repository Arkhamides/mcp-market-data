"""Pure backtesting engine — no I/O, no async, no MCP dependencies.

The engine simulates a set of buy/sell rules against a list of OHLCV candle
dicts (as returned by OHLCVStore.get_recent / get_range) and returns a result
dict with P&L, max drawdown, and a full trade log.

Supported condition types
-------------------------
percent_change
    Fires when the candle's close has moved by at least `percent`% relative
    to the close `window` candles ago.

    Fields: direction ("up" | "down"), percent (float > 0), window (int >= 1, default 1)

    Note: this is a *level* condition, not an *edge* condition — it fires on
    every candle where the inequality holds, not only on the first crossing.
    In a sustained down-move a buy rule will fire repeatedly, quickly consuming
    cash.  This mirrors DCA (dollar-cost averaging) behaviour.

price_threshold
    Fires every candle where the close is above/below a fixed price level.

    Fields: cross ("above" | "below"), threshold (float > 0)

Trade execution rules
---------------------
- All trades execute at the candle's *close* price.
- BUY: spends `amount_usd` of cash; skipped silently if cash < amount_usd.
- SELL: sells `amount_usd` worth of the asset; skipped silently if holdings
  are insufficient (no partial fills).
- Rules evaluated in order per candle; each rule sees the balance left by
  preceding rules on the same candle.
"""

from datetime import datetime, timezone
from typing import Any


class BacktestError(ValueError):
    """Raised for invalid strategy configuration."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_rules(rules_input: list) -> list[dict]:
    """Validate and normalise raw rule dicts from tool arguments."""
    if not isinstance(rules_input, list) or len(rules_input) == 0:
        raise BacktestError("rules must be a non-empty array.")

    parsed = []
    for idx, rule in enumerate(rules_input):
        label = f"rules[{idx}]"

        action = rule.get("action")
        if action not in ("buy", "sell"):
            raise BacktestError(f"{label}: action must be 'buy' or 'sell', got {action!r}.")

        try:
            amount_usd = float(rule["amount_usd"])
        except (KeyError, TypeError, ValueError):
            raise BacktestError(f"{label}: amount_usd must be a positive number.")
        if amount_usd <= 0:
            raise BacktestError(f"{label}: amount_usd must be > 0.")

        condition = rule.get("condition")
        if not isinstance(condition, dict):
            raise BacktestError(f"{label}: condition must be an object.")

        ctype = condition.get("type")
        if ctype not in ("percent_change", "price_threshold"):
            raise BacktestError(
                f"{label}: condition.type must be 'percent_change' or 'price_threshold', got {ctype!r}."
            )

        parsed_cond: dict[str, Any] = {"type": ctype}

        if ctype == "percent_change":
            direction = condition.get("direction")
            if direction not in ("up", "down"):
                raise BacktestError(f"{label}: condition.direction must be 'up' or 'down'.")
            try:
                percent = float(condition["percent"])
            except (KeyError, TypeError, ValueError):
                raise BacktestError(f"{label}: condition.percent must be a positive number.")
            if percent <= 0:
                raise BacktestError(f"{label}: condition.percent must be > 0.")
            window = int(condition.get("window", 1))
            if window < 1:
                raise BacktestError(f"{label}: condition.window must be >= 1.")
            parsed_cond.update({"direction": direction, "percent": percent, "window": window})

        elif ctype == "price_threshold":
            cross = condition.get("cross")
            if cross not in ("above", "below"):
                raise BacktestError(f"{label}: condition.cross must be 'above' or 'below'.")
            try:
                threshold = float(condition["threshold"])
            except (KeyError, TypeError, ValueError):
                raise BacktestError(f"{label}: condition.threshold must be a positive number.")
            if threshold <= 0:
                raise BacktestError(f"{label}: condition.threshold must be > 0.")
            parsed_cond.update({"cross": cross, "threshold": threshold})

        parsed.append({
            "action": action,
            "amount_usd": amount_usd,
            "condition": parsed_cond,
        })

    return parsed


def _evaluate_condition(candles: list[dict], i: int, condition: dict) -> bool:
    """Return True if the condition is satisfied at candle index i."""
    ctype = condition["type"]

    if ctype == "percent_change":
        window = condition["window"]
        if i < window:
            return False
        ref = candles[i - window]["close"]
        if ref == 0:
            return False
        cur = candles[i]["close"]
        pct = ((cur - ref) / ref) * 100.0
        if condition["direction"] == "down":
            return pct <= -condition["percent"]
        else:  # "up"
            return pct >= condition["percent"]

    elif ctype == "price_threshold":
        price = candles[i]["close"]
        if condition["cross"] == "above":
            return price > condition["threshold"]
        else:  # "below"
            return price < condition["threshold"]

    return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_backtest(
    candles: list[dict],
    rules: list[dict],
    initial_capital: float,
    symbol: str,
    resolution: str,
) -> dict:
    """Simulate trading rules against historical candles.

    Parameters
    ----------
    candles:
        List of candle dicts (oldest-first) as returned by OHLCVStore.
        Each dict must have at least: timestamp (int), close (float).
    rules:
        Raw rule dicts from the tool's `rules` argument.
    initial_capital:
        Starting cash in USD.
    symbol, resolution:
        Passed through to the result dict for context.

    Returns
    -------
    Result dict with P&L, max drawdown, trade counts, and trade log.
    """
    if not candles:
        raise BacktestError("candles list is empty.")
    if initial_capital <= 0:
        raise BacktestError("initial_capital must be > 0.")

    parsed_rules = _parse_rules(rules)

    cash = initial_capital
    asset_held = 0.0  # units of the asset (e.g. BTC)
    trades: list[dict] = []
    portfolio_values: list[float] = []

    for i, candle in enumerate(candles):
        price = float(candle["close"])
        if price <= 0:
            portfolio_values.append(cash + asset_held * (price if price > 0 else 0))
            continue

        for rule in parsed_rules:
            if not _evaluate_condition(candles, i, rule["condition"]):
                continue

            action = rule["action"]
            amount_usd = rule["amount_usd"]

            if action == "buy":
                if cash < amount_usd:
                    continue
                asset_bought = amount_usd / price
                cash -= amount_usd
                asset_held += asset_bought
                pv = round(cash + asset_held * price, 2)
                trades.append({
                    "timestamp": candle["timestamp"],
                    "time": _iso(candle["timestamp"]),
                    "action": "buy",
                    "price": round(price, 2),
                    "amount_usd": round(amount_usd, 2),
                    "asset_amount": round(asset_bought, 8),
                    "cash_after": round(cash, 2),
                    "portfolio_value": pv,
                })

            elif action == "sell":
                asset_to_sell = amount_usd / price
                # use rounded comparison to avoid float epsilon errors
                if round(asset_held, 8) < round(asset_to_sell, 8):
                    continue
                asset_held -= asset_to_sell
                cash += amount_usd
                pv = round(cash + asset_held * price, 2)
                trades.append({
                    "timestamp": candle["timestamp"],
                    "time": _iso(candle["timestamp"]),
                    "action": "sell",
                    "price": round(price, 2),
                    "amount_usd": round(amount_usd, 2),
                    "asset_amount": round(asset_to_sell, 8),
                    "cash_after": round(cash, 2),
                    "portfolio_value": pv,
                })

        portfolio_values.append(cash + asset_held * price)

    # Final portfolio value
    final_price = float(candles[-1]["close"])
    final_value = cash + asset_held * final_price

    # Max drawdown from portfolio value series
    max_drawdown_pct = 0.0
    running_peak = initial_capital
    for pv in portfolio_values:
        if pv > running_peak:
            running_peak = pv
        if running_peak > 0:
            dd = (running_peak - pv) / running_peak * 100.0
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd

    total_pnl_usd = final_value - initial_capital
    total_pnl_pct = (total_pnl_usd / initial_capital) * 100.0

    buy_count = sum(1 for t in trades if t["action"] == "buy")
    sell_count = sum(1 for t in trades if t["action"] == "sell")

    return {
        "symbol": symbol,
        "resolution": resolution,
        "candle_count": len(candles),
        "initial_capital": round(initial_capital, 2),
        "final_portfolio_value": round(final_value, 2),
        "total_pnl_usd": round(total_pnl_usd, 2),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "trade_count": len(trades),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "start_time": _iso(candles[0]["timestamp"]),
        "end_time": _iso(candles[-1]["timestamp"]),
        "trades": trades,
    }
