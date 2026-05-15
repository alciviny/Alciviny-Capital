import pandas as pd
import numpy as np
import polars as pl
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path

def audit_plateaus(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Identificar Plateaus (Preço constante por 2+ barras)
    df['price_change'] = df['close'].diff() != 0
    df['plateau_id'] = df['price_change'].cumsum()
    
    # Contar tamanho dos plateaus
    plateau_sizes = df.groupby('plateau_id').size()
    long_plateaus = plateau_sizes[plateau_sizes >= 4] # Plateaus de 1 hora ou mais
    
    print(f"\n--- AUDITORIA DE PLATEAUS: {symbol} ---")
    print(f"Total de Plateaus Longos (>= 4 barras): {len(long_plateaus)}")
    
    # 2. Verificar Volume nos Plateaus
    vol_col = 'tick_volume' if 'tick_volume' in df.columns else ('volume' if 'volume' in df.columns else None)
    
    if len(long_plateaus) > 0 and vol_col:
        df_plateaus = df[df['plateau_id'].isin(long_plateaus.index)]
        avg_vol = df_plateaus[vol_col].mean()
        zero_vol_plateaus = (df_plateaus[vol_col] == 0).sum()
        
        print(f"Volume Médio ({vol_col}) nos Plateaus: {avg_vol:.2f}")
        print(f"Barras com Volume ZERO nos Plateaus: {zero_vol_plateaus}")
        
        if zero_vol_plateaus > 0:
            print("[ALERTA] Existem barras com PREÇO mas VOLUME ZERO. Isso é lixo de processamento!")
        
        # 3. Mostrar exemplo de plateau suspeito
        suspect = long_plateaus.sort_values(ascending=False).head(1)
        if not suspect.empty:
            pid = suspect.index[0]
            print(f"\nExemplo de Maior Plateau (ID {pid}, Tamanho {suspect.values[0]}):")
            cols_to_show = ['time', 'close', vol_col]
            print(df[df['plateau_id'] == pid][cols_to_show].head(10))
    elif len(long_plateaus) > 0:
        print("[AVISO] Nenhuma coluna de volume encontrada para auditoria profunda.")

def main():
    for asset in ["WIN$", "WDO$", "DI1$"]:
        audit_plateaus(asset)

if __name__ == "__main__":
    main()
