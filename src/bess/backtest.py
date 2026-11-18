"""Rolling-horizon backtest: plan each day on a naive forecast, settle the plan at actual prices."""
import pandas as pd

from bess.battery import BatteryParams
from bess.optimize_arbitrage import DT_H, solve_arbitrage, solve_retrade

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


def rolling_two_stage_backtest(
    da_forecast: pd.Series,
    da_actual: pd.Series,
    id_forecast: pd.Series,
    id_actual: pd.Series,
    battery: BatteryParams,
    id_fee_eur_mwh: float,
    dt_h: float = DT_H,
) -> pd.DataFrame:
    """One row per local day: DA position first, then re-traded on ID. Revenues in EUR.

    Stage 1 (D-1 12:00): plan on `da_forecast`, settle the position at `da_actual`.
    Stage 2 (D-1 afternoon): keep the DA position, re-trade the change on `id_forecast`, settle at `id_actual`.
    Both stages end D at the start SoC ("end of D"), so no position spills into the next day.
    """
    local_day = da_actual.index.tz_convert(MARKET_TZ).date
    rows = []
    for day, da_actual_day in da_actual.groupby(local_day):
        steps = da_actual_day.index
        if da_forecast.loc[steps].isna().any():
            continue
        da_plan = solve_arbitrage(da_forecast.loc[steps], battery, dt_h)
        da_position = da_plan["discharge_mw"] - da_plan["charge_mw"]
        retrade = solve_retrade(id_forecast.loc[steps], da_position, battery, id_fee_eur_mwh, dt_h)
        delta = retrade["delta_mw"]

        da_eur = (dt_h * da_actual_day * da_position).sum()
        id_eur = (dt_h * (id_actual.loc[steps] * delta - id_fee_eur_mwh * delta.abs())).sum()
        rows.append({
            "day": day,
            "da_eur": da_eur,
            "id_eur": id_eur,
            "total_eur": da_eur + id_eur,
            "retraded_mwh": dt_h * delta.abs().sum(),
        })
    return pd.DataFrame(rows)
