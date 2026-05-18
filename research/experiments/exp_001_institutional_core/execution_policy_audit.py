import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.vpin import add_vpin_to_state
from src.indicators.microstructure import add_microstructure_indicators, FlowState

class ExecutionPolicyAuditor:
    """
    Motor de Otimização de Políticas de Execução.
    Decide entre Passive, Aggressive ou Skip baseado no contexto microestrutural.
    """
    def __init__(self, asset: str = "WDO", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        
        if asset == "WDO":
            self.tick_size = 0.5
            self.contract_value = 10.0
            self.avg_spread_bps = 1.2
            self.fixed_fees_bps = 0.3
        else:
            self.tick_size = 5.0
            self.contract_value = 0.2
            self.avg_spread_bps = 0.8
            self.fixed_fees_bps = 0.1

    def load_data(self) -> pl.DataFrame:
        path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        df = pl.read_parquet(path)
        df = add_vpin_to_state(df, bucket_size=2000)
        df = add_microstructure_indicators(df)
        
        # Extrair Hora para Temporal Topology
        df = df.with_columns([
            pl.col("time").dt.hour().alias("hour")
        ])
        return df

    def temporal_topology_report(self, df: pl.DataFrame):
        print(f"\n--- TEMPORAL LIQUIDITY TOPOLOGY: {self.asset} ---")
        
        # Média de VPIN por hora
        topology = df.group_by("hour").agg([
            pl.col("vpin").mean().alias("avg_vpin"),
            pl.col("volume").mean().alias("avg_volume")
        ]).sort("hour")
        
        print(topology.to_pandas().to_string(index=False))
        return topology

    def backtest_policies(self, df: pl.DataFrame):
        print(f"\n--- EXECUTION POLICY BACKTEST: {self.asset} ---")
        
        target_state = FlowState.TRAPPED_BUYERS
        state_df = df.filter(pl.col("flow_state") == target_state.value).drop_nulls()
        
        if len(state_df) < 50: return None

        # 1. Definir Thresholds de VPIN (Institucionais)
        q_low = state_df["vpin"].quantile(0.33)
        q_high = state_df["vpin"].quantile(0.85)
        q_extreme = state_df["vpin"].quantile(0.95)
        
        # 2. Retorno Bruto (h5)
        side = -1 # Trapped Buyers = SELL
        gross_ret_expr = (pl.col("close").shift(-5) / pl.col("close") - 1) * side * 10000
        
        # 3. Modelagem de Custos
        # Aggressive: Paga Spread + Taxas
        # Passive: Ganha Spread - Taxas (65% Fill Rate)
        # Skip: Zero
        
        cost_agg = self.avg_spread_bps + self.fixed_fees_bps
        cost_pass = -self.avg_spread_bps + self.fixed_fees_bps
        fill_prob = 0.65

        state_df = state_df.with_columns([
            gross_ret_expr.alias("gross_alpha"),
            # Política Baseline: Sempre Agressiva
            (gross_ret_expr - cost_agg).alias("ret_always_agg"),
            # Política Adaptativa
            pl.when(pl.col("vpin") >= q_extreme).then(0.0) # SKIP (Toxic)
              .when(pl.col("vpin") >= q_high).then(gross_ret_expr - cost_agg) # AGGRESSIVE (Momentum)
              .when(pl.col("vpin") <= q_low).then((gross_ret_expr - cost_pass) * fill_prob) # PASSIVE (Structural)
              .otherwise(gross_ret_expr - cost_agg).alias("ret_adaptive") # HYBRID (Default Aggressive)
        ])
        
        # 4. Métricas de Performance
        metrics = state_df.select([
            pl.col("ret_always_agg").mean().alias("avg_agg_bps"),
            pl.col("ret_adaptive").mean().alias("avg_adaptive_bps"),
            pl.col("ret_always_agg").std().alias("std_agg"),
            pl.col("ret_adaptive").std().alias("std_adaptive"),
            (pl.col("vpin") >= q_extreme).sum().alias("skipped_trades")
        ])
        
        sharpe_agg = metrics[0, "avg_agg_bps"] / (metrics[0, "std_agg"] + 1e-9)
        sharpe_adaptive = metrics[0, "avg_adaptive_bps"] / (metrics[0, "std_adaptive"] + 1e-9)
        
        print(f"Alpha Médio (Always Aggressive): {metrics[0, 'avg_agg_bps']:.2f} bps | Sharpe: {sharpe_agg:.4f}")
        print(f"Alpha Médio (VPIN Adaptive):    {metrics[0, 'avg_adaptive_bps']:.2f} bps | Sharpe: {sharpe_adaptive:.4f}")
        print(f"Trades Poupados (Toxic Skip): {metrics[0, 'skipped_trades']} de {len(state_df)}")
        
        improvement = ((sharpe_adaptive / (sharpe_agg + 1e-9)) - 1) * 100
        print(f"Melhoria no Sharpe de Execução: {improvement:.2f}%")
        
        return state_df

if __name__ == "__main__":
    auditor = ExecutionPolicyAuditor(asset="WDO", tf="5")
    df = auditor.load_data()
    auditor.temporal_topology_report(df)
    auditor.backtest_policies(df)
