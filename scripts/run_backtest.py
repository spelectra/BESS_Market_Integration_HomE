"""CLI: naive-forecast rolling backtest for DA and ID, compared with daily perfect foresight.

Example: python scripts/run_backtest.py --start 2026-01-01 --end 2026-02-01
Scenarios (each with the full battery, NOT additive):
  day_ahead: plan on yesterday's DA prices, settle at today's DA prices
  id_aep:    plan on today's DA prices (known before intraday trading), settle at ID-AEP
The first day of the period has no DA forecast, so it is skipped in the day_ahead scenario.
"""
import argparse
from dataclasses import replace

import pandas as pd

from bess.backtest import previous_day_forecast, rolling_backtest
from bess.battery import BatteryParams
from bess.data.load import load_energy_prices
from bess.simulation import POWER_LEVELS_MW


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the naive-forecast backtest for one period.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2026-01-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2026-02-01 (exclusive)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prices = load_energy_prices(args.start, args.end)
    scenarios = {  # market -> (forecast used for the decision, actual price used for settlement)
        "day_ahead": (previous_day_forecast(prices["day_ahead"]), prices["day_ahead"]),
        "id_aep": (prices["day_ahead"], prices["id_aep"]),
    }

    rows = []
    for p_max in POWER_LEVELS_MW:
        battery = replace(BatteryParams(), p_max_mw=p_max)
        for market, (forecast, actual) in scenarios.items():
            daily = rolling_backtest(forecast, actual, battery)
            totals = daily[["planned_eur", "realized_eur", "perfect_foresight_eur"]].sum()
            rows.append({"market": market, "power_mw": p_max, "days": len(daily), **totals})
    results = pd.DataFrame(rows)
    results["capture_rate"] = results["realized_eur"] / results["perfect_foresight_eur"]

    print(f"\nRevenue in EUR, {args.start} to {args.end} (exclusive), daily horizon, NOT additive:")
    print(results.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
