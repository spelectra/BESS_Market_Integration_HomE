"""Make sure every raw file the simulation needs exists; fetch the missing ones."""
from functools import partial
from pathlib import Path
from typing import Callable

from bess.data import entsoe, netztransparenz, regelleistung
from bess.paths import RAW_DIR


def _fetch_id_aep(start_date: str, end_date: str, raw_dir: Path) -> Path:
    token = netztransparenz.get_access_token()  # only requested when the file is actually missing
    return netztransparenz.fetch_and_save(start_date, end_date, "id_aep", token, raw_dir)


def _required_files(start_date: str, end_date: str, raw_dir: Path) -> dict[Path, Callable[[], Path]]:
    """Map each raw file the simulation reads -> the call that creates it."""
    files = {
        raw_dir / entsoe.build_raw_filename(start_date, end_date, "DE_LU", "da"):
            partial(entsoe.fetch_and_save, start_date, end_date, "DE_LU", raw_dir, "da"),
        raw_dir / netztransparenz.build_raw_filename(start_date, end_date, "id_aep"):
            partial(_fetch_id_aep, start_date, end_date, raw_dir),
    }
    for product in regelleistung.PRODUCTS:
        # partial binds `product` now; a lambda here would see only the loop's last value (late binding)
        path = raw_dir / regelleistung.build_raw_filename(start_date, end_date, product)
        files[path] = partial(regelleistung.fetch_and_save, start_date, end_date, product, raw_dir)
    return files


def ensure_raw_data(start_date: str, end_date: str, raw_dir: Path = RAW_DIR) -> list[Path]:
    """Fetch every required raw file that is not in raw_dir yet; return the paths that were fetched."""
    fetched = []
    for path, fetch in _required_files(start_date, end_date, raw_dir).items():
        if not path.exists():
            print(f"Missing {path.name}, fetching ...")
            fetched.append(fetch())
    return fetched
