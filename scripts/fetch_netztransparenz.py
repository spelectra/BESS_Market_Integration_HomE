"""CLI: fetch netztransparenz data (e.g. ID-AEP) into data/raw.

Example: python scripts/fetch_netztransparenz.py --start 2025-10-01 --end 2025-11-01
"""
import argparse

from bess.data import netztransparenz


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Netztransparenz data into data/raw.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=netztransparenz.DATASETS,
        default=["id_aep"],
        help="One or more datasets to fetch (default: id_aep)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = netztransparenz.get_access_token()  # one token for all datasets; it is valid for 1 h
    for dataset in args.datasets:
        path = netztransparenz.fetch_and_save(args.start, args.end, dataset, token)
        print(f"Saved {dataset} to {path}")


if __name__ == "__main__":
    main()
