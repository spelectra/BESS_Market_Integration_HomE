"""Hand-checkable LP cases: if these fail, the model equations are wrong, not the data."""
import numpy as np
import pandas as pd
import pytest

from bess.battery import BatteryParams
from bess.optimize_arbitrage import solve_arbitrage, summarize_dispatch


def _prices(values: list[float]) -> pd.Series:
    index = pd.date_range("2025-10-01", periods=len(values), freq="15min", tz="UTC")
    return pd.Series(values, index=index, dtype=float)


def test_one_cheap_one_expensive_step():
    # Charge 1 MW for 15 min at 0 EUR -> stores 0.93 * 0.25 MWh. Getting the same energy back out
    # allows discharging 0.93 * 0.93 MW in the next step at 100 EUR/MWh: 100 * 0.8649 * 0.25 EUR.
    battery = BatteryParams(p_max_mw=1.0)
    dispatch = solve_arbitrage(_prices([0.0, 100.0]), battery)
    assert dispatch["revenue_eur"].sum() == pytest.approx(100 * 0.93**2 * 0.25, rel=1e-4)


def test_flat_prices_earn_nothing():
    dispatch = solve_arbitrage(_prices([50.0] * 8), BatteryParams())
    assert dispatch["revenue_eur"].sum() == pytest.approx(0.0, abs=1e-4)


def test_soc_stays_in_window_and_ends_at_start():
    battery = BatteryParams(p_max_mw=3.0)
    prices = _prices(list(np.random.default_rng(0).normal(80, 40, size=96)))
    dispatch = solve_arbitrage(prices, battery)
    assert dispatch["soc_mwh"].min() >= battery.soc_min_mwh - 1e-6
    assert dispatch["soc_mwh"].max() <= battery.soc_max_mwh + 1e-6
    assert dispatch["soc_mwh"].iloc[-1] == pytest.approx(battery.soc_start_mwh, abs=1e-6)


def test_summary_counts_cycles():
    battery = BatteryParams(p_max_mw=1.0)
    summary = summarize_dispatch(solve_arbitrage(_prices([0.0, 100.0]), battery), battery)
    # 0.8649 MW * 0.25 h discharged over 0.5 h = 1/48 day, divided by 3 MWh
    assert summary["full_cycles_per_day"] == pytest.approx(0.93**2 * 0.25 / 3.0 / (0.5 / 24), rel=1e-4)
