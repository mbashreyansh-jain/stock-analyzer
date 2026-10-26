"""Full bhavdata file, used for delivery quantity and delivery percentage."""

import io
from datetime import date

import pandas as pd


def url_for(day: date) -> str:
    return f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{day:%d%m%Y}.csv"


def cache_key_for(day: date) -> str:
    return f"delivery/{day:%Y}/{day:%Y%m%d}.csv"


def parse(raw: bytes) -> pd.DataFrame:
    """Return symbol, delivery_qty and delivery_pct. Rows without delivery data are dropped."""
    df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, skipinitialspace=True)
    df = df.rename(columns=lambda c: c.strip())
    out = pd.DataFrame({
        "symbol": df["SYMBOL"].str.strip(),
        "series": df["SERIES"].str.strip(),
        "delivery_qty": pd.to_numeric(df["DELIV_QTY"].str.strip(), errors="coerce"),
        "delivery_pct": pd.to_numeric(df["DELIV_PER"].str.strip(), errors="coerce"),
    })
    out = out.dropna(subset=["delivery_qty", "delivery_pct"])
    out["delivery_qty"] = out["delivery_qty"].astype("int64")
    out = out.sort_values("delivery_qty", ascending=False).drop_duplicates("symbol")
    return out[["symbol", "delivery_qty", "delivery_pct"]].reset_index(drop=True)
