"""CLI: two-stage backtest. DA position on D-1, re-traded on ID; every day ends at the start SoC.

Example: python scripts/run_two_stage_backtest.py --start 2026-01-01 --end 2026-02-01
  Stage 1: plan on yesterday's DA prices, settle at actual DA.
  Stage 2: re-trade the change on ID, using actual DA (known after 12:45 on D-1) as the ID forecast.
ID price: ID-AEP for now, since ENTSO-E publishes no IDA1 prices for DE-LU. ID-AEP is an index, so
the ID revenue is optimistic. Swap in IDA1 or continuous-ID prices once available.
"""
import argparse
from dataclasses import replace

import pandas as pd

from bess.backtest import previous_day_forecast, rolling_two_stage_backtest
from bess.battery import BatteryParams
from bess.data.load import load_energy_prices
from bess.simulation import POWER_LEVELS_MW

# Assumption, not a measured value: exchange + clearing fees plus some bid/ask spread per traded MWh.
DEFAULT_ID_FEE_EUR_MWH = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DA -> ID two-stage backtest for one period.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2026-01-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2026-02-01 (exclusive)")
    parser.add_argument("--id-fee", type=float, default=DEFAULT_ID_FEE_EUR_MWH, help="Cost per re-traded MWh in EUR")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prices = load_energy_prices(args.start, args.end)
    da_actual, id_actual = prices["day_ahead"], prices["id_aep"]
    da_forecast = previous_day_forecast(da_actual)

    rows = []
    for p_max in POWER_LEVELS_MW:
        battery = replace(BatteryParams(), p_max_mw=p_max)
        daily = rolling_two_stage_backtest(da_forecast, da_actual, da_actual, id_actual, battery, args.id_fee)
        totals = daily[["da_eur", "id_eur", "total_eur", "retraded_mwh"]].sum()
        rows.append({"power_mw": p_max, "days": len(daily), **totals})
    results = pd.DataFrame(rows)

    print(f"\nDA -> ID, {args.start} to {args.end} (exclusive), ID fee {args.id_fee} EUR/MWh, revenue in EUR:")
    print(results.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
