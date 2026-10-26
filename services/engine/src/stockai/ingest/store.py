"""Database reads and writes used by the ingest pipeline."""

import json
from datetime import date

import pandas as pd
import psycopg


def _records(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    """Rows as tuples with NaN/NA turned into None, ready for psycopg."""
    clean = df[columns].astype(object).where(df[columns].notna(), None)
    return list(clean.itertuples(index=False, name=None))


def upsert_instruments_from_prices(conn: psycopg.Connection, prices: pd.DataFrame) -> dict[str, int]:
    """Create instruments seen for the first time and refresh ISIN/series. Returns symbol -> id."""
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO instruments (symbol, isin, name, series) VALUES (%s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                isin = EXCLUDED.isin,
                series = EXCLUDED.series,
                name = COALESCE(instruments.name, EXCLUDED.name),
                updated_at = now()
            """,
            _records(prices, ["symbol", "isin", "name", "series"]),
        )
    return instrument_ids(conn, list(prices["symbol"]))


def instrument_ids(conn: psycopg.Connection, symbols: list[str]) -> dict[str, int]:
    rows = conn.execute("SELECT symbol, id FROM instruments WHERE symbol = ANY(%s)", (symbols,)).fetchall()
    return dict(rows)


def upsert_prices(conn: psycopg.Connection, day: date, prices: pd.DataFrame, ids: dict[str, int],
                  source: str) -> int:
    df = prices.assign(instrument_id=prices["symbol"].map(ids), trade_date=day, source=source)
    cols = ["instrument_id", "trade_date", "series", "open", "high", "low", "close", "last",
            "prev_close", "volume", "turnover", "trades", "source"]
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE tmp_prices (LIKE prices_daily INCLUDING DEFAULTS) ON COMMIT DROP")
        with cur.copy(f"COPY tmp_prices ({', '.join(cols)}) FROM STDIN") as copy:
            for row in _records(df, cols):
                copy.write_row(row)
        cur.execute(
            f"""
            INSERT INTO prices_daily ({', '.join(cols)})
            SELECT {', '.join(cols)} FROM tmp_prices
            ON CONFLICT (instrument_id, trade_date) DO UPDATE SET
                series = EXCLUDED.series, open = EXCLUDED.open, high = EXCLUDED.high,
                low = EXCLUDED.low, close = EXCLUDED.close, last = EXCLUDED.last,
                prev_close = EXCLUDED.prev_close, volume = EXCLUDED.volume,
                turnover = EXCLUDED.turnover, trades = EXCLUDED.trades, source = EXCLUDED.source
            """
        )
        return cur.rowcount


def update_delivery(conn: psycopg.Connection, day: date, delivery: pd.DataFrame) -> int:
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE tmp_delivery (symbol text, delivery_qty bigint, delivery_pct numeric)"
                    " ON COMMIT DROP")
        with cur.copy("COPY tmp_delivery (symbol, delivery_qty, delivery_pct) FROM STDIN") as copy:
            for row in _records(delivery, ["symbol", "delivery_qty", "delivery_pct"]):
                copy.write_row(row)
        cur.execute(
            """
            UPDATE prices_daily p SET delivery_qty = t.delivery_qty, delivery_pct = t.delivery_pct
            FROM tmp_delivery t JOIN instruments i ON i.symbol = t.symbol
            WHERE p.instrument_id = i.id AND p.trade_date = %s
            """,
            (day,),
        )
        return cur.rowcount


def upsert_index_closes(conn: psycopg.Connection, day: date, closes: pd.DataFrame) -> int:
    cols = ["index_name", "open", "high", "low", "close", "pe", "pb", "div_yield", "volume", "turnover_cr"]
    with conn.cursor() as cur:
        cur.executemany(
            f"""
            INSERT INTO index_daily (trade_date, {', '.join(cols)})
            VALUES (%s, {', '.join(['%s'] * len(cols))})
            ON CONFLICT (index_name, trade_date) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, close = EXCLUDED.close,
                pe = EXCLUDED.pe, pb = EXCLUDED.pb, div_yield = EXCLUDED.div_yield,
                volume = EXCLUDED.volume, turnover_cr = EXCLUDED.turnover_cr
            """,
            [(day, *row) for row in _records(closes, cols)],
        )
    return len(closes)


def upsert_universe(conn: psycopg.Connection, index_name: str, as_of: date, members: pd.DataFrame) -> int:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO instruments (symbol, isin, name, industry) VALUES (%s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                isin = EXCLUDED.isin, name = EXCLUDED.name, industry = EXCLUDED.industry, updated_at = now()
            """,
            _records(members, ["symbol", "isin", "name", "industry"]),
        )
        cur.execute(
            """
            INSERT INTO index_members (index_name, as_of, instrument_id)
            SELECT %s, %s, id FROM instruments WHERE symbol = ANY(%s)
            ON CONFLICT DO NOTHING
            """,
            (index_name, as_of, list(members["symbol"])),
        )
    return len(members)


def latest_universe(conn: psycopg.Connection, index_name: str, on_or_before: date) -> set[str]:
    """Index members as of the latest snapshot on or before the date. Empty if we have no snapshot that old,
    because today's list would wrongly include companies that were not listed back then."""
    rows = conn.execute(
        """
        SELECT i.symbol FROM index_members m JOIN instruments i ON i.id = m.instrument_id
        WHERE m.index_name = %s
          AND m.as_of = (SELECT max(as_of) FROM index_members WHERE index_name = %s AND as_of <= %s)
        """,
        (index_name, index_name, on_or_before),
    ).fetchall()
    return {r[0] for r in rows}


def upsert_corporate_actions(conn: psycopg.Connection, actions: pd.DataFrame) -> int:
    cols = ["symbol", "isin", "series", "ex_date", "subject", "kind", "factor"]
    with conn.cursor() as cur:
        cur.executemany(
            f"""
            INSERT INTO corporate_actions ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})
            ON CONFLICT (symbol, ex_date, subject) DO UPDATE SET
                isin = EXCLUDED.isin, series = EXCLUDED.series, kind = EXCLUDED.kind,
                factor = EXCLUDED.factor, fetched_at = now()
            """,
            _records(actions, cols),
        )
    return len(actions)


def adjusting_actions(conn: psycopg.Connection) -> pd.DataFrame:
    """Splits, bonuses, consolidations and demergers for stocks we hold prices for."""
    rows = conn.execute(
        """
        SELECT i.id, c.ex_date, c.kind, c.factor FROM corporate_actions c
        JOIN instruments i ON i.symbol = c.symbol
        WHERE c.kind IN ('split', 'consolidation', 'bonus', 'demerger')
        """
    ).fetchall()
    df = pd.DataFrame(rows, columns=["instrument_id", "ex_date", "kind", "factor"])
    df["factor"] = pd.to_numeric(df["factor"], errors="coerce")
    return df


def ex_date_market(conn: psycopg.Connection) -> pd.DataFrame:
    """For each demerger, the first open on or after the ex-date and the last close before it."""
    rows = conn.execute(
        """
        SELECT i.id, c.ex_date,
               (SELECT p.open FROM prices_daily p WHERE p.instrument_id = i.id AND p.trade_date >= c.ex_date
                ORDER BY p.trade_date LIMIT 1),
               (SELECT p.close FROM prices_daily p WHERE p.instrument_id = i.id AND p.trade_date < c.ex_date
                ORDER BY p.trade_date DESC LIMIT 1)
        FROM corporate_actions c JOIN instruments i ON i.symbol = c.symbol
        WHERE c.kind = 'demerger'
        """
    ).fetchall()
    df = pd.DataFrame(rows, columns=["instrument_id", "ex_date", "ex_open", "prior_close"])
    for col in ("ex_open", "prior_close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def replace_adjustments(conn: psycopg.Connection, events: pd.DataFrame) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM price_adjustments")
        cur.executemany(
            "INSERT INTO price_adjustments (instrument_id, ex_date, factor, kinds, source) VALUES (%s, %s, %s, %s, %s)",
            _records(events, ["instrument_id", "ex_date", "factor", "kinds", "source"]),
        )
    return len(events)


def adjustments_on(conn: psycopg.Connection, day: date) -> pd.DataFrame:
    rows = conn.execute(
        "SELECT instrument_id, ex_date, factor, kinds, source FROM price_adjustments WHERE ex_date = %s", (day,)
    ).fetchall()
    return pd.DataFrame(rows, columns=["instrument_id", "ex_date", "factor", "kinds", "source"])


def recent_row_counts(conn: psycopg.Connection, before: date, limit: int = 20) -> list[int]:
    rows = conn.execute(
        """
        SELECT row_count FROM ingest_runs
        WHERE dataset = 'bhavcopy' AND status = 'ok' AND trade_date < %s
        ORDER BY trade_date DESC LIMIT %s
        """,
        (before, limit),
    ).fetchall()
    return [r[0] for r in rows]


def replace_quality_issues(conn: psycopg.Connection, day: date, issues: list[dict], ids: dict[str, int]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM data_quality_issues WHERE trade_date = %s", (day,))
        cur.executemany(
            """
            INSERT INTO data_quality_issues (trade_date, check_name, severity, instrument_id, detail)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                (day, i["check_name"], i["severity"], ids.get(i["symbol"]) if i["symbol"] else None,
                 json.dumps(i["detail"], default=str))
                for i in issues
            ],
        )


def record_run(conn: psycopg.Connection, dataset: str, day: date, status: str, row_count: int | None = None,
               message: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO ingest_runs (dataset, trade_date, status, row_count, message) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset, trade_date) DO UPDATE SET
            status = EXCLUDED.status, row_count = EXCLUDED.row_count,
            message = EXCLUDED.message, finished_at = now()
        """,
        (dataset, day, status, row_count, message),
    )


def run_status(conn: psycopg.Connection, dataset: str, start: date, end: date) -> dict[date, str]:
    rows = conn.execute(
        "SELECT trade_date, status FROM ingest_runs WHERE dataset = %s AND trade_date BETWEEN %s AND %s",
        (dataset, start, end),
    ).fetchall()
    return dict(rows)
