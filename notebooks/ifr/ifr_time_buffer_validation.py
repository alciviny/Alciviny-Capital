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

from src.research.utils import get_data_path, calculate_rsi_200, print_research_header

def analyze_time_buffer(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Cálculo IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # --- MÉTRICAS ---
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    
    # Testar diferentes Time Buffers (N candles consecutivos)
    for buffer_n in [1, 3, 5]:
        # Logica baseada no 48/52 do usuário
        # 1. Identificar sinais brutos
        df['raw_bull'] = (df['ifr_200'] > 52).astype(int)
        df['raw_bear'] = (df['ifr_200'] < 48).astype(int)
        
        # 2. Aplicar Time Buffer (Mínimo N candles consecutivos)
        # Usamos rolling sum para validar a persistência
        df['bull_persistent'] = df['raw_bull'].rolling(buffer_n).sum() == buffer_n
        df['bear_persistent'] = df['raw_bear'].rolling(buffer_n).sum() == buffer_n
        
        # 3. Mapear Regime com Histerese e Persistência
        regimes = []
        curr = 0
        for b, r in zip(df['bull_persistent'], df['bear_persistent']):
            if b: curr = 1
            elif r: curr = -1
            regimes.append(curr)
        
        col_name = f'regime_b{buffer_n}'
        df[col_name] = regimes
        
        # Calcular performance
        exp_bull = df[df[col_name] == 1]['fwd_ret'].mean()
        exp_bear = df[df[col_name] == -1]['fwd_ret'].mean()
        
        # Calcular trocas de sinal
        df['change'] = df[col_name] != df[col_name].shift(1)
        
        results.append({
            'Buffer (Candles)': buffer_n,
            'Ret Bull%': exp_bull,
            'Ret Bear%': exp_bear,
            'Trocas/Ano': (df['change'].sum() / (len(df)/100)),
            'Samples': df[df[col_name] != 0].shape[0]
        })
        
    return results, symbol

def run_study():
    print_research_header("VALIDAÇÃO DE TIME-BUFFER: PERSISTÊNCIA NO 48/52")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_time_buffer(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
