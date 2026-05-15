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

def analyze_pullback_to_zone(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Cálculo IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # 2. Definir Regime (Histerese 48/52)
    regimes = []
    curr = 0
    for v in df['ifr_200']:
        if v > 52: curr = 1
        elif v < 48: curr = -1
        regimes.append(curr)
    df['regime'] = regimes
    
    # 3. Identificar Sinais de Pullback na Zona (48/52)
    # Compra: Tendência de Alta (Bull) mas IFR retornou para 48 (ou próximo)
    # Venda: Tendência de Baixa (Bear) mas IFR retornou para 52
    
    df['signal_buy'] = (df['regime'] == 1) & (df['ifr_200'] <= 48.5) & (df['ifr_200'] >= 47.5)
    df['signal_sell'] = (df['regime'] == -1) & (df['ifr_200'] >= 51.5) & (df['ifr_200'] <= 52.5)
    
    # Retornos futuros
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    # Comparar: Entrada no Rompimento (52) vs Entrada no Pullback (48)
    # Entrada no Rompimento (primeira vez que bate 52)
    df['breakout_buy'] = (df['ifr_200'] > 52) & (df['ifr_200'].shift(1) <= 52)
    
    results = []
    
    # Métricas para Breakout 52 (Baseline)
    brk_data = df[df['breakout_buy'] == True]
    if len(brk_data) > 0:
        results.append({
            'Setup': 'Breakout 52 (Entrada Topo)',
            'Ret Médio%': brk_data['fwd_ret'].mean(),
            'WR%': (brk_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(brk_data)
        })
        
    # Métricas para Pullback 48 (Teoria do Usuário)
    pb_data = df[df['signal_buy'] == True]
    if len(pb_data) > 0:
        results.append({
            'Setup': 'Pullback 48 (DIP na Tendência)',
            'Ret Médio%': pb_data['fwd_ret'].mean(),
            'WR%': (pb_data['fwd_ret'] > 0).mean() * 100,
            'Amostras': len(pb_data)
        })
        
    # Métricas para Venda no Pullback 52
    sell_pb_data = df[df['signal_sell'] == True]
    if len(sell_pb_data) > 0:
        results.append({
            'Setup': 'Pullback 52 (SELL na Baixa)',
            'Ret Médio%': -sell_pb_data['fwd_ret'].mean(),
            'WR%': (sell_pb_data['fwd_ret'] < 0).mean() * 100,
            'Amostras': len(sell_pb_data)
        })

    return results, symbol

def run_study():
    print_research_header("TESTE DE PULLBACK NA ZONA 48/52 (COMPRA NO 48 EM ALTA)")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        results, symbol = analyze_pullback_to_zone(asset)
        print(f"\n[ATIVO: {symbol}]")
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_study()
