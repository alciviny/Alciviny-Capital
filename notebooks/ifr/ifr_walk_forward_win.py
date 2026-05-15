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

def run_walk_forward_win(timeframe="15"):
    path = get_data_path("WIN$", timeframe)
    if not os.path.exists(path): return
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
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
    
    # Retornos (horizonte de 20 bars)
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    # Separar por Ano
    df['year'] = df['time'].dt.year
    years = sorted(df['year'].unique())
    
    results = []
    for year in years:
        if year < 2021: continue # Filtrar anos com poucos dados se houver
        
        year_df = df[df['year'] == year]
        
        # Stats Compra
        b_data = year_df[year_df['sig_buy'] == True]
        # Stats Venda
        s_data = year_df[year_df['sig_sell'] == True]
        
        all_signals = pd.concat([b_data, s_data])
        
        if len(all_signals) > 0:
            # Calcular retorno ajustado (venda inverte sinal)
            b_ret = b_data['fwd_ret'].mean() if len(b_data) > 0 else 0
            s_ret = -s_data['fwd_ret'].mean() if len(s_data) > 0 else 0
            
            # Média ponderada dos retornos
            total_n = len(b_data) + len(s_data)
            avg_ret = (b_ret * len(b_data) + s_ret * len(s_data)) / total_n
            
            # Win Rate Combinada
            b_wins = (b_data['fwd_ret'] > 0).sum()
            s_wins = (s_data['fwd_ret'] < 0).sum()
            total_wr = (b_wins + s_wins) / total_n * 100
            
            results.append({
                'Ano': year,
                'Ret Médio%': avg_ret,
                'Win Rate%': total_wr,
                'Amostras': total_n,
                'Status': 'POSITIVO' if avg_ret > 0 else 'NEGATIVO'
            })
            
    return results

def run_study():
    print_research_header("WALK-FORWARD ANALYSIS: SETUP SNIPER NO WIN$ (15m)")
    results = run_walk_forward_win()
    
    if results:
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))
        
        # Média Final
        print("\n" + "="*50)
        print(f"ESTABILIDADE DO SETUP: {res_df['Status'].value_counts().to_dict()}")
        print(f"RETORNO MÉDIO HISTÓRICO: {res_df['Ret Médio%'].mean():.4f}%")
        print(f"WIN RATE MÉDIA: {res_df['Win Rate%'].mean():.2f}%")
        print("="*50)

if __name__ == "__main__":
    run_study()
