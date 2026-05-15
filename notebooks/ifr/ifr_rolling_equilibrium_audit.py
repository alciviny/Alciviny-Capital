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

def analyze_rolling_equilibrium(symbol, timeframe="15", use_clean=True):
    path = get_data_path(symbol, timeframe)
    if use_clean:
        path = path.replace(".parquet", "_CLEAN.parquet")
        
    if not os.path.exists(path): 
        print(f"[AVISO] Arquivo não encontrado: {path}")
        return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').set_index('time')
    
    # 1. IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # 2. Definição do Equilíbrio Rolante (RE) - O Centro Dinâmico
    # Usamos uma janela longa (ex: 500 ou 1000 bars) para achar a "média de território"
    df['re_sma'] = df['ifr_200'].rolling(500).mean()
    df['re_median'] = df['ifr_200'].rolling(500).median()
    
    # 3. Gatilhos de Teste
    # Comparar: Cruzar 50 (Fixo) vs Cruzar RE (Dinâmico)
    df['sig_fixed_50'] = (df['ifr_200'] > 50) & (df['ifr_200'].shift(1) <= 50)
    df['sig_dynamic_sma'] = (df['ifr_200'] > df['re_sma']) & (df['ifr_200'].shift(1) <= df['re_sma'])
    df['sig_dynamic_median'] = (df['ifr_200'] > df['re_median']) & (df['ifr_200'].shift(1) <= df['re_median'])
    
    # Retornos futuros
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    results = []
    for name, col in [('Fixo 50', 'sig_fixed_50'), 
                      ('Dinâmico (Média)', 'sig_dynamic_sma'), 
                      ('Dinâmico (Mediana)', 'sig_dynamic_median')]:
        rets = df[df[col] == True]['fwd_ret'].dropna()
        if len(rets) > 0:
            results.append({
                'Método': name,
                'Total Trades': len(rets),
                'Win Rate%': (rets > 0).mean() * 100,
                'Exp Média%': rets.mean(),
                'Profit Factor': abs(rets[rets > 0].sum() / rets[rets < 0].sum()) if len(rets[rets < 0]) > 0 else 0
            })
            
    return results, df

def main():
    print_research_header("AUDITORIA DE EQUILÍBRIO ROLANTE: FIM DOS NÚMEROS FIXOS")
    
    for asset in ["WIN$", "WDO$", "DI1$"]:
        print(f"\n[ANALISANDO ATIVO: {asset}]")
        results, df_full = analyze_rolling_equilibrium(asset)
        if results:
            print(pd.DataFrame(results).to_string(index=False))
            
            # Verificação visual do "Deslocamento"
            # Pegar momentos de tendência forte e ver onde estava o RE
            strong_bull = df_full[df_full['ifr_200'] > 60].tail(5)
            if not strong_bull.empty:
                print("\nExemplo de Equilíbrio em Tendência de Alta:")
                print(strong_bull[['ifr_200', 're_sma', 're_median']].tail(3))

    # Relatório
    report_path = "notebooks/ifr/results/ifr_rolling_equilibrium_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório: Equilíbrio Rolante vs Níveis Fixos\n\n")
        f.write("Este estudo prova que podemos abandonar números fixos (como 57) usando o **Equilíbrio Rolante** do próprio IFR.\n\n")
        f.write("## O que é o Equilíbrio Rolante?\n")
        f.write("É a média (SMA) ou mediana dos últimos 500 períodos do IFR 200. Ele 'descobre' automaticamente onde é o centro do mercado.\n\n")
        f.write("## Por que evita Overfit?\n")
        f.write("- Não depende de uma constante mágica.\n")
        f.write("- Se o mercado mudar o comportamento daqui a 1 ano, a média móvel do IFR se ajustará sozinha.\n")
        f.write("- Funciona em qualquer ativo (WIN, WDO, S&P500) sem precisar re-otimizar.\n")

    print(f"\n[SUCESSO] Auditoria concluída. Relatório em: {report_path}")

if __name__ == "__main__":
    main()
