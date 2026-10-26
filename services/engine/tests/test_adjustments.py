from datetime import date

import pandas as pd
import pytest

from stockai.prices import adjustments


def _actions(rows):
    return pd.DataFrame(rows, columns=["instrument_id", "ex_date", "kind", "factor"])


def _market(rows=()):
    return pd.DataFrame(list(rows), columns=["instrument_id", "ex_date", "ex_open", "prior_close"])


def test_split_and_bonus_on_same_day_multiply():
    ev = adjustments.events(
        _actions([(1, date(2026, 10, 8), "split", 0.5), (1, date(2026, 10, 8), "bonus", 0.5)]), _market()
    )
    assert len(ev) == 1
    assert ev.iloc[0]["factor"] == pytest.approx(0.25)
    assert ev.iloc[0]["kinds"] == "bonus,split"
    assert ev.iloc[0]["source"] == "corporate_action"


def test_dividends_and_rights_do_not_adjust():
    ev = adjustments.events(
        _actions([(1, date(2026, 10, 1), "other", None), (1, date(2026, 10, 2), "rights", None)]), _market()
    )
    assert ev.empty


def test_demerger_factor_is_market_implied():
    ev = adjustments.events(
        _actions([(7, date(2026, 10, 8), "demerger", None)]),
        _market([(7, date(2026, 10, 8), 39.0, 454.55)]),
    )
    assert ev.iloc[0]["factor"] == pytest.approx(39.0 / 454.55)
    assert ev.iloc[0]["source"] == "market_implied"


def test_demerger_without_price_drop_is_ignored():
    ev = adjustments.events(
        _actions([(7, date(2026, 10, 8), "demerger", None)]),
        _market([(7, date(2026, 10, 8), 460.0, 454.55)]),
    )
    assert ev.empty


def test_apply_scales_history_before_each_ex_date():
    prices = pd.DataFrame({
        "trade_date": [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)],
        "open": [1000.0, 500.0, 100.0], "high": [1000.0, 500.0, 100.0],
        "low": [1000.0, 500.0, 100.0], "close": [1000.0, 500.0, 100.0],
        "volume": [10, 20, 100],
    })
    adj = pd.DataFrame({"ex_date": [date(2026, 2, 1), date(2026, 3, 1)], "factor": [0.5, 0.2]})
    out = adjustments.apply(prices, adj)
    assert list(out["close"]) == pytest.approx([100.0, 100.0, 100.0])
    assert list(out["volume"]) == [100, 100, 100]
    assert list(out["adj_factor"]) == pytest.approx([0.1, 0.2, 1.0])


def test_apply_without_events_is_identity():
    prices = pd.DataFrame({"trade_date": [date(2026, 1, 1)], "open": [1.0], "high": [1.0], "low": [1.0],
                           "close": [1.0], "volume": [5]})
    out = adjustments.apply(prices, pd.DataFrame(columns=["ex_date", "factor"]))
    assert out["close"].iloc[0] == 1.0 and out["adj_factor"].iloc[0] == 1.0
