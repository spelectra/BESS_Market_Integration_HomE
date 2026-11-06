"""CLI: fetch ENTSO-E prices into data/raw.

Example: python scripts/fetch_entsoe.py --start 2025-10-01 --end 2025-11-01 --datasets da
"""
import argparse

from bess.data import entsoe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ENTSO-E prices into data/raw.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument("--country", default="DE_LU", help="Bidding zone code (default: DE_LU)")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=entsoe.FETCHERS,
        default=["da"],
        help="One or more datasets to fetch (default: da)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for price_type in args.datasets:
        path = entsoe.fetch_and_save(args.start, args.end, args.country, price_type=price_type)
        print(f"Saved {price_type} to {path}")


if __name__ == "__main__":
    main()
