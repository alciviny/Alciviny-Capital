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
from src.core.config import IFR_PERIOD, TRANSACTION_COST

def audit_asset(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path):
        return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # Cálculo IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # Regimes
    df['regime'] = np.where(df['ifr_200'] > 50, 'BULL', 'BEAR')
    df.loc[df['ifr_200'].isna(), 'regime'] = np.nan
    
    # Retorno futuro (20 candles)
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    # Métricas por Regime
    stats = df.groupby('regime')['fwd_ret'].agg(['mean', 'std', 'count'])
    
    # Cálculo de "Hit Rate" da Tendência (Sinal do retorno bate com o regime?)
    df['hit'] = np.where(df['regime'] == 'BULL', df['fwd_ret'] > 0, df['fwd_ret'] < 0)
    hit_rate = df.groupby('regime')['hit'].mean() * 100
    
    return {
        'symbol': symbol,
        'bull_ret': stats.loc['BULL', 'mean'] if 'BULL' in stats.index else 0,
        'bear_ret': stats.loc['BEAR', 'mean'] if 'BEAR' in stats.index else 0,
        'bull_hit': hit_rate.get('BULL', 0),
        'bear_hit': hit_rate.get('BEAR', 0),
        'samples': len(df.dropna(subset=['regime']))
    }

def run_multi_asset_audit():
    print_research_header("AUDITORIA MULTI-ATIVO: IFR 200 LINHA 50")
    
    assets = ["WIN$", "WDO$", "DI1$"]
    results = []
    
    for asset in assets:
        print(f"[AUDIT] Analisando {asset}...")
        res = audit_asset(asset)
        if res:
            results.append(res)
    
    report_df = pd.DataFrame(results)
    
    print("\n[RESULTADOS DA AUDITORIA]")
    print(report_df.to_string(index=False, formatters={
        'bull_ret': '{:+.4f}%'.format,
        'bear_ret': '{:+.4f}%'.format,
        'bull_hit': '{:.1f}%'.format,
        'bear_hit': '{:.1f}%'.format
    }))
    
    # Análise de Viés
    global_bull_bias = report_df['bull_ret'].mean()
    global_bear_bias = report_df['bear_ret'].mean()
    
    print("\n[VEREDITO DO AUDITOR]")
    print(f"Média Global Bull Ret: {global_bull_bias:+.4f}%")
    print(f"Média Global Bear Ret: {global_bear_bias:+.4f}%")
    
    is_robust = (global_bull_bias > 0 and global_bear_bias < 0)
    if is_robust:
        print(">>> RESULTADO: A hipótese é ROBUSTA através de múltiplos ativos.")
    else:
        print(">>> RESULTADO: A hipótese apresenta VIÉS DE ATIVO ou RUÍDO estatístico.")

if __name__ == "__main__":
    run_multi_asset_audit()
