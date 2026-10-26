import pandas as pd

from stockai.ingest import quality


def _prices(rows):
    return pd.DataFrame(rows, columns=["symbol", "open", "high", "low", "close", "prev_close"])


def test_ohlc_flags_close_above_high_and_zero_prices():
    issues = quality.check_ohlc(_prices([
        ("GOOD", 10, 11, 9, 10.5, 10),
        ("BADHIGH", 10, 10.2, 9, 10.5, 10),
        ("ZERO", 0, 11, 0, 10, 10),
    ]))
    assert {i["symbol"] for i in issues} == {"BADHIGH", "ZERO"}
    assert all(i["severity"] == "error" for i in issues)


def test_row_count_needs_history_and_flags_short_days():
    assert quality.check_row_count(100, [2900] * 3) == []
    assert quality.check_row_count(2900, [2950] * 10) == []
    [issue] = quality.check_row_count(1500, [2950] * 10)
    assert issue["check_name"] == "row_count"


def test_coverage_lists_missing_members():
    [issue] = quality.check_coverage({"A", "B"}, {"A", "B", "C"}, "NIFTY 500")
    assert issue["detail"]["missing"] == ["C"] and issue["severity"] == "warn"
    assert quality.check_coverage({"A"}, {"A"}, "NIFTY 500") == []


def test_extreme_moves_skip_adjusted_symbols():
    prices = _prices([
        ("SPLIT", 250, 260, 234, 250.2, 1302),
        ("JUMP", 400, 410, 395, 405, 272),
        ("CALM", 100, 101, 99, 100.5, 100),
    ])
    issues = quality.check_extreme_moves(prices, adjusted_symbols={"SPLIT"})
    assert [i["symbol"] for i in issues] == ["JUMP"]
