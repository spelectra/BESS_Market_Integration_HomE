"""Rolling-horizon backtest: plan each day on a naive forecast, settle the plan at actual prices."""
import pandas as pd

from bess.battery import BatteryParams
from bess.optimize_arbitrage import DT_H, solve_arbitrage

MARKET_TZ = "Europe/Berlin"  # market days are local days: 96 steps, 92/100 on DST change days


def previous_day_forecast(prices: pd.Series) -> pd.Series:
    """Naive forecast: the price at the same local wall-clock time on the previous day.

    Matching on wall-clock time (not a fixed 96-step shift) keeps 18:00 aligned with 18:00 across
    DST changes. The first day has no previous day and stays NaN.
    """
    wall = prices.index.tz_convert(MARKET_TZ).tz_localize(None)
    yesterday = pd.Series(prices.to_numpy(), index=wall + pd.Timedelta(days=1))
    yesterday = yesterday[~yesterday.index.duplicated()]  # fall-back day: 02:00-03:00 exists twice
    forecast = yesterday.reindex(wall).ffill(limit=4)  # day after spring-forward: 02:00-03:00 missing
    return pd.Series(forecast.to_numpy(), index=prices.index, name=f"{prices.name}_forecast")


def rolling_backtest(
    forecast: pd.Series, actual: pd.Series, battery: BatteryParams, dt_h: float = DT_H
) -> pd.DataFrame:
    """One row per local day: planned, realized and perfect-foresight revenue in EUR.

    Each day is solved on its own with SoC end == start, so every day starts at the same SoC and no
    state needs to be carried over. Days without a complete forecast are skipped.
    """
    local_day = actual.index.tz_convert(MARKET_TZ).date
    rows = []
    for day, actual_day in actual.groupby(local_day):
        forecast_day = forecast.loc[actual_day.index]
        if forecast_day.isna().any():
            continue
        plan = solve_arbitrage(forecast_day, battery, dt_h)  # decided with forecast information only
        net_mw = plan["discharge_mw"] - plan["charge_mw"]
        rows.append({
            "day": day,
            "planned_eur": plan["revenue_eur"].sum(),  # what the plan expected to earn
            "realized_eur": (dt_h * actual_day * net_mw).sum(),  # same plan, settled at actual prices
            "perfect_foresight_eur": solve_arbitrage(actual_day, battery, dt_h)["revenue_eur"].sum(),
        })
    return pd.DataFrame(rows)
