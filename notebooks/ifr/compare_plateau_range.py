import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.mt5_connector import MT5Connector

def compare_plateau_range():
    conn = MT5Connector()
    if not conn.connect(): return
    
    symbol = "DI1$"
    # Período do plateau identificado: 2021-10-13 11:15:00 a 13:30:00
    date_from = datetime(2021, 10, 13, 11, 0, tzinfo=timezone.utc)
    date_to = datetime(2021, 10, 13, 14, 0, tzinfo=timezone.utc)
    
    print(f"\n--- COMPARATIVO: {symbol} em {date_from.date()} ---")
    
    # 1. Carregar do Parquet Local
    parquet_path = "data/storage/DI1$_15.parquet"
    if os.path.exists(parquet_path):
        df_local = pd.read_parquet(parquet_path)
        df_local['time'] = pd.to_datetime(df_local['time'])
        # Ajustar timezone se necessário
        if df_local['time'].dt.tz is None:
            df_local['time'] = df_local['time'].dt.tz_localize('UTC')
        
        mask = (df_local['time'] >= date_from) & (df_local['time'] <= date_to)
        print("\n[DADOS NO PARQUET LOCAL]:")
        vol_col = 'tick_volume' if 'tick_volume' in df_local.columns else 'volume'
        print(df_local[mask][['time', 'close', vol_col]])
    
    # 2. Baixar direto do MT5 (Dados Brutos)
    print("\n[BAIXANDO DIRETO DO MT5...]")
    # copy_rates_range usa naive datetimes para BRT ou UTC dependendo do servidor, 
    # mas o conector trata.
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, date_from, date_to)
    if rates is not None:
        df_mt5 = pd.DataFrame(rates)
        df_mt5['time'] = pd.to_datetime(df_mt5['time'], unit='s', utc=True)
        print("\n[DADOS BRUTOS MT5]:")
        print(df_mt5[['time', 'close', 'tick_volume']])
    else:
        print("Falha ao baixar dados do MT5 para esse range.")
        
    conn.disconnect()

if __name__ == "__main__":
    compare_plateau_range()
