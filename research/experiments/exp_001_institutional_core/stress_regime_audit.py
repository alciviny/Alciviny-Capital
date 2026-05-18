import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.mixture import GaussianMixture

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.vpin import add_vpin_to_state
from src.indicators.microstructure import add_microstructure_indicators, FlowState

class StressAuditor:
    """
    Motor de Auditoria de Stress e Sobrevivência.
    Simula colapsos de liquidez e eventos macro para testar a robustez do alpha.
    """
    def __init__(self, asset: str = "WDO", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        
        if asset == "WDO":
            self.baseline_spread_bps = 1.2
            self.fixed_fees_bps = 0.3
        else:
            self.baseline_spread_bps = 0.8
            self.fixed_fees_bps = 0.1

    def load_data(self) -> pl.DataFrame:
        path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        df = pl.read_parquet(path)
        df = add_vpin_to_state(df, bucket_size=2000)
        df = add_microstructure_indicators(df)
        
        # Calcular Volatilidade Realizada (Parkinson)
        const = 1.0 / (4.0 * np.log(2.0))
        log_hl = (pl.col("high") / (pl.col("low") + 1e-9)).log()
        df = df.with_columns([
            ((log_hl**2).rolling_mean(window_size=20).sqrt() * np.sqrt(const)).alias("vol_local")
        ])
        return df

    def run_stress_audit(self, df: pl.DataFrame):
        print(f"\n--- STRESS REGIME AUDIT: {self.asset} ---")
        
        target_state = FlowState.TRAPPED_BUYERS
        state_df = df.filter(pl.col("flow_state") == target_state.value).drop_nulls()
        
        if len(state_df) < 50: return None

        # 1. Identificar Regimes de Stress (HMM Kill-Switch Simples)
        # Usamos GMM como proxy de HMM de 2 estados: Estável vs Estressado
        features = state_df.select(["vol_local", "vpin"]).to_pandas()
        gmm = GaussianMixture(n_components=2, random_state=42)
        regimes = gmm.fit_predict(features)
        
        # Identificar qual estado é o "Estressado" (maior vol média)
        st_0_vol = features[regimes == 0]["vol_local"].mean()
        st_1_vol = features[regimes == 1]["vol_local"].mean()
        toxic_state = 1 if st_1_vol > st_0_vol else 0
        
        state_df = state_df.with_columns([
            pl.Series(name="regime_toxic", values=(regimes == toxic_state).astype(int))
        ])

        # 2. Simulação de Colapso de Liquidez (Stress Modeling)
        # Durante regime tóxico: Spread x 3, Slippage x 5
        side = -1
        gross_alpha = (pl.col("close").shift(-5) / pl.col("close") - 1) * side * 10000
        
        cost_normal = self.baseline_spread_bps + self.fixed_fees_bps
        cost_stress = (self.baseline_spread_bps * 3.0) + (self.fixed_fees_bps + 5.0) # 5bps slippage extra
        
        state_df = state_df.with_columns([
            pl.when(pl.col("regime_toxic") == 1)
              .then(gross_alpha - cost_stress)
              .otherwise(gross_alpha - cost_normal)
              .alias("net_alpha_stressed")
        ])

        # 3. Relatório de Sobrevivência
        normal_period = state_df.filter(pl.col("regime_toxic") == 0)
        toxic_period = state_df.filter(pl.col("regime_toxic") == 1)
        
        print(f"Regime ESTÁVEL: n={len(normal_period)} | Net Alpha: {normal_period['net_alpha_stressed'].mean():.2f} bps")
        print(f"Regime TÓXICO:  n={len(toxic_period)}  | Net Alpha: {toxic_period['net_alpha_stressed'].mean():.2f} bps")
        
        # 4. Bayesian Position Sizing (Confidence Factor)
        # Confidence = 1 - P(Toxic)
        # Vamos usar as probabilidades do GMM
        probs = gmm.predict_proba(features)[:, 1 - toxic_state] # Probabilidade de ser Estável
        state_df = state_df.with_columns([
            pl.Series(name="confidence", values=probs)
        ])
        
        print("\n--- BAYESIAN CONFIDENCE SIZING ---")
        # Se operarmos apenas com confiança > 0.7
        confident_df = state_df.filter(pl.col("confidence") > 0.7)
        print(f"Confiança > 0.7: n={len(confident_df)} | Net Alpha: {confident_df['net_alpha_stressed'].mean():.2f} bps")
        
        return state_df

if __name__ == "__main__":
    auditor = StressAuditor(asset="WDO", tf="5")
    df = auditor.load_data()
    auditor.run_stress_audit(df)
