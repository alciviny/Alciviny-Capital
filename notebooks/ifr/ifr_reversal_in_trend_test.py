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

def analyze_ifr50_reversal_timing(symbol, timeframe="15"):
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
    
    # 4. Gatilhos de Reversão no IFR 50
    # Compra: No regime Bull e Zona de Valor, IFR 50 volta de baixo para cima do 45
    df['sig_reversal_buy'] = (df['regime'] == 1) & (df['in_zone']) & (df['ifr_50'] > 45) & (df['ifr_50'].shift(1) <= 45)
    
    # Venda: No regime Bear e Zona de Valor, IFR 50 volta de cima para baixo do 55
    df['sig_reversal_sell'] = (df['regime'] == -1) & (df['in_zone']) & (df['ifr_50'] < 55) & (df['ifr_50'].shift(1) >= 55)
    
    # Retornos futuros
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    
    # Performance Compra
    buy_data = df[df['sig_reversal_buy'] == True]
    if len(buy_data) > 0:
        results.append({
            'Lado': 'COMPRA (Volta do 45)',
            'Ret Médio%': buy_data['fwd_ret'].mean(),
            'WR%': (buy_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(buy_data)
        })
        
    # Performance Venda
    sell_data = df[df['sig_reversal_sell'] == True]
    if len(sell_data) > 0:
        results.append({
            'Lado': 'VENDA (Volta do 55)',
            'Ret Médio%': -sell_data['fwd_ret'].mean(),
            'WR%': (sell_data['fwd_ret'] < 0).mean() * 100,
            'Amostras': len(sell_data)
        })

    return results, symbol

def run_study():
    print_research_header("AUDITORIA: REVERSÃO IFR 50 (45/55) DENTRO DA ZONA IFR 200")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_ifr50_reversal_timing(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
