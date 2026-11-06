"""CLI: fetch FCR / aFRR capacity results from regelleistung.net into data/raw.

Example: python scripts/fetch_regelleistung.py --start 2025-10-01 --end 2025-11-01 --products FCR aFRR
"""
import argparse

from bess.data import regelleistung


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch FCR/aFRR capacity results into data/raw.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument(
        "--products",
        nargs="+",
        choices=regelleistung.PRODUCTS,
        default=regelleistung.PRODUCTS,
        help="One or more products to fetch (default: FCR aFRR)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for product in args.products:
        path = regelleistung.fetch_and_save(args.start, args.end, product)
        print(f"Saved {product} to {path}")


if __name__ == "__main__":
    main()
