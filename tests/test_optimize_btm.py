"""Hand-checkable BTM cases: peak shaving and the no-feed-in rule."""
import pandas as pd
import pytest

from bess.battery import BatteryParams
from bess.optimize_btm import GridTariff, site_cost_eur, solve_btm


def _series(values: list[float]) -> pd.Series:
    index = pd.date_range("2026-01-01", periods=len(values), freq="15min", tz="UTC")
    return pd.Series(values, index=index, dtype=float)


def test_battery_shaves_a_single_spike_by_its_power():
    load = _series([0.5] * 4 + [2.0] + [0.5] * 3)
    spot = _series([50.0] * 8)
    tariff = GridTariff(demand_charge_eur_mw_a=1e9)  # make the peak dominate everything else
    result = solve_btm(spot, load, BatteryParams(p_max_mw=1.0), tariff)
    assert result["grid_mw"].max() == pytest.approx(1.0, abs=1e-6)  # 2.0 MW spike - 1.0 MW discharge
    assert result["grid_mw"].min() >= -1e-6  # never feeds into the grid


def test_site_cost_splits_energy_and_pro_rated_demand_charge():
    grid = _series([1.0] * 4)  # 1 MWh over one hour
    cost = site_cost_eur(grid, _series([100.0] * 4), GridTariff(demand_charge_eur_mw_a=8760.0, energy_fee_eur_mwh=50.0))
    assert cost["energy_eur"] == pytest.approx(150.0)  # 1 MWh * (100 + 50)
    assert cost["demand_eur"] == pytest.approx(1.0)  # 8760 EUR/MW·a * 1 h / 8760 h * 1 MW


def test_mixed_ftm_only_equals_plain_arbitrage():
    from bess.optimize_arbitrage import solve_arbitrage
    from bess.optimize_mixed import solve_mixed

    spot = _series([10.0, 90.0, 20.0, 120.0, 30.0, 80.0, 15.0, 100.0])
    load = _series([0.3] * 8)
    ftm = pd.Series(False, index=spot.index)
    result = solve_mixed(spot, load, ftm, BatteryParams(), GridTariff())
    expected = solve_arbitrage(spot, BatteryParams())["revenue_eur"].sum()
    assert (0.25 * spot * result["output_mw"]).sum() == pytest.approx(expected, rel=1e-6)
    assert result["grid_mw"].to_numpy() == pytest.approx(load.to_numpy())  # FTM: the site draws its load unchanged
