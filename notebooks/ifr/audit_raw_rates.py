import MetaTrader5 as mt5
import pandas as pd
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.mt5_connector import MT5Connector

def audit_raw_rates(symbol="DI1$", timeframe=15):
    conn = MT5Connector()
    if not conn.connect(): return
    
    print(f"\n--- DADOS BRUTOS DIRETOS DO MT5: {symbol} ---")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 10)
    if rates is not None:
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        print(df[['time', 'open', 'high', 'low', 'close', 'tick_volume']])
    else:
        print("Falha ao obter rates.")
        
    conn.disconnect()

if __name__ == "__main__":
    audit_raw_rates("DI1$")
    audit_raw_rates("WDO$")
