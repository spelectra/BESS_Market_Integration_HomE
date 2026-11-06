# BESS_Market_Integration_HomE
Comparison of financial impact of Intraday vs. Day-Ahead vs. ancillary services markets vs. automatic Frequency Restoration Reserve

Things to change to run as a new user: create .env and add your personal entsoe api key ("ENTSOE_API_KEY=your-key-here")

## Revenue simulation: what happens

1. **Fetch** raw data into `data/raw/` (one script per source, all with `--start` / `--end`):
   - `src/fetch_entsoe.py`: day-ahead prices (ENTSO-E)
   - `src/fetch_netztransparenz.py`: ID-AEP (netztransparenz)
   - `src/fetch_regelleistung.py`: FCR and aFRR capacity prices (regelleistung.net)
2. **Simulate** with `scripts/run_simulation.py --start YYYY-MM-DD --end YYYY-MM-DD`:
   - loads the raw files for the period (fails if one is missing; it does not fetch)
   - **Day-ahead and ID-AEP:** one LP per market and power level that maximizes arbitrage revenue
     (buy low, sell high) subject to the battery constraints below
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

### LP check: simultaneous charging and discharging
With negative prices, a pure LP can charge and discharge in the same step to "burn" energy through
the efficiency losses and get paid for consuming it, which is physically impossible. v1 keeps the LP
(no binary variables) and reports the number of steps with both charge > 0 and discharge > 0.
If that number is significant, switch to a MILP with a binary charge/discharge variable.

### Not modelled
- Grid fees, taxes, levies, trading and balancing costs
- Grid connection limits and shared use with the charging park
- aFRR energy activation revenue and SoC impact of FCR/aFRR activations
- Availability / downtime, rent for the storage

### Outputs
- Revenue per month per market and power level (EUR)
- Equivalent full cycles per day (discharged energy / E_max) as a plausibility check
