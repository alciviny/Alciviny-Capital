import pandas as pd
import numpy as np
import polars as pl
import os
import sys
import matplotlib.pyplot as plt

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, calculate_rsi_200, print_research_header
from src.core.config import IFR_PERIOD

def analyze_robustness(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Cálculo IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    df['ifr_slope'] = df['ifr_200'] - df['ifr_200'].shift(5) # Slope de 5 barras
    
    # --- ABORDAGENS ---
    
    # A. Simple 50 (Baseline)
    df['regime_simple'] = np.where(df['ifr_200'] > 50, 1, -1)
    
    # B. Hysteresis (48/52) - Números Mágicos do Usuário
    df['regime_hyster'] = 0
    curr = 0
    modes = []
    for v in df['ifr_200']:
        if v > 52: curr = 1
        elif v < 48: curr = -1
        modes.append(curr)
    df['regime_hyster'] = modes
    
    # C. Slope Confirmation (Trend must have momentum)
    df['regime_slope'] = np.where((df['ifr_200'] > 50) & (df['ifr_slope'] > 0), 1, 
                         np.where((df['ifr_200'] < 50) & (df['ifr_slope'] < 0), -1, 0))
    # Preencher os zeros com o último estado para manter o regime
    df['regime_slope'] = df['regime_slope'].replace(0, np.nan).ffill()

    # --- MÉTRICAS DE ROBUSTEZ ---
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    for name, col in [('Simple 50', 'regime_simple'), 
                      ('Hysteresis (48/52)', 'regime_hyster'), 
                      ('Confirmed Slope', 'regime_slope')]:
        
        # Filtro de trades: apenas quando o regime muda (sinal de entrada)
        df['change'] = df[col] != df[col].shift(1)
        changes = df[df['change'] == True]
        
        # Performance do regime mantido
        exp_bull = df[df[col] == 1]['fwd_ret'].mean()
        exp_bear = df[df[col] == -1]['fwd_ret'].mean()
        
        # Estabilidade: Qual a duração média de um regime?
        durations = []
        count = 0
        last_v = None
        for v in df[col]:
            if v == last_v: count += 1
            else:
                if last_v is not None: durations.append(count)
                count = 1
                last_v = v
        avg_duration = np.mean(durations) if durations else 0

        results.append({
            'Método': name,
            'Ret Bull%': exp_bull,
            'Ret Bear%': exp_bear,
            'Trocas/Ano': len(changes) / (len(df)/100), # Normalizado
            'Duração Média (Bars)': avg_duration
        })
        
    return results, symbol

def run_robust_study():
    print_research_header("ESTUDO DE ROBUSTEZ: FILTROS PARA O DIVISOR 50 (48/52)")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_robustness(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_robust_study()
