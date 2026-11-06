"""Fetch 15-min data from the Netztransparenz (German TSOs) API into data/raw."""
import io
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from bess.paths import RAW_DIR

# Constants
TOKEN_URL = "https://identity.netztransparenz.de/users/connect/token"
DATA_URL = "https://ds.netztransparenz.de/api/v1/data"
REQUEST_TIMEOUT_S = 60
MARKET_TZ = "Europe/Berlin"  # CLI dates are local days, same as fetch_entsoe
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"  # API expects UTC timestamps in this format

# Maps CLI dataset name -> (API endpoint, value column in the returned CSV)
DATASETS = {
    "id_aep": ("IdAep", "ID AEP in EUR/MWh"),
}


def get_access_token() -> str:
    """Request an OAuth2 access token (valid 1 h) with the client credentials from .env."""
    load_dotenv()  # reads .env from the project root
    client_id = os.getenv("NTP_CLIENT_ID")
    client_secret = os.getenv("NTP_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "NTP_CLIENT_ID / NTP_CLIENT_SECRET are not set. Copy .env.example to .env and add your "
            "Netztransparenz API client (https://extranet.netztransparenz.de → API-Clients)."
        )
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _to_utc_range(start_date: str, end_date: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Interpret CLI dates as local (Berlin) midnights and convert them to UTC for the API."""
    start = pd.Timestamp(start_date, tz=MARKET_TZ).tz_convert("UTC")
    end = pd.Timestamp(end_date, tz=MARKET_TZ).tz_convert("UTC")
    return start, end


def fetch_dataset(start_date: str, end_date: str, dataset: str, token: str) -> pd.Series:
    """Fetch one dataset for [start_date, end_date) and return a UTC-indexed series in EUR/MWh."""
    endpoint, value_column = DATASETS[dataset]
    start, end = _to_utc_range(start_date, end_date)
    url = f"{DATA_URL}/{endpoint}/{start.strftime(API_TIME_FORMAT)}/{end.strftime(API_TIME_FORMAT)}"
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()

    # API returns German-style CSV: ';' separator, ',' as decimal mark
    df = pd.read_csv(io.StringIO(response.text), sep=";", decimal=",")

    # The API states the time zone per row; pandas renames the duplicate second column to "Zeitzone.1"
    tz_columns = ["Zeitzone", "Zeitzone.1"]
    if not (df[tz_columns] == "UTC").all().all():
        raise ValueError(f"Expected all timestamps in UTC, got: {pd.unique(df[tz_columns].values.ravel())}")
    index = pd.to_datetime(df["Datum von"] + " " + df["(Uhrzeit) von"], utc=True)
    return pd.Series(df[value_column].to_numpy(), index=index, name="price_eur_mwh")


def save_to_csv(prices: pd.Series, file_path: Path) -> None:
    """Write a price series to CSV, creating parent folders if needed."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(file_path, index_label="timestamp_utc")


def build_raw_filename(start_date: str, end_date: str, dataset: str) -> str:
    """Standardized raw filename: <dataset>_DE_<YYYY-MM-DD>_<YYYY-MM-DD>.csv (end exclusive)."""
    start = pd.Timestamp(start_date).strftime("%Y-%m-%d")
    end = pd.Timestamp(end_date).strftime("%Y-%m-%d")
    return f"{dataset}_DE_{start}_{end}.csv"


def fetch_and_save(start_date: str, end_date: str, dataset: str, token: str, raw_dir: Path = RAW_DIR) -> Path:
    """Fetch one dataset, save it to raw_dir under the standard name, return the file path."""
    prices = fetch_dataset(start_date, end_date, dataset, token)
    file_path = raw_dir / build_raw_filename(start_date, end_date, dataset)
    save_to_csv(prices, file_path)
    return file_path
