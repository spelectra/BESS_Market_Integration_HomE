"""Run every market × power level for one period and collect the results in one table."""
from dataclasses import replace
from pathlib import Path

import pandas as pd

from bess.battery import BatteryParams
from bess.capacity_revenue import afrr_revenue, fcr_revenue
from bess.data.load import load_capacity_prices, load_energy_prices
from bess.optimize_arbitrage import solve_arbitrage, summarize_dispatch
from bess.paths import RAW_DIR

POWER_LEVELS_MW = (0.8,1.0, 2.0, 3.0)
CAPACITY_REVENUE = {"fcr": fcr_revenue, "afrr": afrr_revenue}  # market -> revenue function


def run_simulation(
    start_date: str,
    end_date: str,
    base_battery: BatteryParams = BatteryParams(),
    power_levels_mw: tuple[float, ...] = POWER_LEVELS_MW,
    raw_dir: Path = RAW_DIR,
) -> pd.DataFrame:
    """Return one row per (market, power level): revenue, cycles/day and the LP sanity check.

    Each market is evaluated on its own; the revenues are alternatives, not additive.
    """
    energy_prices = load_energy_prices(start_date, end_date, raw_dir)
    capacity_blocks = load_capacity_prices(start_date, end_date, raw_dir)

    rows = []
    for p_max in power_levels_mw:
        battery = replace(base_battery, p_max_mw=p_max)  # same battery, only the power changes
        for market, prices in energy_prices.items():
            summary = summarize_dispatch(solve_arbitrage(prices, battery), battery)
            rows.append({"market": market, "power_mw": p_max, **summary})
        for market, revenue_fn in CAPACITY_REVENUE.items():
            rows.append({"market": market, "power_mw": p_max, "revenue_eur": revenue_fn(capacity_blocks[market], p_max)})
    return pd.DataFrame(rows)
