import pandas as pd
import numpy as np
import polars as pl
import os
import sys
from scipy import stats

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, calculate_rsi_200, print_research_header
from src.core.config import IFR_PERIOD

def calculate_metrics(returns):
    if len(returns) == 0:
        return [0] * 6
    
    mean_ret = returns.mean()
    std_ret = returns.std()
    win_rate = (returns > 0).mean() * 100
    
    # Simulação de Profit Factor (Ganhos brutos / Perdas brutas)
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    pf = gross_profit / (gross_loss + 1e-9)
    
    # Sharpe-like (Média / Std) - Sem anualização para manter "pure data" do candle
    ratio = mean_ret / (std_ret + 1e-9)
    
    return mean_ret, std_ret, win_rate, pf, ratio, len(returns)

def walk_forward_audit(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path):
        return []
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df['year'] = df['time'].dt.year
    df = df.sort_values('time')
    
    # Cálculo IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    df['regime'] = np.where(df['ifr_200'] > 50, 'BULL', 'BEAR')
    
    # Retorno futuro (20 candles)
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    all_years_results = []
    
    for year in sorted(df['year'].unique()):
        year_data = df[df['year'] == year].dropna(subset=['fwd_ret', 'regime'])
        if len(year_data) < 500: continue # Ignorar anos com poucos dados
        
        for regime in ['BULL', 'BEAR']:
            regime_rets = year_data[year_data['regime'] == regime]['fwd_ret']
            
            # Se for BEAR, invertemos o retorno para simular "Estar Vendido"
            if regime == 'BEAR':
                strat_rets = -regime_rets
            else:
                strat_rets = regime_rets
                
            m_ret, s_ret, wr, pf, ratio, count = calculate_metrics(strat_rets)
            
            all_years_results.append({
                'Ativo': symbol,
                'Ano': year,
                'Regime': regime,
                'Exp_Ret%': m_ret,
                'Vol': s_ret,
                'WR%': wr,
                'PF': pf,
                'Ratio': ratio,
                'Amostras': count
            })
            
    return all_years_results

def run_full_audit():
    print_research_header("AUDITORIA INDUSTRIAL: WALK-FORWARD IFR 200")
    
    assets = ["WIN$", "WDO$", "DI1$"]
    full_data = []
    
    for asset in assets:
        print(f"[PROCESSANDO] {asset}...")
        full_data.extend(walk_forward_audit(asset))
    
    results_df = pd.DataFrame(full_data)
    
    # Salvar para análise posterior
    results_df.to_csv("notebooks/ifr/results/walk_forward_audit.csv", index=False)
    
    # Mostrar resumo por Ativo e Regime (Média de todos os anos)
    summary = results_df.groupby(['Ativo', 'Regime'])[['Exp_Ret%', 'PF', 'WR%', 'Ratio']].mean()
    
    print("\n[RESUMO CONSOLIDADO - MÉDIA ANUAL]")
    print(summary.to_string())
    
    print("\n[DETALHE POR ANO - WIN$]")
    print(results_df[results_df['Ativo'] == "WIN$"].to_string(index=False))
    
    print("\n[DETALHE POR ANO - WDO$]")
    print(results_df[results_df['Ativo'] == "WDO$"].to_string(index=False))

if __name__ == "__main__":
    run_full_audit()
