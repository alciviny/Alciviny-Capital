import sys
import os
import pandas as pd
from datetime import datetime, timezone
import MetaTrader5 as mt5

sys.path.append(os.getcwd())
from src.data.store import DataStore
from src.data.mt5_connector import MT5Connector

ds = DataStore()
connector = MT5Connector()
connector.connect()

for symbol in ['WIN$', 'WDO$', 'DI1$']:
    print(f"Updating {symbol}...")
    last_ts = ds.get_last_timestamp(symbol, 15)
    if last_ts is not None:
        # Convert to naive for copy_rates_range if needed, or keep aware
        # copy_rates_range takes datetime objects.
        # If last_ts is aware, we should keep it or convert both.
        date_from = last_ts.to_pydatetime()
        date_to = datetime.now(timezone.utc).replace(tzinfo=None)
        if date_from.tzinfo is not None:
            date_from = date_from.replace(tzinfo=None)
            
        print(f"  Fetching from {date_from} to {date_to}")
        new_data = connector.get_historical_data_range(symbol, 15, date_from, date_to)
        
        if new_data is not None and len(new_data) > 0:
            print(f"  Downloaded {len(new_data)} rows.")
            existing = ds.load(symbol, 15)
            # Ensure both are tz-aware or both naive
            if existing['time'].dt.tz is None:
                existing['time'] = existing['time'].dt.tz_localize('UTC')
            if new_data['time'].dt.tz is None:
                new_data['time'] = new_data['time'].dt.tz_localize('UTC')
                
            combined = pd.concat([existing, new_data]).drop_duplicates(subset='time').sort_values('time')
            ds.save(combined, symbol, 15)
            print(f"  Saved {len(combined)} rows.")
        else:
            print("  No new data.")

connector.disconnect()
