import pandas as pd
import numpy as np
import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, calculate_rsi_200, print_research_header
from src.core.config import IFR_PERIOD

def run_validation():
    print_research_header("VALIDAÇÃO IFR 200: LINHA 50 COMO DIVISOR")
    
    symbol = "WIN$"
    timeframe = "15"
    path = get_data_path(symbol, timeframe)
    
    print(f"[INFO] Carregando dados: {symbol} {timeframe}m")
    df_pl = pl.read_parquet(path)
    df = df_pl.to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    print(f"[INFO] Calculando IFR 200...")
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # Definir Regimes
    df['regime'] = np.where(df['ifr_200'] > 50, 'BULL', 'BEAR')
    df.loc[df['ifr_200'].isna(), 'regime'] = np.nan
    
    print("\n[ESTATÍSTICAS DE REGIME]")
    counts = df['regime'].value_counts(normalize=True) * 100
    for regime, perc in counts.items():
        print(f"Regime {regime:4}: {perc:5.1f}% do tempo")

    # 1. Análise de Retornos Futuros
    horizons = [5, 20, 50]
    print("\n[MÉDIA DE RETORNOS FUTUROS (%) POR REGIME]")
    for h in horizons:
        df[f'ret_{h}'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    summary = df.groupby('regime')[[f'ret_{h}' for h in horizons]].mean()
    print(summary)

    # 2. Plot: Equity Curve
    print("\n[INFO] Gerando Equity Curve...")
    df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
    df['strategy_ret'] = df['log_ret'] * np.where(df['regime'].shift(1) == 'BULL', 1, -1)
    
    plt.figure(figsize=(12, 6))
    plt.plot(df['time'], df['log_ret'].cumsum(), label='Buy & Hold (WIN)', color='gray', alpha=0.5)
    plt.plot(df['time'], df['strategy_ret'].cumsum(), label='IFR 200 Trend Follow (Long/Short)', color='blue')
    plt.title(f"Equity Curve: IFR 200 Trend Divisor (WIN 15m)")
    plt.xlabel("Data")
    plt.ylabel("Log Retorno Acumulado")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    output_path = "notebooks/ifr/results/equity_curve.png"
    plt.savefig(output_path)
    print(f"[INFO] Equity Curve salva em: {output_path}")

    # 3. Plot: Distribuição de Retornos
    plt.figure(figsize=(10, 5))
    sns.kdeplot(df[df['regime'] == 'BULL']['ret_20'], label='Retornos em Bull (IFR > 50)', fill=True)
    sns.kdeplot(df[df['regime'] == 'BEAR']['ret_20'], label='Retornos em Bear (IFR < 50)', fill=True)
    plt.axvline(0, color='red', linestyle='--')
    plt.title("Densidade de Retornos Futuros (20 candles) por Regime")
    plt.xlabel("Retorno (%)")
    plt.legend()
    
    dist_path = "notebooks/ifr/results/return_distribution.png"
    plt.savefig(dist_path)
    print(f"[INFO] Distribuição salva em: {dist_path}")

    # Check if hypothesis holds
    bull_mean = df[df['regime'] == 'BULL']['ret_20'].mean()
    bear_mean = df[df['regime'] == 'BEAR']['ret_20'].mean()
    
    print("\n[VEREDITO]")
    if bull_mean > 0 and bear_mean < 0:
        print(">>> HIPÓTESE VALIDADA: A linha 50 separa regimes com viés de retorno opostos.")
    elif bull_mean > bear_mean:
        print(">>> HIPÓTESE PARCIAL: Existe um viés relativo, mas um ou ambos os regimes não têm sinal absoluto esperado.")
    else:
        print(">>> HIPÓTESE REJEITADA: O IFR 200 na linha 50 não mostrou viés de tendência claro neste ativo/timeframe.")

if __name__ == "__main__":
    run_validation()
