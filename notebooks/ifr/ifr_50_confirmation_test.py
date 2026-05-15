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
from src.indicators.oscillators import calculate_rsi_wilder

def analyze_ifr50_confirmation(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Indicadores
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    df['ifr_50'] = calculate_rsi_wilder(df['close'], period=50)
    
    # 2. Regime Macro (48/52 Histerese)
    regimes = []
    curr = 0
    for v in df['ifr_200']:
        if v > 52: curr = 1
        elif v < 48: curr = -1
        regimes.append(curr)
    df['regime'] = regimes
    
    # 3. Zona de Valor do IFR 200
    df['in_zone'] = (df['ifr_200'] >= 48) & (df['ifr_200'] <= 52)
    
    # 4. Sinais de Gatilho (Timer IFR 50)
    # Hipótese A: IFR 50 cruza o 52 para cima (Confirmação de força forte)
    df['sig_50_cross_52'] = (df['regime'] == 1) & (df['in_zone']) & (df['ifr_50'] > 52) & (df['ifr_50'].shift(1) <= 52)
    
    # Hipótese B: IFR 50 cruza o 48 para cima (Antecipação na base da zona)
    df['sig_50_cross_48'] = (df['regime'] == 1) & (df['in_zone']) & (df['ifr_50'] > 48) & (df['ifr_50'].shift(1) <= 48)
    
    # Retornos futuros
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    
    # Performance Hipótese A
    a_data = df[df['sig_50_cross_52'] == True]
    if len(a_data) > 0:
        results.append({
            'Gatilho (Timer IFR 50)': 'Cruzamento do 52 (Alta)',
            'Ret Médio%': a_data['fwd_ret'].mean(),
            'WR%': (a_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(a_data)
        })
        
    # Performance Hipótese B
    b_data = df[df['sig_50_cross_48'] == True]
    if len(b_data) > 0:
        results.append({
            'Gatilho (Timer IFR 50)': 'Cruzamento do 48 (Fundo)',
            'Ret Médio%': b_data['fwd_ret'].mean(),
            'WR%': (b_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(b_data)
        })

    return results, symbol

def run_study():
    print_research_header("AUDITORIA DE GATILHO: IFR 50 DENTRO DA ZONA IFR 200")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_ifr50_confirmation(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
