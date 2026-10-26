"""NSE corporate actions feed (splits, bonuses, consolidations, demergers, dividends).

The feed is a JSON API on www.nseindia.com. Each action has a free-text subject such as
"Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share" or "Bonus 1:1",
which parse_subject turns into a price adjustment factor.
"""

import json
import re
from datetime import date

import pandas as pd

REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-actions"

_FACE_VALUE = r"From\s+R[se]\.?\s*([\d.]+).*?To\s+R[se]\.?\s*([\d.]+)"
_SPLIT = re.compile(r"(?i)split.*?" + _FACE_VALUE)
_CONSOLIDATION = re.compile(r"(?i)consolidat.*?" + _FACE_VALUE)
_BONUS = re.compile(r"(?i)bonus\s*(\d+)\s*:\s*(\d+)")


def url_for(start: date, end: date) -> str:
    return ("https://www.nseindia.com/api/corporates-corporateActions?index=equities"
            f"&from_date={start:%d-%m-%Y}&to_date={end:%d-%m-%Y}")


def parse_subject(subject: str) -> tuple[str, float | None]:
    """Return (kind, factor). Prices before the ex-date are multiplied by factor.

    kind is one of split, consolidation, bonus, demerger, rights, other. Factor is None when
    the subject alone does not determine it (demerger, rights) or no adjustment applies.
    """
    if m := _SPLIT.search(subject):
        old, new = float(m.group(1)), float(m.group(2))
        return ("split", new / old) if old > 0 and new > 0 else ("split", None)
    if m := _CONSOLIDATION.search(subject):
        old, new = float(m.group(1)), float(m.group(2))
        return ("consolidation", new / old) if old > 0 and new > 0 else ("consolidation", None)
    if m := _BONUS.search(subject):
        new_shares, held = int(m.group(1)), int(m.group(2))
        return ("bonus", held / (new_shares + held)) if new_shares + held > 0 else ("bonus", None)
    if re.search(r"(?i)demerger|spin.?off", subject):
        return "demerger", None
    if re.search(r"(?i)\brights?\b", subject):
        return "rights", None
    return "other", None


def parse(raw: bytes) -> pd.DataFrame:
    records = json.loads(raw)
    rows = []
    for r in records:
        try:
            ex_date = pd.to_datetime(r["exDate"], format="%d-%b-%Y").date()
        except (KeyError, ValueError, TypeError):
            continue
        subject = (r.get("subject") or "").strip()
        kind, factor = parse_subject(subject)
        rows.append({
            "symbol": (r.get("symbol") or "").strip(),
            "isin": (r.get("isin") or "").strip() or None,
            "series": (r.get("series") or "").strip() or None,
            "ex_date": ex_date,
            "subject": subject,
            "kind": kind,
            "factor": factor,
        })
    cols = ["symbol", "isin", "series", "ex_date", "subject", "kind", "factor"]
    return pd.DataFrame(rows, columns=cols).drop_duplicates(["symbol", "ex_date", "subject"])
