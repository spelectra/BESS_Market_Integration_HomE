"""Load raw CSVs from data/raw into clean, validated price data for the simulation."""
from pathlib import Path

import pandas as pd

from bess.data import entsoe, netztransparenz, regelleistung
from bess.paths import RAW_DIR

MARKET_TZ = "Europe/Berlin"
STEP = pd.Timedelta(minutes=15)
BLOCK_LENGTH = pd.Timedelta(hours=4)
BLOCKS_PER_DAY = 6

# FCR is pay-as-cleared: everyone gets the settlement price, in EUR/MW per 4-h block.
FCR_PRICE_COLUMN = "GERMANY_SETTLEMENTCAPACITY_PRICE_[EUR/MW]"
# aFRR capacity is pay-as-bid: we assume our bid earns the average accepted price, in (EUR/MW)/h.
# Upper-bound alternative: "GERMANY_MARGINAL_CAPACITY_PRICE_[(EUR/MW)/h]" (bid exactly the highest accepted price).
AFRR_PRICE_COLUMN = "GERMANY_AVERAGE_CAPACITY_PRICE_[(EUR/MW)/h]"


def _read_raw(raw_dir: Path, filename: str, fetch_hint: str) -> pd.DataFrame:
    """Read one raw CSV, or fail with a message that says which fetch script to run."""
    path = raw_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Fetch it first: python scripts/{fetch_hint}")
    return pd.read_csv(path)


def _check_regular_15min(prices: pd.Series, name: str) -> None:
    """Fail fast on duplicate timestamps or gaps, which would silently corrupt the SoC balance."""
    if prices.index.duplicated().any():
        raise ValueError(f"{name}: duplicate timestamps")
    steps = prices.index.to_series().diff().dropna()
    if not (steps == STEP).all():
        raise ValueError(f"{name}: irregular time steps {steps.value_counts().to_dict()}")
    if prices.isna().any():
        raise ValueError(f"{name}: {prices.isna().sum()} missing prices")


def load_energy_prices(start_date: str, end_date: str, raw_dir: Path = RAW_DIR) -> dict[str, pd.Series]:
    """Return {"day_ahead": series, "id_aep": series}, 15-min UTC index, EUR/MWh."""
    sources = {
        "day_ahead": (entsoe.build_raw_filename(start_date, end_date, "DE_LU", "da"), "fetch_entsoe.py"),
        "id_aep": (netztransparenz.build_raw_filename(start_date, end_date, "id_aep"), "fetch_netztransparenz.py"),
    }
    prices = {}
    for market, (filename, script) in sources.items():
        hint = f"{script} --start {start_date} --end {end_date}"
        df = _read_raw(raw_dir, filename, hint)
        series = pd.Series(
            df["price_eur_mwh"].to_numpy(),
            index=pd.to_datetime(df.iloc[:, 0], utc=True),
            name=market,
        )
        _check_regular_15min(series, market)
        prices[market] = series
    return prices


def _block_hours(block_start_utc: pd.Series) -> pd.Series:
    """Actual block length in hours: 4 h, except 3 h / 5 h for the 00–04 block on DST change days."""
    local_start = block_start_utc.dt.tz_convert(MARKET_TZ).dt.tz_localize(None)
    local_end = (local_start + BLOCK_LENGTH).dt.tz_localize(MARKET_TZ).dt.tz_convert("UTC")
    return (local_end - block_start_utc) / pd.Timedelta(hours=1)


def _load_blocks(
    raw_dir: Path, start_date: str, end_date: str, product: str, product_column: str, price_column: str
) -> pd.DataFrame:
    """Return one row per block and direction: block_start_utc, block_hours, direction, price."""
    filename = regelleistung.build_raw_filename(start_date, end_date, product)
    df = _read_raw(raw_dir, filename, f"fetch_regelleistung.py --start {start_date} --end {end_date}")

    blocks = pd.DataFrame({
        "block_start_utc": pd.to_datetime(df["block_start_utc"], utc=True),
        "direction": df[product_column].str.split("_").str[0],  # "NEGPOS", "POS" or "NEG"
        "price": pd.to_numeric(df[price_column], errors="coerce"),  # "-" (no result) -> NaN
    })
    blocks = blocks.dropna(subset=["price"])  # e.g. empty second FCR tender rows
    blocks["block_hours"] = _block_hours(blocks["block_start_utc"])

    n_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
    expected = n_days * BLOCKS_PER_DAY * blocks["direction"].nunique()
    if blocks.duplicated(subset=["block_start_utc", "direction"]).any() or len(blocks) != expected:
        raise ValueError(f"{product}: expected {expected} unique blocks, got {len(blocks)}")
    return blocks.reset_index(drop=True)


def load_capacity_prices(start_date: str, end_date: str, raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Return {"fcr": blocks, "afrr": blocks}; prices in the units published by regelleistung.net."""
    return {
        "fcr": _load_blocks(raw_dir, start_date, end_date, "FCR", "PRODUCTNAME", FCR_PRICE_COLUMN),
        "afrr": _load_blocks(raw_dir, start_date, end_date, "aFRR", "PRODUCT", AFRR_PRICE_COLUMN),
    }
