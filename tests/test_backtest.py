"""Hand-checkable backtest cases: forecast alignment and the settlement logic."""
import numpy as np
import pandas as pd
import pytest

from bess.backtest import previous_day_forecast, rolling_backtest, rolling_two_stage_backtest
from bess.battery import BatteryParams
from bess.optimize_arbitrage import solve_arbitrage, solve_retrade


def _local_days(start: str, n_days: int) -> pd.Series:
    """Random 15-min UTC prices covering n_days local Berlin days (handles 92/100-step DST days)."""
    start_utc = pd.Timestamp(start, tz="Europe/Berlin").tz_convert("UTC")
    end_utc = (pd.Timestamp(start) + pd.Timedelta(days=n_days)).tz_localize("Europe/Berlin").tz_convert("UTC")
    index = pd.date_range(start_utc, end_utc, freq="15min", inclusive="left")
    return pd.Series(np.random.default_rng(0).normal(80, 40, len(index)), index=index)


def test_forecast_is_previous_day_at_same_wall_clock_time():
    prices = _local_days("2026-03-28", 3)  # includes the spring-forward day 2026-03-29
    forecast = previous_day_forecast(prices)
    local = prices.index.tz_convert("Europe/Berlin")
    at_18h = local.hour == 18
    assert forecast[at_18h].iloc[4:8].to_numpy() == pytest.approx(prices[at_18h].iloc[0:4].to_numpy())
    assert forecast[local.date == local[0].date()].isna().all()  # first day has no previous day


def test_perfect_forecast_realizes_perfect_foresight():
    actual = _local_days("2026-01-01", 2)
    daily = rolling_backtest(actual, actual, BatteryParams())
    assert daily["realized_eur"].to_numpy() == pytest.approx(daily["perfect_foresight_eur"].to_numpy(), rel=1e-6)


def test_retrade_keeps_an_already_optimal_position():
    prices = _local_days("2026-01-01", 1)
    plan = solve_arbitrage(prices, BatteryParams())
    base = plan["discharge_mw"] - plan["charge_mw"]
    retrade = solve_retrade(prices, base, BatteryParams(), fee_eur_mwh=1.0)  # same prices: nothing new to learn
    assert retrade["delta_mw"].abs().max() == pytest.approx(0.0, abs=1e-6)


def test_two_stage_with_flat_da_earns_id_perfect_foresight():
    # Flat DA prices -> no DA position. Then the ID stage alone is plain arbitrage on the ID prices.
    id_prices = _local_days("2026-01-01", 1)
    da_prices = pd.Series(50.0, index=id_prices.index)
    daily = rolling_two_stage_backtest(da_prices, da_prices, id_prices, id_prices, BatteryParams(), id_fee_eur_mwh=0.0)
    expected = solve_arbitrage(id_prices, BatteryParams())["revenue_eur"].sum()
    assert daily["da_eur"].iloc[0] == pytest.approx(0.0, abs=1e-6)
    assert daily["id_eur"].iloc[0] == pytest.approx(expected, rel=1e-6)
