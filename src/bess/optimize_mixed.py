"""Mixed BTM/FTM: a calendar rule assigns each quarter-hour to BTM (serve the site) or FTM (trade DA).

Accounting, the same for every rule:
  - battery output (discharge - charge) is worth the spot price in both modes: sold on DA (FTM) or not
    bought by the site (BTM). Site grid energy fees stay constant and are left out of the comparison.
  - in BTM steps the battery may only serve the site: grid = load - output >= 0, no feed-in.
  - the demand charge is set by the highest site grid draw; only BTM steps can lower it.
"""
from typing import Optional

import cvxpy as cp
import numpy as np
import pandas as pd

from bess.battery import BatteryParams
from bess.optimize_arbitrage import DT_H, battery_model, maximize
from bess.optimize_btm import HOURS_PER_YEAR, GridTariff

MARKET_TZ = "Europe/Berlin"
AUTUMN_MONTHS = (9, 10, 11)  # the site's peaks grew to ~2 MW in these months (WERHM 2026)
PEAK_CAP_TOLERANCE_MW = 1e-4  # numerical slack when the LP peak is reused as a hard cap in the MILP


def solve_mixed(
    spot: pd.Series,
    load_mw: pd.Series,
    btm_mask: pd.Series,
    battery: BatteryParams,
    tariff: GridTariff,
    peak_cap_mw: Optional[float] = None,
    dt_h: float = DT_H,
    allow_simultaneous: bool = False,
) -> pd.DataFrame:
    """Perfect-foresight dispatch for one BTM/FTM assignment.

    Without `peak_cap_mw` the peak is a decision variable carrying the pro-rated demand charge.
    With it, the peak is a fixed cap and only the spot value is maximized (used for the monthly MILPs).
    """
    charge, discharge, soc, constraints, solver = battery_model(len(spot), battery, dt_h, allow_simultaneous)
    output = discharge - charge  # MW out of the battery, + = discharge
    grid = load_mw.to_numpy() - cp.multiply(btm_mask.to_numpy(dtype=float), output)  # FTM steps: grid = load
    constraints.append(grid >= 0)  # no feed-in from the site in BTM steps
    spot_value = dt_h * spot.to_numpy() @ output

    if peak_cap_mw is None:
        peak = cp.Variable(nonneg=True)
        constraints.append(grid <= peak)
        period_years = len(spot) * dt_h / HOURS_PER_YEAR
        objective = spot_value - tariff.demand_charge_eur_mw_a * period_years * peak
    else:
        constraints.append(grid <= peak_cap_mw + PEAK_CAP_TOLERANCE_MW)
        objective = spot_value
    maximize(objective, constraints, solver)

    return pd.DataFrame(
        {"output_mw": output.value, "soc_mwh": soc.value[1:], "grid_mw": grid.value, "btm": btm_mask.to_numpy()},
        index=spot.index,
    )


def solve_mixed_two_pass(
    spot: pd.Series, load_mw: pd.Series, btm_mask: pd.Series, battery: BatteryParams, tariff: GridTariff
) -> pd.DataFrame:
    """Pass 1: LP over the whole period finds the peak. Pass 2: one MILP per month with that peak as a cap.

    The annual peak couples all months, so a monthly split alone cannot price it; the full-period MILP
    does not solve in reasonable time. Each month starts and ends at the start SoC.
    """
    lp = solve_mixed(spot, load_mw, btm_mask, battery, tariff, allow_simultaneous=True)
    peak_cap = float(lp["grid_mw"].max())

    local = spot.index.tz_convert(MARKET_TZ)
    months = []
    for _, steps in spot.groupby([local.year, local.month]).groups.items():
        months.append(solve_mixed(spot[steps], load_mw[steps], btm_mask[steps], battery, tariff, peak_cap_mw=peak_cap))
    return pd.concat(months).sort_index()


def btm_rules(index: pd.DatetimeIndex) -> dict[str, pd.Series]:
    """Calendar-only rules (no look-ahead on load or prices): True = BTM, False = FTM."""
    local = index.tz_convert(MARKET_TZ)
    weekend = np.asarray(local.dayofweek >= 5)
    midday = np.asarray((local.hour >= 10) & (local.hour < 18))
    rules = {
        "ftm_only": np.zeros(len(index), dtype=bool),
        "btm_only": np.ones(len(index), dtype=bool),
        "weekend_midday": weekend & midday,
        "daily_midday": midday,
        "autumn_weekend_midday": weekend & midday & np.isin(local.month, AUTUMN_MONTHS),
    }
    return {name: pd.Series(mask, index=index) for name, mask in rules.items()}
