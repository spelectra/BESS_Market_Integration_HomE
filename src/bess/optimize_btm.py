"""Behind-the-meter battery at a site that buys at spot: shift load to cheap quarter-hours, shave the peak."""
from dataclasses import dataclass

import cvxpy as cp
import pandas as pd

from bess.battery import BatteryParams
from bess.optimize_arbitrage import DT_H, battery_model, maximize

HOURS_PER_YEAR = 8760


@dataclass(frozen=True)
class GridTariff:
    """Grid fees with 15-min power metering. Default: Stadtwerke Wertheim 2026, Mittelspannung, < 2,500 h/a."""

    demand_charge_eur_mw_a: float = 15_340.0  # 15.34 EUR/kW·a on the highest 15-min grid draw of the year
    energy_fee_eur_mwh: float = 68.9  # 6.89 ct/kWh on every MWh drawn from the grid


def site_cost_eur(grid_mw: pd.Series, spot: pd.Series, tariff: GridTariff, dt_h: float = DT_H) -> dict[str, float]:
    """Energy cost (spot + grid energy fee) and demand charge of one grid-draw profile.

    The annual demand charge is pro-rated to the period length, so periods shorter than a year compare fairly.
    """
    period_years = len(grid_mw) * dt_h / HOURS_PER_YEAR
    return {
        "energy_eur": float((dt_h * (spot + tariff.energy_fee_eur_mwh) * grid_mw).sum()),
        "demand_eur": float(tariff.demand_charge_eur_mw_a * period_years * grid_mw.max()),
    }


def solve_btm(
    spot: pd.Series,
    load_mw: pd.Series,
    battery: BatteryParams,
    tariff: GridTariff,
    dt_h: float = DT_H,
    allow_simultaneous: bool = False,
) -> pd.DataFrame:
    """Minimize the site's grid cost with a battery behind the meter (perfect foresight on spot and load).

    grid = load + charge - discharge must stay >= 0: no feed-in, the battery only serves the site.
    One `peak` variable carries the demand charge, so the LP trades off spot savings against the peak.
    """
    n = len(spot)
    charge, discharge, soc, constraints, solver = battery_model(n, battery, dt_h, allow_simultaneous)
    grid = load_mw.to_numpy() + charge - discharge
    peak = cp.Variable(nonneg=True)
    constraints += [grid >= 0, grid <= peak]

    period_years = n * dt_h / HOURS_PER_YEAR
    cost = dt_h * (spot.to_numpy() + tariff.energy_fee_eur_mwh) @ grid + tariff.demand_charge_eur_mw_a * period_years * peak
    maximize(-cost, constraints, solver)  # maximizing -cost == minimizing cost

    return pd.DataFrame(
        {
            "charge_mw": charge.value,
            "discharge_mw": discharge.value,
            "soc_mwh": soc.value[1:],
            "grid_mw": grid.value,
        },
        index=spot.index,
    )
