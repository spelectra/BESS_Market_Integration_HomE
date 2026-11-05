import os
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import pandas as pd
from pathlib import Path
import argparse

#Constants

# Day-ahead prices switched from hourly to 15-min resolution on 2025-10-01 (SDAC go-live)
DA_15MIN_START = pd.Timestamp("2025-10-01", tz="Europe/Brussels")

#Intraday auction prices 15-min intervals were only available from 2024-06-13 on
IDA_15MIN_START = pd.Timestamp("2024-06-13", tz="Europe/Brussels")


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

#check whether the specified date range is compatible with timeseries start
def _validated_range(start_date, end_date, min_start: pd.Timestamp):
    start = pd.Timestamp(start_date, tz='Europe/Brussels')
    end = pd.Timestamp(end_date, tz='Europe/Brussels')
    
    if start < min_start:
        raise ValueError(
            "no 15-min data before this date"
        )
    return start,end

    
#fetch intraday data
def fetch_intraday1_prices(start_date, end_date, country_code) -> pd.Series:
    start, end = _validated_range(start_date, end_date, IDA_15MIN_START)
    # returns panda series
    prices = client.query_intraday_prices(country_code, start=start, end=end, sequence=1)
    return prices

#fetch day ahead prices in specified interval
def fetch_day_ahead_prices(start_date, end_date, country_code) -> pd.Series:
    start, end = _validated_range(start_date, end_date, DA_15MIN_START)
    # returns panda series
    prices = client.query_day_ahead_prices(country_code, start=start, end=end)
    return prices


# Maps dataset name -> fetch function. Single source of truth for CLI choices and filenames.
FETCHERS = {
    "da": fetch_day_ahead_prices,
    "ida1": fetch_intraday1_prices,
}



def save_to_csv(prices: pd.Series, file_path: Path) -> None:
    """Write a price series to CSV, creating parent folders if needed."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    prices.tz_convert("UTC").to_csv(file_path, header=["price_eur_mwh"])
    
def build_raw_filename(start_date: str, end_date: str, country_code: str, price_type: str) -> str:
    """Standardized raw filename: da_prices_<COUNTRY>_<YYYY-MM-DD>_<YYYY-MM-DD>.csv (end exclusive)."""
    start = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    end = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    return f"{price_type}_{country_code}_{start}_{end}.csv"


def fetch_and_save(
    start_date: str,
    end_date: str,
    country_code: str = "DE_LU",
    raw_dir: Path = RAW_DIR,
    price_type: str = "da",
) -> Path:
    """Fetch one dataset, save it to raw_dir under the standard name, return the file path."""
    fetch = FETCHERS[price_type]
    prices = fetch(start_date, end_date, country_code)
    file_path = raw_dir / build_raw_filename(start_date, end_date, country_code, price_type)
    save_to_csv(prices, file_path)
    return file_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch ENTSO-E prices into data/raw.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument("--country", default="DE_LU", help="Bidding zone code (default: DE_LU)")
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=FETCHERS,
        default=["da"],
        help="One or more datasets to fetch (default: da)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for price_type in args.datasets:
        path = fetch_and_save(args.start, args.end, args.country, price_type=price_type)
        print(f"Saved {price_type} to {path}")



