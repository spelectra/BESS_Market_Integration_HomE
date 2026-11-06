"""CLI: perfect-foresight revenue per market and power level for one period.

Example: python scripts/run_simulation.py --start 2025-10-01 --end 2025-11-01
Needs the raw files for the same period (see the fetch_*.py scripts).
"""
import argparse

from bess.data.ensure import ensure_raw_data
from bess.paths import PROCESSED_DIR
from bess.simulation import run_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the BESS revenue simulation for one period.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not download missing raw files; fail if one is missing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.no_fetch:
        ensure_raw_data(args.start, args.end)  # fetches only the files that are missing in data/raw
    results = run_simulation(args.start, args.end)

    revenue_table = results.pivot(index="market", columns="power_mw", values="revenue_eur")
    revenue_table.columns = [f"{p:g} MW" for p in revenue_table.columns]
    print(f"\nRevenue in EUR, {args.start} to {args.end} (exclusive), 3 MWh, perfect foresight, NOT additive:")
    print(revenue_table.round(0).to_string())

    print("\nLP plausibility check (arbitrage markets only):")
    checks = results.dropna(subset=["full_cycles_per_day"])
    print(checks[["market", "power_mw", "full_cycles_per_day", "simultaneous_steps"]].round(2).to_string(index=False))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"revenue_{args.start}_{args.end}.csv"
    results.to_csv(out_path, index=False)
    print(f"\nSaved full results to {out_path}")


if __name__ == "__main__":
    main()
