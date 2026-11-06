# BESS_Market_Integration_HomE
Comparison of financial impact of Intraday vs. Day-Ahead vs. ancillary services markets vs. automatic Frequency Restoration Reserve

## Setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt` (installs the `bess` package from `src/` in editable mode)
3. Copy `.env.example` to `.env` and add your ENTSO-E key and netztransparenz client credentials
4. `pytest` to check that everything works

## Project layout
- `src/bess/`: importable library code (fetching, loading, battery model, revenue calculation)
- `scripts/`: thin command-line entry points that call `bess`
- `tests/`: hand-checkable unit tests
- `data/raw/`, `data/processed/`: downloads and results (git-ignored)

## Revenue simulation: what happens

1. **Fetch** raw data into `data/raw/` (one script per source, all with `--start` / `--end`):
   - `scripts/fetch_entsoe.py`: day-ahead prices (ENTSO-E)
   - `scripts/fetch_netztransparenz.py`: ID-AEP (netztransparenz)
   - `scripts/fetch_regelleistung.py`: FCR and aFRR capacity prices (regelleistung.net)
2. **Simulate** with `scripts/run_simulation.py --start YYYY-MM-DD --end YYYY-MM-DD`:
   - loads the raw files for the period (fails if one is missing; it does not fetch)
   - **Day-ahead and ID-AEP:** one optimization (MILP) per market and power level that maximizes
     arbitrage revenue (buy low, sell high) subject to the battery constraints below
   - **FCR and aFRR:** simple capacity calculation, revenue = capacity price × offered MW
   - writes a table of revenue per market × power level to `data/processed/`

## LP assumptions (v1, high-level)

### Purpose
- Theoretical maximum revenue (perfect foresight) per market and power level.
- Results are upper bounds, not realistic trading results.

### Battery
- Energy capacity E_max: 3.0 MWh (usable capacity)
- Power P_max: 1 / 2 / 3 MW (same for charge and discharge)
- One-way efficiency η: 0.93 (round trip ≈ 0.86), constant
- SoC window: 0–100 % of E_max (no operational buffer)
- Start SoC = end SoC = 50 % of E_max
- No degradation cost, no cycle limit, no auxiliary consumption
- No minimum run time or ramp limits; full power available in every step

### Time
- Horizon: one calendar month per LP run, historic data
- Resolution: 15 min (dt = 0.25 h); data from 2025-10-01 onwards
- Timestamps in UTC; DST days have 92 / 100 steps

### Prices and markets
- Day-ahead: ENTSO-E DE-LU, SDAC (sequence 1), EUR/MWh
- Intraday: netztransparenz ID-AEP, EUR/MWh
- FCR: regelleistung.net capacity price, EUR/MW per 4-h block. The product is symmetric
  (`NEGPOS`), so one offered MW covers both directions.
- aFRR: regelleistung.net capacity price in (EUR/MW)/h, multiplied by 4 h to get EUR/MW per block.
  POS and NEG are separate products; the ideal case offers P_max in **both** directions.
- Perfect foresight: all prices known in advance
- Price taker: battery does not affect market prices
- Each market optimized separately; revenues are NOT additive

### Simultaneous charging and discharging (LP vs. MILP)
With negative prices, a pure LP can charge and discharge in the same step to "burn" energy through
the efficiency losses and get paid for consuming it, which is physically impossible. In October 2025
the pure LP did this in 66–129 quarter-hours (all at prices ≤ 0), so the model uses a **MILP** with one
binary per step (charge *or* discharge). Revenue impact is small (≤ 25 EUR/month) and the MILP solves
in ~1 s with SciPy/HiGHS. `solve_arbitrage(..., allow_simultaneous=True)` restores the pure LP; the
output still reports `simultaneous_steps` as a check.

### Capacity prices
- FCR is pay-as-cleared: revenue uses the German settlement price.
- aFRR capacity is pay-as-bid: revenue uses the German **average** accepted price. The marginal
  (highest accepted) price would be the stricter upper bound.
- The 00–04 block is 3 h / 5 h long on DST change days; aFRR revenue uses the actual block length.

### Not modelled
- Grid fees, taxes, levies, trading and balancing costs
- Grid connection limits and shared use with the charging park
- aFRR energy activation revenue and SoC impact of FCR/aFRR activations
- Availability / downtime, rent for the storage

### Outputs
- Revenue per month per market and power level (EUR)
- Equivalent full cycles per day (discharged energy / E_max) as a plausibility check
