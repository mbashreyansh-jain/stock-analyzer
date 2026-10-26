"""Split/bonus/demerger adjustment: turn corporate actions into factors and apply them to raw prices.

Raw prices are never changed in the database. A factor on an ex-date means every price before
that date is multiplied by it (a 10-to-2 split gives 0.2), so old and new prices compare directly.
"""

import numpy as np
import pandas as pd

ADJUSTING_KINDS = ("split", "consolidation", "bonus", "demerger")
EVENT_COLUMNS = ["instrument_id", "ex_date", "factor", "kinds", "source"]


def events(actions: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    """Combine corporate actions into one factor per instrument and ex-date.

    `actions` needs instrument_id, ex_date, kind, factor (None for demergers). `market` needs
    instrument_id, ex_date, ex_open, prior_close. A demerger has no ratio in its notice, so its
    factor is implied by the market: the ex-date opening price over the previous close.
    """
    df = actions[actions["kind"].isin(ADJUSTING_KINDS)].copy()
    if df.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    df = df.merge(market, on=["instrument_id", "ex_date"], how="left")
    df["factor"] = df["factor"].astype(float)
    implied = df["ex_open"].astype(float) / df["prior_close"].astype(float)
    is_demerger = df["kind"] == "demerger"
    if is_demerger.any():
        df.loc[is_demerger, "factor"] = implied[is_demerger].where((implied > 0) & (implied < 1))
    df["market_implied"] = is_demerger
    df = df.dropna(subset=["factor"])
    df = df[df["factor"] > 0]
    if df.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    grouped = df.groupby(["instrument_id", "ex_date"], as_index=False).agg(
        factor=("factor", "prod"),
        kinds=("kind", lambda k: ",".join(sorted(set(k)))),
        market_implied=("market_implied", "any"),
    )
    grouped["source"] = np.where(grouped["market_implied"], "market_implied", "corporate_action")
    grouped["instrument_id"] = grouped["instrument_id"].astype("int64")
    return grouped[EVENT_COLUMNS]


def apply(prices: pd.DataFrame, adjustments: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of one instrument's prices with OHLC and volume adjusted.

    `prices` needs trade_date, open, high, low, close, volume. `adjustments` needs ex_date and
    factor. A price on day d is multiplied by every factor whose ex_date is after d, and volume
    is divided by the same amount, so the whole series is comparable with today's price.
    """
    out = prices.copy()
    if adjustments.empty:
        out["adj_factor"] = 1.0
        return out

    adj = adjustments.sort_values("ex_date")
    ex_dates = pd.to_datetime(adj["ex_date"]).to_numpy()
    factors = adj["factor"].astype(float).to_numpy()
    # suffix[i] = product of factors[i:], with a trailing 1.0 for "no later events"
    suffix = np.append(np.cumprod(factors[::-1])[::-1], 1.0)

    idx = np.searchsorted(ex_dates, pd.to_datetime(out["trade_date"]).to_numpy(), side="right")
    cum = suffix[idx]
    for col in ("open", "high", "low", "close"):
        out[col] = (out[col].astype(float) * cum).round(2)
    out["volume"] = (out["volume"].astype(float) / cum).round().astype("int64")
    out["adj_factor"] = cum
    return out
