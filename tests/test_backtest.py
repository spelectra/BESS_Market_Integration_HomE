"""Hand-checkable backtest cases: forecast alignment and the settlement logic."""
import numpy as np
import pandas as pd
import pytest

from bess.backtest import previous_day_forecast, rolling_backtest
from bess.battery import BatteryParams


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
