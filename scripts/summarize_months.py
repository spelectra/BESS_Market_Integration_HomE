from pathlib import Path
import pandas as pd

files = sorted(Path("data/processed").glob("revenue_2026-*.csv"))
all_months = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
subset=all_months[all_months["power_mw"] == 0.8]
print(subset.groupby(["market", "power_mw"])["revenue_eur"].agg(["mean", "min", "max"]))
