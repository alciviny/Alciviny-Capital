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

def analyze_zscore_vs_fixed(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Cálculo IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # --- MÉTODO 1: FIXED 48/52 ---
    df['reg_fixed'] = 0
    curr = 0
    modes = []
    for v in df['ifr_200']:
        if v > 52: curr = 1
        elif v < 48: curr = -1
        modes.append(curr)
    df['reg_fixed'] = modes
    
    # --- MÉTODO 2: ADAPTIVE Z-SCORE BUFFER ---
    # Usamos uma janela longa (500 bars) para o desvio padrão do IFR
    # para evitar que ele fique "nervoso"
    df['ifr_std'] = df['ifr_200'].rolling(500).std()
    # Coeficiente 0.5 de desvio padrão (equivalente a uma zona de ~2-3 pontos no IFR padrão)
    df['upper_adapt'] = 50 + (0.5 * df['ifr_std'])
    df['lower_adapt'] = 50 - (0.5 * df['ifr_std'])
    
    df['reg_adapt'] = 0
    curr = 0
    modes_adapt = []
    for v, up, lo in zip(df['ifr_200'], df['upper_adapt'], df['lower_adapt']):
        if np.isnan(up) or np.isnan(lo):
            modes_adapt.append(0)
            continue
        if v > up: curr = 1
        elif v < lo: curr = -1
        modes_adapt.append(curr)
    df['reg_adapt'] = modes_adapt

    # --- MÉTRICAS ---
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    for name, col in [('Fixed 48/52', 'reg_fixed'), ('Adaptive Z-Buffer', 'reg_adapt')]:
        df['change'] = df[col] != df[col].shift(1)
        
        exp_bull = df[df[col] == 1]['fwd_ret'].mean()
        exp_bear = df[df[col] == -1]['fwd_ret'].mean()
        
        durations = []
        count = 0
        last_v = None
        for v in df[col]:
            if v == last_v: count += 1
            else:
                if last_v is not None: durations.append(count)
                count = 1
                last_v = v
        
        results.append({
            'Método': name,
            'Ret Bull%': exp_bull,
            'Ret Bear%': exp_bear,
            'Trocas/Ano': (df['change'].sum() / (len(df)/100)),
            'Estabilidade (Bars)': np.mean(durations) if durations else 0
        })
        
    return results, symbol

def run_study():
    print_research_header("COMPARATIVO: FIXED 48/52 VS ADAPTIVE Z-BUFFER")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_zscore_vs_fixed(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
