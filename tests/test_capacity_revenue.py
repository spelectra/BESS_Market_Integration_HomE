"""Capacity revenue: units (per block vs. per hour) and DST block lengths."""
import pandas as pd
import pytest

from bess.capacity_revenue import afrr_revenue, fcr_revenue
from bess.data.load import _block_hours


def test_fcr_is_price_per_block_times_mw():
    blocks = pd.DataFrame({"price": [10.0, 20.0], "block_hours": [4.0, 4.0]})
    assert fcr_revenue(blocks, p_max_mw=2.0) == pytest.approx(60.0)


def test_afrr_is_hourly_price_times_block_hours_times_mw():
    # POS 1 (EUR/MW)/h for a 4-h block + NEG 2 (EUR/MW)/h for a 5-h (DST) block, 1 MW each
    blocks = pd.DataFrame({"price": [1.0, 2.0], "block_hours": [4.0, 5.0]})
    assert afrr_revenue(blocks, p_max_mw=1.0) == pytest.approx(14.0)


@pytest.mark.parametrize(
    ("local_day", "expected_hours"),
    [("2025-10-15", 4.0), ("2025-10-26", 5.0), ("2025-03-30", 3.0)],  # normal, clocks back, clocks forward
)
def test_first_block_length_on_dst_days(local_day, expected_hours):
    start_utc = pd.Series([pd.Timestamp(local_day, tz="Europe/Berlin").tz_convert("UTC")])
    assert _block_hours(start_utc).iloc[0] == pytest.approx(expected_hours)
