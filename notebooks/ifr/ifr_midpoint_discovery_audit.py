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

def analyze_midpoint_discovery(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').set_index('time')
    
    # 1. IFR 200
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # 2. Definição de Midpoints e Zonas
    # Método A: Fixed 50 (48/52)
    df['mid_fixed'] = 50
    df['zone_fixed'] = (df['ifr_200'] >= 48) & (df['ifr_200'] <= 52)
    
    # Método B: Rolling Mean (Janela longa 1000 bars)
    df['mid_rolling'] = df['ifr_200'].rolling(1000).mean()
    df['zone_rolling'] = (df['ifr_200'] >= df['mid_rolling'] - 2) & (df['ifr_200'] <= df['mid_rolling'] + 2)
    
    # Método C: Z-Score Zero (Equilíbrio Estatístico)
    ifr_std = df['ifr_200'].rolling(500).std()
    df['z_score'] = (df['ifr_200'] - 50) / ifr_std
    df['zone_zscore'] = df['z_score'].abs() < 0.5
    
    def classify_zone_exit(df_sub, zone_col, midpoint_col):
        """Classifica se a saída da zona foi um Pullback ou Reversal."""
        events = []
        df_sub['in_zone'] = df_sub[zone_col]
        df_sub['zone_id'] = (df_sub['in_zone'] != df_sub['in_zone'].shift()).cumsum()
        df_sub.loc[~df_sub['in_zone'], 'zone_id'] = 0
        
        unique_zones = df_sub[df_sub['zone_id'] > 0]['zone_id'].unique()
        
        for zid in unique_zones:
            zone_data = df_sub[df_sub['zone_id'] == zid]
            if len(zone_data) < 2: continue
            
            # Entrada: de onde veio?
            idx_start = zone_data.index[0]
            pos_start = df_sub.index.get_loc(idx_start)
            if pos_start == 0: continue
            entry_val = df_sub['ifr_200'].iloc[pos_start-1]
            entry_mid = df_sub[midpoint_col].iloc[pos_start-1]
            side_entry = 1 if entry_val > entry_mid else -1
            
            # Saída: para onde foi?
            idx_end = zone_data.index[-1]
            pos_end = df_sub.index.get_loc(idx_end)
            if pos_end >= len(df_sub) - 1: continue
            exit_val = df_sub['ifr_200'].iloc[pos_end+1]
            exit_mid = df_sub[midpoint_col].iloc[pos_end+1]
            side_exit = 1 if exit_val > exit_mid else -1
            
            # Classificação
            # Pullback: Voltou para o lado de onde veio
            # Reversal: Cruzou para o outro lado
            event_type = "PULLBACK" if side_entry == side_exit else "REVERSAL"
            
            # Performance pós-saída (20 bars)
            h = 20
            fwd_ret = (df_sub['close'].shift(-h).iloc[pos_end+1] / df_sub['close'].iloc[pos_end+1] - 1) * 100
            
            events.append({
                'type': event_type,
                'ret': fwd_ret,
                'duration': len(zone_data),
                'side': side_entry
            })
            
        return events

    all_stats = []
    for method, zone_col, mid_col in [('Fixed 50', 'zone_fixed', 'mid_fixed'), 
                                     ('Rolling SMA', 'zone_rolling', 'mid_rolling'), 
                                     ('Z-Score 0.5', 'zone_zscore', 'mid_fixed')]: # Z-Score usa 50 como ref
        events = classify_zone_exit(df.copy(), zone_col, mid_col)
        if not events: continue
        
        ev_df = pd.DataFrame(events)
        pullbacks = ev_df[ev_df['type'] == 'PULLBACK']
        reversals = ev_df[ev_df['type'] == 'REVERSAL']
        
        # Expectativa por tipo
        pb_exp = pullbacks['ret'].mean()
        rv_exp = reversals['ret'].mean()
        
        pb_count = len(pullbacks)
        rv_count = len(reversals)
        total = pb_count + rv_count
        
        all_stats.append({
            'Método': method,
            'Prob Pullback%': (pb_count / total) * 100,
            'Exp Pullback%': pb_exp,
            'Exp Reversal%': rv_exp,
            'Duração Média': ev_df['duration'].mean(),
            'Total Eventos': total
        })
        
    return all_stats

def main():
    print_research_header("DISCOBERTA DE MIDPOINT: PULLBACK VS REVERSAL (IFR 200)")
    
    summary = []
    for asset in ["WIN$", "WDO$", "DI1$"]:
        print(f"\n[ANALISANDO: {asset}]")
        stats = analyze_midpoint_discovery(asset)
        if stats:
            for s in stats:
                s['Ativo'] = asset
                summary.append(s)
            print(pd.DataFrame(stats).to_string(index=False))
            
    # Relatório
    report_path = "notebooks/ifr/results/ifr_midpoint_audit_results.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    df_sum = pd.DataFrame(summary)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Auditoria de Midpoint: Onde o Regime de Fato Muda?\n\n")
        f.write("Este estudo analisa o comportamento do IFR 200 ao entrar na 'Zona Neutra' e sua capacidade de prever Pullbacks vs Reversões.\n\n")
        
        for asset in df_sum['Ativo'].unique():
            f.write(f"## Ativo: {asset}\n")
            f.write(df_sum[df_sum['Ativo'] == asset].drop(columns='Ativo').to_markdown(index=False))
            f.write("\n\n")
            
        f.write("## Conclusões sobre a Assertividade\n")
        f.write("1. **Fixed 50 (48/52)**: É a zona clássica. Se a Prob Pullback for alta, confirma a tese de zona de valor.\n")
        f.write("2. **Rolling/Z-Score**: Se apresentarem maior Exp Pullback, indicam que o 'centro' é dinâmico e depende da volatilidade recente.\n")
        f.write("3. **Ponto de Inflexão**: O método com menor 'Duração Média' e maior 'Exp Reversal' identifica o momento exato da troca de mãos.\n")

    print(f"\n[SUCESSO] Auditoria concluída. Relatório em: {report_path}")

if __name__ == "__main__":
    main()
