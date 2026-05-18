import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.models.macro_regime_detector import MacroRegimeDetector
from src.indicators.microstructure import add_microstructure_indicators
from src.indicators.vpin import add_vpin_to_state

class MacroRegimeResearcher:
    def __init__(self, assets: List[str] = ["WDO", "WIN"]):
        self.assets = assets
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"

    def load_and_aggregate(self) -> pl.DataFrame:
        print("Lendo e agregando dados para horizontes macro (1h)...")
        
        # Carregar WDO (Base)
        wdo = pl.read_parquet(os.path.join(self.base_path, "WDO$_5.parquet"))
        win = pl.read_parquet(os.path.join(self.base_path, "WIN$_5.parquet"))
        
        # 1. Alinhamento Temporal e Cálculo de DCC Proxy (Correlação WIN/WDO)
        wdo_ret = wdo.select(["time", "close"]).with_columns((pl.col("close").pct_change()).alias("ret_wdo"))
        win_ret = win.select(["time", "close"]).with_columns((pl.col("close").pct_change()).alias("ret_win"))
        
        df = wdo_ret.join(win_ret, on="time", how="inner")
        df = df.with_columns([
            pl.rolling_corr(pl.col("ret_wdo"), pl.col("ret_win"), window_size=20).alias("dcc_proxy")
        ])
        
        # 2. Features Estruturais (ainda em 5m)
        wdo = add_vpin_to_state(wdo)
        wdo = add_microstructure_indicators(wdo)
        
        # Volatilidade Parkinson
        log_hl = (wdo["high"] / wdo["low"]).log()
        wdo = wdo.with_columns([
            (log_hl**2).rolling_mean(window_size=20).sqrt().alias("vol_realized"),
            pl.col("vpin").rolling_mean(window_size=20).alias("vpin_smooth"),
            pl.col("ofi").rolling_sum(window_size=12).alias("ofi_agg") # ~1h de fluxo
        ])
        
        # 3. Agregação para 1h
        df_merged = wdo.join(df.select(["time", "dcc_proxy"]), on="time", how="left")
        
        # Hurst Proxy: Volatilidade / (Volume^0.5)
        df_merged = df_merged.with_columns([
            (pl.col("vol_realized") / (pl.col("volume").sqrt() + 1e-9)).alias("hurst_proxy")
        ])
        
        macro_df = df_merged.group_by_dynamic("time", every="1h").agg([
            pl.col("vol_realized").mean(),
            pl.col("dcc_proxy").mean(),
            pl.col("ofi_agg").mean(),
            pl.col("vpin_smooth").mean(),
            pl.col("hurst_proxy").mean().alias("hurst"),
            pl.col("close").last().alias("price")
        ]).drop_nulls()
        
        return macro_df

    def run_persistence_audit(self, df: pl.DataFrame):
        print(f"\n--- REGIME PERSISTENCE AUDIT (1h Horizon) ---")
        
        detector = MacroRegimeDetector(n_states=3)
        detector.fit(df)
        states = detector.predict(df)
        
        stats = detector.get_persistence_stats(states)
        trans_mat = detector.get_transition_matrix()
        
        print("\nMATRIZ DE TRANSIÇÃO (Probabilidades):")
        labels = ["Estável/Calm", "Trend/Persistent", "Stress/Toxic"]
        tm_df = pd.DataFrame(trans_mat, columns=labels, index=labels)
        print(tm_df.to_string())
        
        print("\nESTATÍSTICAS DE PERSISTÊNCIA:")
        for k, v in stats.items():
            unit = "horas" if "duration" in k else ""
            print(f"{k}: {v:.2f} {unit}")
            
        # 4. Forward Stability (Simulando 2024 vs 2025)
        # Dividir o dataframe ao meio
        mid = len(df) // 2
        df_1 = df.head(mid)
        df_2 = df.tail(mid)
        
        detector_1 = MacroRegimeDetector(n_states=3)
        detector_1.fit(df_1)
        tm_1 = detector_1.get_transition_matrix()
        
        detector_2 = MacroRegimeDetector(n_states=3)
        detector_2.fit(df_2)
        tm_2 = detector_2.get_transition_matrix()
        
        # Medir estabilidade via erro médio absoluto entre matrizes
        tm_stability = np.mean(np.abs(tm_1 - tm_2))
        print(f"\nESTABILIDADE DAS TRANSIÇÕES (TM Error): {tm_stability:.4f}")
        if tm_stability < 0.1:
            print("STATUS: Regimes Estruturalmente Estáveis.")
        else:
            print("STATUS: Regimes Instáveis (Drift Macro Detectado).")

if __name__ == "__main__":
    researcher = MacroRegimeResearcher()
    df = researcher.load_and_aggregate()
    researcher.run_persistence_audit(df)
