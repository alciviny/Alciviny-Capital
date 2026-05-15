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

def analyze_confluence_timing(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Indicadores
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    df['ifr_14'] = calculate_rsi_wilder(df['close'], period=14)
    
    # 2. Definir Regime Macro (48/52 Histerese)
    regimes = []
    curr = 0
    for v in df['ifr_200']:
        if v > 52: curr = 1
        elif v < 48: curr = -1
        regimes.append(curr)
    df['regime'] = regimes
    
    # 3. Definir "Estar na Zona de Valor" (48/52)
    df['in_value_zone'] = (df['ifr_200'] >= 48) & (df['ifr_200'] <= 52)
    
    # 4. Sinais de Confluência (Timing)
    # Compra: No regime BULL, dentro da zona de valor, espera o IFR 14 dar momentum (> 50)
    df['signal_confluence_buy'] = (df['regime'] == 1) & (df['in_value_zone']) & (df['ifr_14'] > 50) & (df['ifr_14'].shift(1) <= 50)
    
    # Retornos futuros
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    
    # Baseline: Entrar na zona de valor sem timing (qualquer candle na zona)
    zone_data = df[(df['regime'] == 1) & (df['in_value_zone'])]
    if len(zone_data) > 0:
        results.append({
            'Estratégia': 'Entrada Cega na Zona (48/52)',
            'Ret Médio%': zone_data['fwd_ret'].mean(),
            'WR%': (zone_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(zone_data)
        })
        
    # Confluência: Entrada com Gatilho IFR 14
    conf_data = df[df['signal_confluence_buy'] == True]
    if len(conf_data) > 0:
        results.append({
            'Estratégia': 'Zona 200 + Gatilho IFR 14',
            'Ret Médio%': conf_data['fwd_ret'].mean(),
            'WR%': (conf_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(conf_data)
        })

    return results, symbol

def run_study():
    print_research_header("AUDITORIA DE TIMING: ZONA IFR 200 + GATILHO IFR 14")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_confluence_timing(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
