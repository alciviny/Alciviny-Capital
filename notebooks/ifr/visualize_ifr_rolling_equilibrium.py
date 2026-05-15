import pandas as pd
import numpy as np
import polars as pl
import matplotlib.pyplot as plt
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, calculate_rsi_200

def create_viz(symbol="DI1$", timeframe="15", use_clean=True):
    path = get_data_path(symbol, timeframe)
    if use_clean:
        path = path.replace(".parquet", "_CLEAN.parquet")
        
    if not os.path.exists(path): return
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').tail(1500)
    
    # 1. IFR 200 e Equilíbrio Rolante
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    df['re_median'] = df['ifr_200'].rolling(500).median()
    
    # 2. Plotagem
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True, gridspec_kw={'height_ratios': [1, 1]})
    
    # Subplot 1: Preço
    ax1.plot(df['time'], df['close'], color='darkblue', alpha=0.8, label=f'Preço {symbol}')
    ax1.set_title(f"Preço {symbol} (Base Limpa) - 15min", fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Subplot 2: IFR 200 e RE
    ax2.plot(df['time'], df['ifr_200'], color='blue', alpha=0.8, label='IFR 200')
    ax2.plot(df['time'], df['re_median'], color='crimson', linewidth=2.5, label='Equilíbrio Rolante (Mediana 500)')
    ax2.axhline(50, color='black', linestyle='--', alpha=0.4, label='Nível 50 (Obsoleto)')
    
    # Preenchimento
    ax2.fill_between(df['time'], df['ifr_200'], df['re_median'], 
                     where=(df['ifr_200'] >= df['re_median']), color='green', alpha=0.15)
    ax2.fill_between(df['time'], df['ifr_200'], df['re_median'], 
                     where=(df['ifr_200'] < df['re_median']), color='red', alpha=0.15)
    
    ax2.set_title("O Fim do 50: IFR 200 navegando pelo Equilíbrio Dinâmico", fontsize=14, fontweight='bold')
    ax2.set_ylim(df['ifr_200'].min()-2, df['ifr_200'].max()+2)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_path = "notebooks/ifr/results/ifr_clean_rolling_viz.png"
    plt.savefig(output_path)
    print(f"[SUCESSO] Visualização salva em: {output_path}")

if __name__ == "__main__":
    create_viz("DI1$")
