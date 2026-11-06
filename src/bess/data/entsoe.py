"""Fetch day-ahead and intraday auction prices from ENTSO-E into data/raw."""
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient

from bess.paths import RAW_DIR

# Constants

# Day-ahead prices switched from hourly to 15-min resolution on 2025-10-01 (SDAC go-live)
DA_15MIN_START = pd.Timestamp("2025-10-01", tz="Europe/Brussels")

# Intraday auction prices 15-min intervals were only available from 2024-06-13 on
IDA_15MIN_START = pd.Timestamp("2024-06-13", tz="Europe/Brussels")


@lru_cache(maxsize=1)
def _get_client() -> EntsoePandasClient:
    """Create the ENTSO-E client on first use (not at import), so importing this module needs no key."""
    load_dotenv()  # reads .env from the project root
    api_key = os.getenv("ENTSOE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ENTSOE_API_KEY is not set. Copy .env.example to .env and add your own ENTSO-E key."
        )
    return EntsoePandasClient(api_key)


# check whether the specified date range is compatible with timeseries start
def _validated_range(start_date, end_date, min_start: pd.Timestamp):
    start = pd.Timestamp(start_date, tz="Europe/Brussels")
    end = pd.Timestamp(end_date, tz="Europe/Brussels")

    if start < min_start:
        raise ValueError("no 15-min data before this date")
    return start, end


# fetch intraday data
def fetch_intraday1_prices(start_date, end_date, country_code) -> pd.Series:
    start, end = _validated_range(start_date, end_date, IDA_15MIN_START)
    # returns panda series
    prices = _get_client().query_intraday_prices(country_code, start=start, end=end, sequence=1)
    return prices


# fetch day ahead prices in specified interval
def fetch_day_ahead_prices(start_date, end_date, country_code) -> pd.Series:
    start, end = _validated_range(start_date, end_date, DA_15MIN_START)
    # returns panda series
    prices = _get_client().query_day_ahead_prices(country_code, start=start, end=end)
    # entsoe-py truncates with after=end (inclusive); drop the end timestamp so the range is [start, end)
    prices = prices[prices.index < end]
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
    """Standardized raw filename: <price_type>_<COUNTRY>_<YYYY-MM-DD>_<YYYY-MM-DD>.csv (end exclusive)."""
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
