"""Fetch 4-h FCR and aFRR capacity auction results from regelleistung.net into data/raw."""
import argparse
import io
from pathlib import Path
import time

import pandas as pd
import requests

# Constants
BASE_URL = "https://www.regelleistung.net/apps/cpp-publisher/api/v1/download/tenders/resultsoverview"
PRODUCTS = ["FCR", "aFRR"]  # values for the API's productTypes parameter
PRODUCT_COLUMN = {"FCR": "PRODUCTNAME", "aFRR": "PRODUCT"}  # e.g. "NEGPOS_00_04" / "POS_00_04"
MARKET_TZ = "Europe/Berlin"  # 4-h blocks are defined in German local time
REQUEST_TIMEOUT_S = 30    # max wait for one response
REQUEST_DELAY_S = 0.25    # pause between requests

# location to save
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def fetch_day(day: pd.Timestamp, product: str) -> pd.DataFrame:
    """Download one day's capacity results for one product and parse the Excel into a DataFrame."""
    params = {
        "date": day.strftime("%Y-%m-%d"),
        "exportFormat": "xlsx",
        "market": "CAPACITY",
        "productTypes": product,
    }
    response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()  # turn HTTP 4xx/5xx into an exception instead of parsing an error page
    return pd.read_excel(io.BytesIO(response.content))  # parse in memory, no temp .xlsx on disk


def add_block_start_utc(df: pd.DataFrame, product: str) -> pd.DataFrame:
    """Add a UTC timestamp for the start of each 4-h block, e.g. DATE_FROM + 'POS_04_08' -> 04:00 local."""
    start_hour = df[PRODUCT_COLUMN[product]].str.split("_").str[-2].astype(int)
    local_start = pd.to_datetime(df["DATE_FROM"]) + pd.to_timedelta(start_hour, unit="h")
    df.insert(0, "block_start_utc", local_start.dt.tz_localize(MARKET_TZ).dt.tz_convert("UTC"))
    return df


def fetch_range(start_date: str, end_date: str, product: str) -> pd.DataFrame:
    """Fetch all days in [start_date, end_date) for one product and stack them into one DataFrame."""
    days = pd.date_range(start_date, end_date, freq="D", inclusive="left")
    frames: list[pd.DataFrame] = []
    failed_days: list[pd.Timestamp] = []
    for day in days:
        time.sleep(REQUEST_DELAY_S)
        try:
            df = fetch_day(day, product)
        except requests.HTTPError as err:
            failed_days.append(day)
        else:
            frames.append(df)
    if not frames: 
        raise RuntimeError(f"No data fetched for {product}; failed days: {failed_days}")
    print(failed_days)
    return add_block_start_utc(pd.concat(frames, ignore_index=True), product)


def build_raw_filename(start_date: str, end_date: str, product: str) -> str:
    """Standardized raw filename: <product>_capacity_<YYYY-MM-DD>_<YYYY-MM-DD>.csv (end exclusive)."""
    start = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    end = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    return f"{product.lower()}_capacity_{start}_{end}.csv"


def fetch_and_save(start_date: str, end_date: str, product: str, raw_dir: Path = RAW_DIR) -> Path:
    """Fetch one product for the date range, save it to raw_dir under the standard name, return the path."""
    df = fetch_range(start_date, end_date, product)
    file_path = raw_dir / build_raw_filename(start_date, end_date, product)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    return file_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch FCR/aFRR capacity results into data/raw.")
    parser.add_argument("--start", required=True, help="Start date, e.g. 2025-10-01 (inclusive)")
    parser.add_argument("--end", required=True, help="End date, e.g. 2025-11-01 (exclusive)")
    parser.add_argument(
        "--products",
        nargs="+",
        choices=PRODUCTS,
        default=PRODUCTS,
        help="One or more products to fetch (default: FCR aFRR)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    for product in args.products:
        path = fetch_and_save(args.start, args.end, product)
        print(f"Saved {product} to {path}")
