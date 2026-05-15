import pandas as pd
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.append(os.getcwd())

from src.data.store import DataStore

ds = DataStore()
for s in ['WIN$', 'WDO$', 'DI1$']:
    try:
        df = ds.load(s, 15)
        if df is not None:
            df.set_index('time', inplace=True)
            print(f"{s}: {df.index.min()} to {df.index.max()} ({len(df)} rows)")
        else:
            print(f"{s}: Not found")
    except Exception as e:
        print(f"Error loading {s}: {e}")
