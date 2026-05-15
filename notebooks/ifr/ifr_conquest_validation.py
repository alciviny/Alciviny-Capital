import pandas as pd
import numpy as np
import polars as pl
import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, print_research_header
from src.indicators.oscillators import calculate_rsi_wilder

def analyze_conquest_dynamics(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    # 1. Carregar Dados
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 2. Calcular IFR 200
    df['ifr_200'] = calculate_rsi_wilder(df['close'], period=200)
    df = df.dropna(subset=['ifr_200'])
    
    ifr_values = df['ifr_200'].values
    prices = df['close'].values
    
    conquests = [] # List of dicts: {start_level, outcome, price_delta, bars}
    
    # 3. Máquina de Estados para Conquista
    # Definimos que estamos "testando" um nível quando o IFR entra no bloco N
    # Sucesso: Chega em N+1 antes de cair para N-1
    # Falha: Cai para N-1 antes de chegar em N+1
    
    current_level = int(np.floor(ifr_values[0]))
    start_idx = 0
    
    for i in range(1, len(ifr_values)):
        v = ifr_values[i]
        
        # Se subiu para o próximo nível
        if v >= current_level + 1:
            conquests.append({
                'start_level': current_level,
                'outcome': 1, # Avanço (Conquista)
                'price_pct': (prices[i] / prices[start_idx] - 1) * 100,
                'bars': i - start_idx
            })
            current_level = int(np.floor(v))
            start_idx = i
            
        # Se caiu para o nível anterior
        elif v <= current_level - 1:
            conquests.append({
                'start_level': current_level,
                'outcome': -1, # Recuo (Perda de território)
                'price_pct': (prices[i] / prices[start_idx] - 1) * 100,
                'bars': i - start_idx
            })
            current_level = int(np.floor(v))
            start_idx = i
            
    if not conquests: return None
    
    res_df = pd.DataFrame(conquests)
    
    # 4. Agregação por Nível
    stats = res_df.groupby('start_level').agg({
        'outcome': [lambda x: (x == 1).mean() * 100, 'count'],
        'price_pct': 'mean',
        'bars': 'mean'
    })
    
    stats.columns = ['Prob_Avanco_%', 'Amostras', 'Ret_Medio_Conquista', 'Barras_Medias']
    stats = stats.reset_index()
    
    # Filtrar zona 40-60
    stats = stats[(stats['start_level'] >= 40) & (stats['start_level'] <= 60)]
    
    return stats

def main():
    print_research_header("VALIDAÇÃO: TEORIA DA CONQUISTA DE TERRITÓRIO (IFR 200)")
    
    assets = ["WIN$", "WDO$", "DI1$"]
    
    for asset in assets:
        print(f"\n[ANALISANDO DINÂMICA: {asset}] ...")
        stats = analyze_conquest_dynamics(asset)
        
        if stats is not None:
            print(stats.to_string(index=False))
            
            # Insights
            top_conquest = stats.sort_values('Prob_Avanco_%', ascending=False).iloc[0]
            worst_conquest = stats.sort_values('Prob_Avanco_%', ascending=True).iloc[0]
            
            print(f"\n>>> Melhor Nível de Avanço: {top_conquest['start_level']} ({top_conquest['Prob_Avanco_%']:.1f}% de sucesso)")
            print(f"\n>>> Nível de Maior Resistência: {worst_conquest['start_level']} ({100 - worst_conquest['Prob_Avanco_%']:.1f}% de recuo)")
            
            # Salvar
            output_path = f"results/conquest_{asset.replace('$', '')}.csv"
            stats.to_csv(output_path, index=False)

if __name__ == "__main__":
    main()
