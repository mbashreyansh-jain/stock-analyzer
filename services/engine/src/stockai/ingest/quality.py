"""Data quality checks for one trading day. Each check is a pure function returning issues.

An issue is a dict with check_name, severity ('info' | 'warn' | 'error'), symbol (or None)
and detail (a JSON-serialisable dict).
"""

import statistics

import pandas as pd

# Most NSE stocks have circuit limits of 20% or less, so a bigger unadjusted move is suspicious.
EXTREME_MOVE = 0.20
MIN_ROW_RATIO = 0.8


def issue(check: str, severity: str, symbol: str | None = None, **detail) -> dict:
    return {"check_name": check, "severity": severity, "symbol": symbol, "detail": detail}


def check_ohlc(prices: pd.DataFrame) -> list[dict]:
    """Open and close must sit inside the day's low-high range, and all prices must be positive."""
    bad = prices[
        (prices[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (prices["low"] > prices[["open", "close"]].min(axis=1))
        | (prices["high"] < prices[["open", "close"]].max(axis=1))
    ]
    return [
        issue("ohlc_consistency", "error", r.symbol, open=r.open, high=r.high, low=r.low, close=r.close)
        for r in bad.itertuples()
    ]


def check_row_count(count: int, recent_counts: list[int]) -> list[dict]:
    """Flag a day with far fewer rows than usual, which usually means a truncated file."""
    if len(recent_counts) < 5:
        return []
    typical = statistics.median(recent_counts)
    if count < MIN_ROW_RATIO * typical:
        return [issue("row_count", "warn", None, rows=count, typical=typical)]
    return []


def check_coverage(day_symbols: set[str], universe: set[str], universe_name: str) -> list[dict]:
    """Members of the analysis universe with no price today."""
    missing = sorted(universe - day_symbols)
    if not missing:
        return []
    severity = "warn" if len(missing) <= 10 else "error"
    return [issue("universe_coverage", severity, None, universe=universe_name, missing=missing)]


def check_extreme_moves(prices: pd.DataFrame, adjusted_symbols: set[str]) -> list[dict]:
    """Moves beyond the circuit range that are not explained by a split or bonus."""
    df = prices[(prices["prev_close"] > 0) & ~prices["symbol"].isin(adjusted_symbols)]
    move = df["close"] / df["prev_close"] - 1
    hits = df[move.abs() > EXTREME_MOVE]
    return [
        issue("extreme_move", "warn", r.symbol, prev_close=r.prev_close, close=r.close,
              move_pct=round((r.close / r.prev_close - 1) * 100, 2))
        for r in hits.itertuples()
    ]


def report_adjustments(events: pd.DataFrame, symbols_by_id: dict[int, str]) -> list[dict]:
    """Log each adjustment applied today. Market-implied ones (demergers) deserve a manual look."""
    return [
        issue("adjustment_applied", "warn" if r.source == "market_implied" else "info",
              symbols_by_id.get(int(r.instrument_id)), factor=round(float(r.factor), 6),
              kinds=r.kinds, source=r.source)
        for r in events.itertuples()
    ]
