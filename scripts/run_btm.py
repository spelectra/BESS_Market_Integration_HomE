"""CLI: behind-the-meter battery at the Wertheim charging site (spot supply, MS grid tariff, perfect foresight).

Example: python scripts/run_btm.py --start 2026-01-01 --end 2026-11-01
The battery shifts site load to cheap quarter-hours and shaves the peak; no feed-in into the grid.
Solved as a pure LP (no charge/discharge binaries): a 10-month MILP does not finish in reasonable time.
The LP may charge and discharge at once where spot + grid energy fee < 0; "simultaneous_mwh" shows how much.
"""
import argparse
from dataclasses import replace

import numpy as np
import pandas as pd

from bess.battery import BatteryParams
from bess.data.load import load_energy_prices, load_site_demand
from bess.optimize_arbitrage import DT_H
from bess.optimize_btm import HOURS_PER_YEAR, GridTariff, site_cost_eur, solve_btm
from bess.simulation import POWER_LEVELS_MW

FULL_LOAD_HOURS_THRESHOLD = 2500  # grid tariff switches between the two price sets here


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the behind-the-meter simulation for one period.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2026-01-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2026-11-01 (exclusive)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spot = load_energy_prices(args.start, args.end)["day_ahead"]
    load = load_site_demand(args.start, args.end)
    tariff = GridTariff()
    baseline = site_cost_eur(load, spot, tariff)

    rows = [{"power_mw": 0.0, "peak_mw": load.max(), **baseline, "simultaneous_mwh": 0.0}]
    for p_max in POWER_LEVELS_MW:
        battery = replace(BatteryParams(), p_max_mw=p_max)
        result = solve_btm(spot, load, battery, tariff, allow_simultaneous=True)
        simultaneous_mwh = DT_H * np.minimum(result["charge_mw"], result["discharge_mw"]).sum()
        cost = site_cost_eur(result["grid_mw"], spot, tariff)
        rows.append({"power_mw": p_max, "peak_mw": result["grid_mw"].max(), **cost, "simultaneous_mwh": simultaneous_mwh})
    results = pd.DataFrame(rows)
    results["total_eur"] = results["energy_eur"] + results["demand_eur"]
    results["savings_eur"] = results["total_eur"].iloc[0] - results["total_eur"]

    annual_energy_mwh = DT_H * load.sum() * HOURS_PER_YEAR / (len(load) * DT_H)  # battery losses ignored here
    results["full_load_hours"] = annual_energy_mwh / results["peak_mw"]
    if (results["full_load_hours"] >= FULL_LOAD_HOURS_THRESHOLD).any():
        print(f"WARNING: >= {FULL_LOAD_HOURS_THRESHOLD} full-load hours in some rows, the < 2,500 h tariff no longer applies")

    print(f"\nBTM at Wertheim, {args.start} to {args.end} (exclusive), grid cost in EUR (row 0 = no battery):")
    print(results.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
