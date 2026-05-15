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

# Tentar baixar desde 2010
date_from = datetime(2010, 1, 1)
date_to = datetime.now()

for symbol in ['WIN$', 'WDO$', 'DI1$']:
    print(f"Downloading deep history for {symbol}...")
    new_data = connector.get_historical_data_range(symbol, 15, date_from, date_to)
    if new_data is not None:
        print(f"  Downloaded {len(new_data)} rows.")
        # Salvar por cima (ou unificar)
        if new_data['time'].dt.tz is None:
            new_data['time'] = new_data['time'].dt.tz_localize('UTC')
        ds.save(new_data, symbol, 15)
    else:
        print("  Failed to download.")

connector.disconnect()
