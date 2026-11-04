import os
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import pandas as pd

# Load the ENTSOE_API_KEY from the .env file
load_dotenv()  # reads .env from the project root
api_key = os.getenv("ENTSOE_API_KEY")
if not api_key:
    raise RuntimeError(
        "ENTSOE_API_KEY is not set. Copy .env.example to .env and add your own ENTSO-E key."
    )
client = EntsoePandasClient(api_key)

#Assign path to save




#Load Day Ahead Prices for Germany from 2017-12-01 to 2018-01-01

def fetch_day_ahead_prices(start_date.tz_convert("UTC"), end_date.tz_convert("UTC"), country_code):
    start = pd.Timestamp(start_date, tz='UTC')
    end = pd.Timestamp(end_date, tz='UTC')
    country_code = country_code 
    country_code_from = country_code 
    country_code_to = country_code 

    #ignore this for now
    type_marketagreement_type = 'A01'
    contract_marketagreement_type = "A01"
    process_type = 'A51'

    # Day-ahead prices switched from hourly to 15-min resolution on 2025-10-01 (SDAC go-live)
    DA_15MIN_START = pd.Timestamp("2025-10-01", tz="Europe/Brussels")

    if start < DA_15MIN_START:
        raise ValueError(
            f"Start date {start.date()} is before {DA_15MIN_START.date()}: "
            "day-ahead prices are hourly before this date, not 15-min."
        )

    # methods that return Pandas Series
    dataframe = client.query_day_ahead_prices(country_code, start=start, end=end)
    # client.query_aggregated_bids(country_code, start=start, end=end, process_type)
    # client.query_net_position(country_code, start=start, end=end, dayahead=True)
    # client.query_crossborder_flows(country_code_from, country_code_to, start=start, end=end)
    # client.query_scheduled_exchanges(country_code_from, country_code_to, start=start, end=end, dayahead=False)
    # client.query_net_transfer_capacity_dayahead(country_code_from, country_code_to, start=start, end=end)
    # client.query_net_transfer_capacity_weekahead(country_code_from, country_code_to, start=start, end=end)
    # client.query_net_transfer_capacity_monthahead(country_code_from, country_code_to, start=start, end=end)
    # client.query_net_transfer_capacity_yearahead(country_code_from, country_code_to, start=start, end=end)
    # client.query_intraday_offered_capacity(country_code_from, country_code_to, start=start, end=end, implicit=True)
    # client.query_offered_capacity(country_code_from, country_code_to, contract_marketagreement_type, start=start, end=end, implicit=True)
    # client.query_aggregate_water_reservoirs_and_hydro_storage(country_code, start=start, end=end)

    # methods that return Pandas DataFrames
    # client.query_load(country_code, start=start, end=end)
    # client.query_load_forecast(country_code, start=start, end=end)
    # client.query_load_and_forecast(country_code, start=start, end=end)
    # client.query_generation_forecast(country_code, start=start, end=end)
    # client.query_wind_and_solar_forecast(country_code, start=start, end=end, psr_type=None)
    # client.query_intraday_wind_and_solar_forecast(country_code, start=start, end=end, psr_type=None)
    # client.query_generation(country_code, start=start, end=end, psr_type=None)
    # client.query_generation_per_plant(country_code, start=start, end=end, psr_type=None, include_eic=False)
    # client.query_installed_generation_capacity(country_code, start=start, end=end, psr_type=None)
    # client.query_installed_generation_capacity_per_unit(country_code, start=start, end=end, psr_type=None)
    # client.query_activated_balancing_energy_prices(country_code, start=start, end=end, process_type='A16', psr_type=None, business_type=None, standard_market_product=None, original_market_product=None)
    # client.query_activated_balancing_energy(country_code, start=start, end=end, business_type, psr_type=None)
    # client.query_imbalance_prices(country_code, start=start, end=end, psr_type=None)
    # client.query_imbalance_volumes(country_code, start=start, end=end, psr_type=None)
    # client.query_contracted_reserve_prices(country_code, type_marketagreement_type, start=start, end=end, psr_type=None)
    # client.query_contracted_reserve_amount(country_code, type_marketagreement_type, start=start, end=end, psr_type=None)
    # client.query_unavailability_of_generation_units(country_code, start=start, end=end, docstatus=None, periodstartupdate=None, periodendupdate=None)
    # client.query_unavailability_of_production_units(country_code, start, end, docstatus=None, periodstartupdate=None, periodendupdate=None)
    # client.query_unavailability_transmission(country_code_from, country_code_to, start=start, end=end, docstatus=None, periodstartupdate=None, periodendupdate=None)
    # client.query_withdrawn_unavailability_of_generation_units(country_code, start, end)
    # client.query_unavailability_of_offshore_grid(area_code, start, end)
    # client.query_physical_crossborder_allborders(country_code, start, end, export=True)
    # client.query_import(country_code, start, end)
    # client.query_generation_import(country_code, start, end)
    # client.query_procured_balancing_capacity(country_code, process_type, start=start, end=end, type_marketagreement_type=None)
return dataframe