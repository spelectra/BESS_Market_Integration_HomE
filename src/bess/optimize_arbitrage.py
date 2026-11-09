"""Perfect-foresight arbitrage MILP/LP: buy low, sell high within the battery's power, energy and SoC limits."""
import cvxpy as cp
import pandas as pd

from bess.battery import BatteryParams

DT_H = 0.25  # 15-min steps


def solve_arbitrage(
    prices: pd.Series, battery: BatteryParams, dt_h: float = DT_H, allow_simultaneous: bool = False
) -> pd.DataFrame:
    """Maximize arbitrage revenue over the whole price series (perfect foresight).

    Power is measured at the grid connection: charging `c` MW stores eta * c, discharging `d` MW
    takes d / eta out of the battery. Returns one row per step with charge, discharge, SoC and revenue.

    allow_simultaneous=False (default) adds one binary per step so the battery either charges or
    discharges (MILP). With True it is a pure LP, which at negative prices charges and discharges at
    once to burn energy through the losses — physically impossible, but useful as an experiment.
    """
    n = len(prices)
    price = prices.to_numpy()
    charge = cp.Variable(n, nonneg=True)  # MW drawn from the grid
    discharge = cp.Variable(n, nonneg=True)  # MW fed into the grid
    soc = cp.Variable(n + 1)  # MWh at the step boundaries: soc[0] = start, soc[n] = end

    constraints = [
        charge <= battery.p_max_mw,
        discharge <= battery.p_max_mw,
        soc[1:] == soc[:-1] + dt_h * (battery.eta * charge - discharge / battery.eta),
        soc >= battery.soc_min_mwh,
        soc <= battery.soc_max_mwh,
        soc[0] == battery.soc_start_mwh,
        soc[n] == battery.soc_start_mwh,  # end = start, otherwise the LP sells the initial charge
    ]
    solver = None  # cvxpy picks its default LP solver
    if not allow_simultaneous:
        is_charging = cp.Variable(n, boolean=True)  # 1 = may charge, 0 = may discharge
        constraints += [charge <= battery.p_max_mw * is_charging, discharge <= battery.p_max_mw * (1 - is_charging)]
        solver = cp.SCIPY  # SciPy's HiGHS handles mixed-integer problems; month-long MILP solves in ~1 s

    revenue = dt_h * price @ (discharge - charge)  # EUR = EUR/MWh * MW * h
    problem = cp.Problem(cp.Maximize(revenue), constraints)
    problem.solve(solver=solver)
    if problem.status != cp.OPTIMAL:
        raise RuntimeError(f"LP not solved to optimality: status={problem.status}")

    return pd.DataFrame(
        {
            "price_eur_mwh": price,
            "charge_mw": charge.value,
            "discharge_mw": discharge.value,
            "soc_mwh": soc.value[1:],  # SoC at the end of each step
            "revenue_eur": dt_h * price * (discharge.value - charge.value),
        },
        index=prices.index,
    )


def summarize_dispatch(dispatch: pd.DataFrame, battery: BatteryParams, dt_h: float = DT_H) -> dict[str, float]:
    """Total revenue and equivalent full cycles per day."""
    n_days = len(dispatch) * dt_h / 24
    discharged_mwh = dispatch["discharge_mw"].sum() * dt_h
    return {
        "revenue_eur": float(dispatch["revenue_eur"].sum()),
        "full_cycles_per_day": float(discharged_mwh / battery.e_max_mwh / n_days),
    }
