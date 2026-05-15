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

def analyze_setup_multi_tf(symbol, timeframe):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return []
    
    df = pl.read_parquet(path).to_pandas()
    df = df.sort_values('time')
    
    # 1. Indicadores
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    df['ifr_50'] = calculate_rsi_wilder(df['close'], period=50)
    
    # 2. Regime
    regimes = []
    curr = 0
    for v in df['ifr_200']:
        if v > 52: curr = 1
        elif v < 48: curr = -1
        regimes.append(curr)
    df['regime'] = regimes
    
    # 3. Zona 200
    df['in_zone'] = (df['ifr_200'] >= 48) & (df['ifr_200'] <= 52)
    
    # 4. Gatilhos
    df['sig_buy'] = (df['regime'] == 1) & (df['in_zone']) & (df['ifr_50'] > 45) & (df['ifr_50'].shift(1) <= 45)
    df['sig_sell'] = (df['regime'] == -1) & (df['in_zone']) & (df['ifr_50'] < 55) & (df['ifr_50'].shift(1) >= 55)
    
    # Retornos (Ajustamos o horizonte conforme o TF)
    h = 20 if timeframe == "15" else (60 if timeframe == "5" else 5)
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    
    # Stats Compra
    b_data = df[df['sig_buy'] == True]
    if len(b_data) > 0:
        results.append({
            'Ativo': symbol, 'TF': timeframe, 'Lado': 'Compra',
            'Ret Médio%': b_data['fwd_ret'].mean(),
            'WR%': (b_data['fwd_ret'] > 0).mean() * 100, 'N': len(b_data)
        })
        
    # Stats Venda
    s_data = df[df['sig_sell'] == True]
    if len(s_data) > 0:
        results.append({
            'Ativo': symbol, 'TF': timeframe, 'Lado': 'Venda',
            'Ret Médio%': -s_data['fwd_ret'].mean(),
            'WR%': (s_data['fwd_ret'] < 0).mean() * 100, 'N': len(s_data)
        })
        
    return results

def run_study():
    print_research_header("AUDITORIA MULTI-TIMEFRAME: SETUP REVERSÃO NA TENDÊNCIA")
    
    all_results = []
    for asset in ["WIN$", "WDO$", "DI1$"]:
        for tf in ["5", "15", "60"]:
            res = analyze_setup_multi_tf(asset, tf)
            all_results.extend(res)
            
    final_df = pd.DataFrame(all_results)
    # Pivotar para facilitar leitura
    for asset in ["WIN$", "WDO$", "DI1$"]:
        print(f"\n[ATIVO: {asset}]")
        asset_df = final_df[final_df['Ativo'] == asset].drop(columns=['Ativo'])
        print(asset_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
