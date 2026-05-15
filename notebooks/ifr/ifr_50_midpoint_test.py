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

def analyze_ifr50_midpoint(symbol, timeframe="15"):
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
    
    # 4. Sinal de Gatilho: IFR 50 rompendo a linha 50
    df['sig_50_cross_50'] = (df['regime'] == 1) & (df['in_zone']) & (df['ifr_50'] > 50) & (df['ifr_50'].shift(1) <= 50)
    
    # Retornos futuros
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    
    # Performance
    data = df[df['sig_50_cross_50'] == True]
    if len(data) > 0:
        results.append({
            'Gatilho': 'IFR 50 cruza Linha 50',
            'Ret Médio%': data['fwd_ret'].mean(),
            'WR%': (data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(data)
        })
    else:
        results.append({'Gatilho': 'Nenhum sinal encontrado', 'Ret Médio%': 0, 'WR%': 0, 'Amostras': 0})

    return results, symbol

def run_study():
    print_research_header("AUDITORIA FINAL: GATILHO IFR 50 CRUZANDO 50 (DENTRO DA ZONA 200)")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_ifr50_midpoint(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
