import pandas as pd
import numpy as np
import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from typing import Dict, List

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, print_research_header
from src.indicators.oscillators import calculate_rsi_wilder

def run_comprehensive_ifr_1000_audit():
    assets = ["WIN$", "WDO$", "DI1$"]
    summary_results = []
    
    for symbol in assets:
        print_research_header(f"AUDITORIA: IFR 1000 vs IFR 200 ({symbol})")
        
        path = get_data_path(symbol, timeframe="15")
        if not os.path.exists(path): continue
            
        df = pl.read_parquet(path).to_pandas()
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').set_index('time')
        
        # Calcular IFRs
        df['ifr_200'] = calculate_rsi_wilder(df['close'], period=200)
        df['ifr_1000'] = calculate_rsi_wilder(df['close'], period=1000)
        df['ifr_50'] = calculate_rsi_wilder(df['close'], period=50)
        
        # Retornos
        df['ret_100'] = (df['close'].shift(-100) / df['close'] - 1) * 100
        
        # Stats
        bull_200 = df[df['ifr_200'] > 50]['ret_100'].mean()
        bull_1000 = df[df['ifr_1000'] > 50]['ret_100'].mean()
        
        # Sniper Test
        def backtest_sniper(anchor_col):
            signals = (df[anchor_col] > 52) & (df['ifr_50'] > 45) & (df['ifr_50'].shift(1) <= 45)
            rets = df[signals.shift(1).fillna(False)]['ret_100']
            return rets.mean() if not rets.empty else 0

        sniper_200 = backtest_sniper('ifr_200')
        sniper_1000 = backtest_sniper('ifr_1000')
        
        summary_results.append({
            'Asset': symbol,
            'Bull_Ret_200': bull_200,
            'Bull_Ret_1000': bull_1000,
            'Sniper_200_Ret': sniper_200,
            'Sniper_1000_Ret': sniper_1000
        })

    summary_df = pd.DataFrame(summary_results)
    print("\n[RESULTADO GLOBAL]")
    print(summary_df.to_string(index=False))
    
    # Gerar Relatório Consolidated
    report_path = os.path.join(script_dir, "results/ifr_1000_mega_audit.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Auditoria Global IFR 1000 vs 200\n\n")
        f.write(summary_df.to_markdown(index=False))
        
    print(f"\n[SUCESSO] Relatório salvo em: {report_path}")

if __name__ == "__main__":
    run_comprehensive_ifr_1000_audit()
