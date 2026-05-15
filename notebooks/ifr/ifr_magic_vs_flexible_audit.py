import pandas as pd
import numpy as np
import polars as pl
import os
import sys
import logging

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, calculate_rsi_200, print_research_header
from src.indicators.regime.entropy import PermutationEntropyAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IFR_Audit")

def calculate_magic_hysteresis(ifr_series, up=52, lo=48):
    """Implementa a regra de histerese 48/52."""
    modes = []
    curr = 0
    for v in ifr_series:
        if v > up: curr = 1
        elif v < lo: curr = -1
        modes.append(curr)
    return np.array(modes)

def calculate_zscore_regime(ifr_series, window=500, k=0.5):
    """Implementa a regra adaptativa de Z-Score."""
    rolling_std = pd.Series(ifr_series).rolling(window).std()
    upper = 50 + (k * rolling_std)
    lower = 50 - (k * rolling_std)
    
    modes = []
    curr = 0
    for v, up, lo in zip(ifr_series, upper, lower):
        if np.isnan(up) or np.isnan(lo):
            modes.append(0)
            continue
        if v > up: curr = 1
        elif v < lo: curr = -1
        modes.append(curr)
    return np.array(modes)

def calculate_perceptis_regime(df_input, ifr_series):
    """
    Implementa a regra 'Perceptis' baseada em Entropia de Permutação.
    Regra: Bull se IFR > 50 E Entropia indica Estrutura (PE < 0.8).
    """
    # Usar WIN como referência para PE se for multi-asset, ou o próprio ativo
    # Para simplificar este audit, calculamos a PE da série de retornos do ativo atual.
    rets = df_input['close'].pct_change().fillna(0)
    pe_analyzer = PermutationEntropyAnalyzer(rolling_window=63)
    
    # Simular estrutura do analyzer
    series_vals = rets.values
    m, tau = 3, 1
    pe_vals = np.full(len(series_vals), np.nan)
    
    # Otimização simples para o audit
    for i in range(63, len(series_vals) + 1):
        sub = series_vals[i-63:i]
        # Padrões ordinais
        shape = (sub.shape[0] - (m - 1) * tau, m)
        strides = (sub.strides[0], tau * sub.strides[0])
        embedded = np.lib.stride_tricks.as_strided(sub, shape=shape, strides=strides)
        patterns = np.argsort(embedded, axis=1)
        
        weights = m ** np.arange(m)
        codes = (patterns * weights).sum(axis=1)
        unique, counts = np.unique(codes, return_counts=True)
        probs = counts / counts.sum()
        h = -np.sum(probs * np.log(probs)) / np.log(6) # Log(factorial(3))
        pe_vals[i-1] = h
        
    modes = []
    curr = 0
    for v, pe in zip(ifr_series, pe_vals):
        if np.isnan(pe):
            modes.append(0)
            continue
        # Se está estruturado (PE < 0.8), seguimos o IFR. Caso contrário, neutro.
        if pe < 0.8:
            if v > 50: curr = 1
            elif v < 50: curr = -1
        else:
            curr = 0
        modes.append(curr)
    return np.array(modes)

def run_asset_audit(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').set_index('time')
    
    # 1. IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # 2. Métodos
    df['reg_magic'] = calculate_magic_hysteresis(df['ifr_200'])
    df['reg_zscore'] = calculate_zscore_regime(df['ifr_200'])
    df['reg_perceptis'] = calculate_perceptis_regime(df, df['ifr_200'])
    
    # 3. Métricas
    h = 20 # Próximas 5 horas
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    methods = [
        ('Magic Numbers (48/52)', 'reg_magic'),
        ('Adaptive Z-Score', 'reg_zscore'),
        ('Perceptis (PE Filter)', 'reg_perceptis')
    ]
    
    for name, col in methods:
        # Filtrar apenas estados não-neutros
        active = df[df[col] != 0]
        if active.empty:
            results.append({'Método': name, 'Exp%': 0, 'Win%': 0, 'Estabilidade': 0, 'PF': 0})
            continue
            
        exp = active['fwd_ret'].mean()
        win_rate = (active['fwd_ret'] > 0).mean() * 100
        
        # Estabilidade: média de barras no mesmo estado
        df['change'] = df[col] != df[col].shift(1)
        switches = df['change'].sum()
        stability = len(df) / switches if switches > 0 else len(df)
        
        # Profit Factor Simplificado
        gains = active[active['fwd_ret'] > 0]['fwd_ret'].sum()
        losses = abs(active[active['fwd_ret'] < 0]['fwd_ret'].sum())
        pf = gains / losses if losses > 0 else 0
        
        results.append({
            'Método': name,
            'Exp%': exp,
            'Win%': win_rate,
            'Estabilidade': stability,
            'PF': pf
        })
        
    return results

def main():
    print_research_header("AUDITORIA: MAGIC NUMBERS VS FLEXIBLE METHODS (IFR 200)")
    
    all_results = {}
    for asset in ["WIN$", "WDO$", "DI1$"]:
        print(f"\n[PROCESSANDO: {asset}]...")
        res = run_asset_audit(asset)
        if res:
            all_results[asset] = pd.DataFrame(res)
            print(all_results[asset].to_string(index=False))
            
    # Relatório Final
    report_path = os.path.join(script_dir, "results/ifr_magic_vs_flexible_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria: IFR 200 (Magic vs Flexible)\n\n")
        for asset, df_res in all_results.items():
            f.write(f"## Ativo: {asset}\n")
            f.write(df_res.to_markdown(index=False))
            f.write("\n\n")
            
        f.write("## Conclusão da Auditoria\n")
        f.write("A hipótese de que os **Números Mágicos (48/52)** são mais assertivos baseia-se na sua estabilidade temporal e na redução do 'chicote' (whipsaw) em zonas de ruído.\n")
        f.write("Métodos flexíveis como Z-Score e Perceptis tendem a ser mais reativos, mas podem sofrer com a quebra de regime em timeframes menores.\n")

    print(f"\n[SUCESSO] Relatório salvo em: {report_path}")

if __name__ == "__main__":
    main()
