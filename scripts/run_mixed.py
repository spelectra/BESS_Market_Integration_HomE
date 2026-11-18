"""CLI: mixed BTM/FTM at Wertheim with calendar block rules (perfect foresight on DA and site load).

Example: python scripts/run_mixed.py --start 2026-01-01 --end 2026-11-01 --power-mw 1.0
value_eur = spot value of the battery output - extra demand charge vs. the site without a battery.
FTM here is DA only; the ID re-trade from run_two_stage_backtest.py would come on top in FTM steps.
"""
import argparse
from dataclasses import replace

import pandas as pd

from bess.battery import BatteryParams
from bess.data.load import load_energy_prices, load_site_demand
from bess.optimize_arbitrage import DT_H
from bess.optimize_btm import GridTariff, site_cost_eur
from bess.optimize_mixed import btm_rules, solve_mixed_two_pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare BTM/FTM block rules for one period.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2026-01-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2026-11-01 (exclusive)")
    parser.add_argument("--power-mw", type=float, default=1.0, help="Battery power in MW (default: 1.0)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spot = load_energy_prices(args.start, args.end)["day_ahead"]
    load = load_site_demand(args.start, args.end)
    battery = replace(BatteryParams(), p_max_mw=args.power_mw)
    tariff = GridTariff()
    baseline_demand_eur = site_cost_eur(load, spot, tariff)["demand_eur"]

    rows = []
    for rule, btm_mask in btm_rules(spot.index).items():
        result = solve_mixed_two_pass(spot, load, btm_mask, battery, tariff)
        spot_value = DT_H * (spot * result["output_mw"]).sum()
        demand_eur = site_cost_eur(result["grid_mw"], spot, tariff)["demand_eur"]
        rows.append({
            "rule": rule,
            "btm_share": btm_mask.mean(),
            "peak_mw": result["grid_mw"].max(),
            "spot_value_eur": spot_value,
            "demand_saving_eur": baseline_demand_eur - demand_eur,
            "value_eur": spot_value + baseline_demand_eur - demand_eur,
        })
    results = pd.DataFrame(rows).sort_values("value_eur", ascending=False)

    print(f"\nMixed BTM/FTM, {args.start} to {args.end} (exclusive), {args.power_mw:g} MW / 3 MWh, EUR:")
    print(results.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
