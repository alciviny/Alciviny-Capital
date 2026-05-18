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

def sanitize_dataset(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    print(f"Limpando {symbol}...")
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').drop_duplicates(subset=['time'])
    
    original_len = len(df)
    
    # 1. Remover Estagnação Extrema
    # Se o preço não muda por 4 barras consecutivas (1 hora), consideramos dado inválido/congelado
    # exceto se for em horários de baixíssima liquidez (mas aqui é 15m, deveria ter tick)
    df['is_stale'] = df['close'].diff() == 0
    df['stale_group'] = (df['is_stale'] != df['is_stale'].shift()).cumsum()
    
    # Contar tamanho dos grupos estagnados
    stale_counts = df.groupby('stale_group')['is_stale'].transform('count')
    
    # Remover se estagnado por mais de 4 barras (1 hora no 15m)
    df_clean = df[~((df['is_stale']) & (stale_counts >= 4))].copy()
    
    # 2. Salvar Versão Clean
    clean_path = path.replace(".parquet", "_CLEAN.parquet")
    df_clean.drop(columns=['diff', 'hour', 'is_stale', 'stale_group'], errors='ignore').to_parquet(clean_path)
    
    removed = original_len - len(df_clean)
    print(f"Sucesso: {removed} barras removidas ({ (removed/original_len)*100:.2f}%).")
    print(f"Arquivo salvo em: {clean_path}")
    
    return clean_path

def main():
    for asset in ["WIN$", "WDO$", "DI1$"]:
        sanitize_dataset(asset)

if __name__ == "__main__":
    main()
