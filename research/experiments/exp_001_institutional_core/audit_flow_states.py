import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# Root path setup (4 levels up from research/experiments/exp_001_institutional_core/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.microstructure import add_microstructure_indicators, FlowState
from src.data.factory import StateVectorFactory
from research.experiments.exp_001_institutional_core.engine import InstitutionalCore

def run_flow_state_audit():
    print(f"[{datetime.now()}] Iniciando Auditoria Estatística de Estados de Fluxo...")
    
    # 1. Preparação de Dados
    base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
    win_file = os.path.join(base_path, "WIN$_15_CLEAN.parquet")
    wdo_file = os.path.join(base_path, "WDO$_15_CLEAN.parquet")
    
    if not os.path.exists(win_file) or not os.path.exists(wdo_file):
        print("Erro: Arquivos de dados não encontrados.")
        return

    win_df = pl.read_parquet(win_file)
    wdo_df = pl.read_parquet(wdo_file).select(["time", "close"]).rename({"close": "WDO"})
    
    # Identificar colunas disponíveis no WIN
    available_cols = win_df.columns
    cols_to_keep = ["time", "open", "high", "low", "close", "volume"]
    if "bid_volume" in available_cols: cols_to_keep.append("bid_volume")
    if "ask_volume" in available_cols: cols_to_keep.append("ask_volume")
    
    win_df = win_df.select(cols_to_keep)
    
    # Manter close para a FlowStateMachine, mas criar WIN para o InstitutionalCore
    win_df = win_df.with_columns([
        pl.col("close").alias("WIN")
    ])
    
    # Join para ter WIN e WDO no mesmo DF
    df = win_df.join(wdo_df, on="time", how="inner")
    print(f"Dados carregados e alinhados: {len(df)} linhas.")

    core = InstitutionalCore()

    # 2. Geração de Regimes Macro e Micro
    print("Gerando Regimes Macro (MRS) e Micro (FlowState)...")
    # Gerar regimes macro via core
    # Reduzimos reps para o audit ser rápido
    results = core.run_full_analysis(df.tail(5000), target="WIN", confluences=["WDO"])
    
    # IMPORTANTE: InstitutionalCore não retorna colunas OHLC. Precisamos dar o join de volta.
    # Usamos o 'time' para o join.
    results = results.join(df.select(["time", "open", "high", "low", "close", "volume"]), on="time", how="inner")
    
    # Adicionar indicadores de microestrutura (OFI, VRP, FlowStates)
    df_enriched = add_microstructure_indicators(results)
    
    # 3. Cálculo de Retornos Forward (Causalidade)
    windows = [1, 3, 5, 10] # Candles de 15min -> 15m, 45m, 1h15, 2h30
    for n in windows:
        df_enriched = df_enriched.with_columns([
            (pl.col("WIN").shift(-n) / pl.col("WIN") - 1).alias(f"fwd_ret_{n}")
        ])

    # 4. Análise Estatística por Estado
    states = [s.value for s in FlowState]
    stats_report = []

    print("\n--- PERFORMANCE CONDICIONAL POR ESTADO (Fwd 5 - 1h15) ---")
    for state in states:
        state_df = df_enriched.filter(pl.col("flow_state") == state)
        count = len(state_df)
        if count < 5: continue 
        
        freq = count / len(df_enriched)
        
        # Retorno médio 5 candles à frente (1h15)
        mean_ret = state_df["fwd_ret_5"].mean() * 10000 # em bps
        std_ret = state_df["fwd_ret_5"].std() * 10000
        sharpe_proxy = mean_ret / std_ret if std_ret > 0 else 0
        
        stats_report.append({
            "state": state,
            "freq": freq,
            "count": count,
            "mean_ret_bps": mean_ret,
            "sharpe": sharpe_proxy,
            "skew": state_df["fwd_ret_5"].skew(),
            "kurt": state_df["fwd_ret_5"].kurtosis()
        })

    stats_df = pd.DataFrame(stats_report).sort_values("sharpe", ascending=False)
    print(stats_df.to_string(index=False))

    # 5. Matriz de Transição
    print("\n--- MATRIZ DE TRANSIÇÃO DE ESTADOS (%) ---")
    df_pd = df_enriched.select(["flow_state"]).to_pandas()
    df_pd["next_state"] = df_pd["flow_state"].shift(-1)
    
    trans_matrix = pd.crosstab(df_pd["flow_state"], df_pd["next_state"], normalize='index') * 100
    print(trans_matrix.round(1))

    # 6. Análise Condicional (Micro | Macro)
    print("\n--- EDGE POR REGIME MACRO (Mean Ret 5 in BPS) ---")
    # No Polars results, as colunas de prob são regime_0_prob etc, mas regime_name tem o nome
    macro_micro = df_enriched.group_by(["regime_name", "flow_state"]).agg([
        (pl.col("fwd_ret_5").mean() * 10000).alias("mean_bps"),
        pl.count().alias("n")
    ]).filter(pl.col("n") > 3).sort(["regime_name", "mean_bps"], descending=[False, True])
    
    print(macro_micro.to_pandas())

    # 7. Information Gain (Mutual Information) - Desativado temporariamente para evitar erros de amostragem
    print("\n--- Auditoria Completa. MI ignorado para estabilidade. ---")

    return stats_df

if __name__ == "__main__":
    run_flow_state_audit()
