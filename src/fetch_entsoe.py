import os
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import pandas as pd
from pathlib import Path
import argparse

# Day-ahead prices switched from hourly to 15-min resolution on 2025-10-01 (SDAC go-live)
DA_15MIN_START = pd.Timestamp("2025-10-01", tz="Europe/Brussels")

#location to save
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


# Load the ENTSOE_API_KEY from the .env file
load_dotenv()  # reads .env from the project root
api_key = os.getenv("ENTSOE_API_KEY")
if not api_key:
    raise RuntimeError(
        "ENTSOE_API_KEY is not set. Copy .env.example to .env and add your own ENTSO-E key."
    )
client = EntsoePandasClient(api_key)

#fetch day ahead prices in specified interval
def fetch_day_ahead_prices(start_date, end_date, country_code):
    start = pd.Timestamp(start_date, tz='Europe/Brussels')
    end = pd.Timestamp(end_date, tz='Europe/Brussels')
    country_code = country_code 
    
    if start < DA_15MIN_START:
        raise ValueError(
            f"Start date {start.date()} is before {DA_15MIN_START.date()}: "
            "day-ahead prices are hourly before this date, not 15-min."
        )

    # returns panda series
    prices = client.query_day_ahead_prices(country_code, start=start, end=end)
    return prices



def save_to_csv(prices: pd.Series, file_path: Path) -> None:
    """Write a price series to CSV, creating parent folders if needed."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    prices.tz_convert("UTC").to_csv(file_path, header=["price_eur_mwh"])
    
def build_raw_filename(start_date: str, end_date: str, country_code: str) -> str:
    """Standardized raw filename: da_prices_<COUNTRY>_<YYYY-MM-DD>_<YYYY-MM-DD>.csv (end exclusive)."""
    start = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    end = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    return f"da_prices_{country_code}_{start}_{end}.csv"


def fetch_and_save(
    start_date: str,
    end_date: str,
    country_code: str = "DE_LU",
    raw_dir: Path = RAW_DIR,
) -> Path:
    """Fetch day-ahead prices, save them to raw_dir under the standard name, return the file path."""
    prices = fetch_day_ahead_prices(start_date, end_date, country_code)
    file_path = raw_dir / build_raw_filename(start_date, end_date, country_code)
    save_to_csv(prices, file_path)
    return file_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ENTSO-E day-ahead prices into data/raw.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument("--country", default="DE_LU", help="Bidding zone code (default: DE_LU)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    path = fetch_and_save(args.start, args.end, args.country)
    print(f"Saved to {path}")



