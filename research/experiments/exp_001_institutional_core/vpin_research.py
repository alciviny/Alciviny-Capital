import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.vpin import add_vpin_to_state
from src.indicators.microstructure import add_microstructure_indicators, FlowState

class VPINResearcher:
    def __init__(self, asset: str = "WIN", tf: str = "1"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"

    def load_data(self) -> pl.DataFrame:
        path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        if not os.path.exists(path):
            # Tentar 5m se 1m não existir
            path = os.path.join(self.base_path, f"{self.asset}$_5.parquet")
            
        df = pl.read_parquet(path)
        # 1. Adicionar VPIN (Buckets de 2000 contratos)
        df = add_vpin_to_state(df, bucket_size=2000)
        # 2. Adicionar Microestrutura (Flow States)
        df = add_microstructure_indicators(df)
        return df

    def analyze_vpin_toxicity(self, df: pl.DataFrame):
        print(f"\n--- VPIN TOXICITY RESEARCH: {self.asset} ---")
        
        # 1. Definir Adverse Selection (t+2)
        df = df.with_columns([
            (pl.col("close").shift(-2) / pl.col("close") - 1).abs().alias("abs_fwd_move")
        ])
        
        # 2. Correlação entre VPIN e Volatilidade/Movimento Futuro
        corr = df.select(pl.corr("vpin", "abs_fwd_move")).to_series()[0]
        print(f"Correlação VPIN vs Abs Forward Move (t+2): {corr:.4f}")
        
        # 3. Conditional Analysis: TRAPPED_BUYERS + VPIN
        target_state = FlowState.TRAPPED_BUYERS
        state_df = df.filter(pl.col("flow_state") == target_state.value).drop_nulls()
        
        if len(state_df) > 20:
            # Dividir por percentis de VPIN
            vpin_q75 = state_df["vpin"].quantile(0.75)
            
            high_vpin_df = state_df.filter(pl.col("vpin") >= vpin_q75)
            low_vpin_df = state_df.filter(pl.col("vpin") < vpin_q75)
            
            # Retorno Médio h5
            fwd_ret = (pl.col("close").shift(-5) / pl.col("close") - 1) * -1 * 10000 # Short
            
            print(f"\nAlpha Contextualizado por VPIN:")
            print(f"High VPIN (Toxic): {high_vpin_df.select(fwd_ret.mean())[0,0]:.2f} bps (n={len(high_vpin_df)})")
            print(f"Low VPIN (Informed): {low_vpin_df.select(fwd_ret.mean())[0,0]:.2f} bps (n={len(low_vpin_df)})")
            
            # 4. Toxicidade Realizada (Adverse Selection em 1 candle)
            adv_sel = (pl.col("close").shift(-1) / pl.col("close") - 1).abs() * 10000
            print(f"\nAdverse Selection Realizada:")
            print(f"High VPIN: {high_vpin_df.select(adv_sel.mean())[0,0]:.2f} bps")
            print(f"Low VPIN: {low_vpin_df.select(adv_sel.mean())[0,0]:.2f} bps")

if __name__ == "__main__":
    # WIN 1m (Alta Resolução)
    researcher = VPINResearcher(asset="WIN", tf="1")
    df = researcher.load_data()
    researcher.analyze_vpin_toxicity(df)
    
    # WDO 5m (Escalabilidade)
    print("\n" + "="*50 + "\n")
    researcher_wdo = VPINResearcher(asset="WDO", tf="5")
    df_wdo = researcher_wdo.load_data()
    researcher_wdo.analyze_vpin_toxicity(df_wdo)
