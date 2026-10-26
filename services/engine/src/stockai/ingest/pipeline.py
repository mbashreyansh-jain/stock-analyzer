"""End-of-day pipeline: download, load, adjust and check one trading day, or a range of days."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg

from stockai.data.nse import bhavcopy, corporate_actions, delivery, indices
from stockai.data.nse.client import NseClient
from stockai.ingest import quality, store
from stockai.prices import adjustments

IST = ZoneInfo("Asia/Kolkata")
UNIVERSE = "NIFTY 500"
# Recent days with no file may simply not be published yet, so they are retried on the next run.
RETRY_NO_DATA_DAYS = 5


@dataclass
class DayResult:
    day: date
    status: str
    prices: int = 0
    delivery: int = 0
    indices: int = 0
    adjustments: int = 0
    issues: dict[str, int] = field(default_factory=dict)


def today_ist() -> date:
    return datetime.now(IST).date()


def last_weekday(on_or_before: date) -> date:
    while on_or_before.weekday() >= 5:
        on_or_before -= timedelta(days=1)
    return on_or_before


def refresh_universe(conn: psycopg.Connection, client: NseClient, as_of: date) -> dict[str, int]:
    counts = {}
    for index_name in indices.CONSTITUENT_FILES:
        raw = client.fetch(indices.constituents_url(index_name),
                           f"constituents/{as_of:%Y%m%d}/{indices.CONSTITUENT_FILES[index_name]}")
        if raw is None:
            continue
        counts[index_name] = store.upsert_universe(conn, index_name, as_of, indices.parse_constituents(raw))
    conn.commit()
    return counts


def sync_corporate_actions(conn: psycopg.Connection, client: NseClient, start: date, end: date) -> int:
    """Download corporate actions month by month. Months that ended over 10 days ago are cached."""
    total = 0
    month = start.replace(day=1)
    while month <= end:
        next_month = (month + timedelta(days=32)).replace(day=1)
        chunk_start, chunk_end = max(month, start), min(next_month - timedelta(days=1), end)
        settled = next_month - timedelta(days=1) < today_ist() - timedelta(days=10)
        cache_key = f"corporate_actions/{chunk_start:%Y%m%d}_{chunk_end:%Y%m%d}.json"
        raw = client.fetch(corporate_actions.url_for(chunk_start, chunk_end), cache_key,
                           use_cache=settled, headers={"Referer": corporate_actions.REFERER,
                                                       "Accept": "application/json"})
        if raw:
            total += store.upsert_corporate_actions(conn, corporate_actions.parse(raw))
        month = next_month
    return total


def ingest_day(conn: psycopg.Connection, client: NseClient, day: date, sync_actions: bool = True) -> DayResult:
    raw = client.fetch(bhavcopy.url_for(day), bhavcopy.cache_key_for(day))
    if raw is None:
        store.record_run(conn, "bhavcopy", day, "no_data", message="No bhavcopy file (holiday or not yet published)")
        conn.commit()
        return DayResult(day, "no_data")

    prices = bhavcopy.parse(raw, day)
    source = "nse_udiff" if day >= bhavcopy.UDIFF_START else "nse_legacy"
    ids = store.upsert_instruments_from_prices(conn, prices)
    result = DayResult(day, "ok", prices=store.upsert_prices(conn, day, prices, ids, source))

    raw = client.fetch(delivery.url_for(day), delivery.cache_key_for(day))
    if raw is not None:
        result.delivery = store.update_delivery(conn, day, delivery.parse(raw))
    store.record_run(conn, "delivery", day, "ok" if raw else "no_data", result.delivery)

    raw = client.fetch(indices.close_url_for(day), indices.close_cache_key_for(day))
    if raw is not None:
        result.indices = store.upsert_index_closes(conn, day, indices.parse_closes(raw))
    store.record_run(conn, "index_closes", day, "ok" if raw else "no_data", result.indices)

    if sync_actions:
        sync_corporate_actions(conn, client, day - timedelta(days=10), day + timedelta(days=30))
    rebuild_adjustments(conn, commit=False)
    events = store.adjustments_on(conn, day)
    result.adjustments = len(events)

    issues = run_quality(conn, day, prices, events, ids)
    for i in issues:
        result.issues[i["severity"]] = result.issues.get(i["severity"], 0) + 1

    store.record_run(conn, "bhavcopy", day, "ok", result.prices)
    conn.commit()
    return result


def run_quality(conn: psycopg.Connection, day: date, prices: pd.DataFrame, events: pd.DataFrame,
                ids: dict[str, int]) -> list[dict]:
    symbols_by_id = {v: k for k, v in ids.items()}
    adjusted_symbols = {symbols_by_id.get(int(i)) for i in events["instrument_id"]}
    issues = (
        quality.check_ohlc(prices)
        + quality.check_row_count(len(prices), store.recent_row_counts(conn, day))
        + quality.check_coverage(set(prices["symbol"]), store.latest_universe(conn, UNIVERSE, day), UNIVERSE)
        + quality.check_extreme_moves(prices, adjusted_symbols)
        + quality.report_adjustments(events, symbols_by_id)
    )
    store.replace_quality_issues(conn, day, issues, ids)
    return issues


def backfill(conn: psycopg.Connection, client: NseClient, start: date, end: date, force: bool = False,
             on_day: Callable[[DayResult], None] | None = None) -> list[DayResult]:
    """Ingest every weekday from start to end in date order, skipping days already done."""
    sync_corporate_actions(conn, client, start, end + timedelta(days=30))
    conn.commit()
    done = store.run_status(conn, "bhavcopy", start, end)
    retry_after = today_ist() - timedelta(days=RETRY_NO_DATA_DAYS)
    results = []
    day = start
    while day <= end:
        status = done.get(day)
        skip = status == "ok" or (status == "no_data" and day < retry_after)
        if day.weekday() < 5 and (force or not skip):
            try:
                result = ingest_day(conn, client, day, sync_actions=False)
            except Exception as exc:  # keep going, the failed day is recorded and retried next run
                conn.rollback()
                store.record_run(conn, "bhavcopy", day, "error", message=str(exc)[:500])
                conn.commit()
                result = DayResult(day, "error")
            results.append(result)
            if on_day:
                on_day(result)
        day += timedelta(days=1)
    return results


def rebuild_adjustments(conn: psycopg.Connection, commit: bool = True) -> int:
    """Recompute every adjustment factor from the stored corporate actions and prices."""
    events = adjustments.events(store.adjusting_actions(conn), store.ex_date_market(conn))
    count = store.replace_adjustments(conn, events)
    if commit:
        conn.commit()
    return count
