import json

import pytest

from stockai.data.nse import corporate_actions as ca


@pytest.mark.parametrize(
    "subject, kind, factor",
    [
        ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", "split", 0.2),
        ("Face Value Split (Sub-Division) - From Rs 5/- Per Share To Re 1/- Per Share", "split", 0.2),
        ("Face Value Split (Sub-Division) - From Rs 2/- Per Share To Re 0.50/- Per Share", "split", 0.25),
        ("Bonus 1:1", "bonus", 0.5),
        ("Bonus 2:1", "bonus", 1 / 3),
        ("Bonus 1:2", "bonus", 2 / 3),
        ("Consolidation Of Shares From Rs 1/- Per Share To Rs 10/- Per Share", "consolidation", 10.0),
        ("Demerger", "demerger", None),
        ("Rights 2:21 @ Premium Rs 748/-", "rights", None),
        ("Dividend - Rs 1.50 Per Share", "other", None),
        ("Annual General Meeting", "other", None),
    ],
)
def test_parse_subject(subject, kind, factor):
    got_kind, got_factor = ca.parse_subject(subject)
    assert got_kind == kind
    if factor is None:
        assert got_factor is None
    else:
        assert got_factor == pytest.approx(factor)


def test_parse_feed_skips_rows_without_ex_date():
    raw = json.dumps([
        {"symbol": "BUILDPRO", "series": "EQ", "isin": "INE1", "exDate": "08-Oct-2026",
         "subject": "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share"},
        {"symbol": "BAD", "series": "EQ", "isin": "INE2", "exDate": "-", "subject": "Bonus 1:1"},
    ]).encode()
    df = ca.parse(raw)
    assert list(df["symbol"]) == ["BUILDPRO"]
    assert df.iloc[0]["kind"] == "split" and df.iloc[0]["factor"] == pytest.approx(0.2)
    assert str(df.iloc[0]["ex_date"]) == "2026-10-08"
