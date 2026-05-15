import sys
import os
sys.path.append(os.getcwd())
from src.data.manager import DataManager
from src.data.mt5_connector import MT5Connector
from src.data.store import DataStore
from src.processing.processor import DataProcessor

dm = DataManager()
for s in ['WIN$', 'WDO$', 'DI1$']:
    print(f"Syncing {s}...")
    dm.update_and_fetch(s, 15)
print("Sync complete.")
