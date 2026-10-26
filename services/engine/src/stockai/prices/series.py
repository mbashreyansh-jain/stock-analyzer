"""Read a stock's daily price history, raw or adjusted for splits and bonuses."""

from datetime import date

import pandas as pd
import psycopg

from stockai.prices import adjustments

COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "delivery_pct"]


def load(conn: psycopg.Connection, symbol: str, start: date | None = None, end: date | None = None,
         adjusted: bool = True) -> pd.DataFrame:
    row = conn.execute("SELECT id FROM instruments WHERE symbol = %s", (symbol.upper(),)).fetchone()
    if row is None:
        raise LookupError(f"Unknown symbol {symbol!r}")
    instrument_id = row[0]

    rows = conn.execute(
        f"""
        SELECT {', '.join(COLUMNS)} FROM prices_daily
        WHERE instrument_id = %s AND (%s::date IS NULL OR trade_date >= %s) AND (%s::date IS NULL OR trade_date <= %s)
        ORDER BY trade_date
        """,
        (instrument_id, start, start, end, end),
    ).fetchall()
    prices = pd.DataFrame(rows, columns=COLUMNS)
    for col in ("open", "high", "low", "close", "delivery_pct"):
        prices[col] = pd.to_numeric(prices[col], errors="coerce")
    if not adjusted or prices.empty:
        return prices

    adj_rows = conn.execute(
        "SELECT ex_date, factor FROM price_adjustments WHERE instrument_id = %s", (instrument_id,)
    ).fetchall()
    adj = pd.DataFrame(adj_rows, columns=["ex_date", "factor"])
    adj["factor"] = pd.to_numeric(adj["factor"])
    return adjustments.apply(prices, adj)
