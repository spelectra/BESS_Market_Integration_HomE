"""Battery parameters: the README's LP assumptions in one place, no magic numbers in the model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryParams:
    """Technical battery parameters. frozen=True: a parameter set can't be changed by accident mid-run."""

    e_max_mwh: float = 3.0  # usable energy capacity
    p_max_mw: float = 1.0  # same limit for charging and discharging
    eta: float = 0.93  # one-way efficiency, round trip = eta**2 ≈ 0.86
    soc_min_frac: float = 0.0  # SoC window as fraction of e_max
    soc_max_frac: float = 1.0
    soc_start_frac: float = 0.5  # start SoC = end SoC

    @property
    def soc_min_mwh(self) -> float:
        return self.soc_min_frac * self.e_max_mwh

    @property
    def soc_max_mwh(self) -> float:
        return self.soc_max_frac * self.e_max_mwh

    @property
    def soc_start_mwh(self) -> float:
        return self.soc_start_frac * self.e_max_mwh
