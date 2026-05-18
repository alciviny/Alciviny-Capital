import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.microstructure import add_microstructure_indicators, FlowState

class InstitutionalValidator:
    def __init__(self, base_path: str = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"):
        self.base_path = base_path
        self.assets = ["WIN", "WDO", "DI1"]
        self.timeframes = ["5", "15", "60"]
        self.cost_bps = 0.5 # Conservador: 0.5 bps por entrada

    def load_and_prepare(self, asset: str, tf: str) -> pl.DataFrame:
        file_path = os.path.join(self.base_path, f"{asset}$_{tf}_CLEAN.parquet")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.base_path, f"{asset}$_{tf}.parquet")
        
        if not os.path.exists(file_path):
            return None
            
        df = pl.read_parquet(file_path)
        # Garantir colunas básicas
        if "close" not in df.columns: return None
        
        df = add_microstructure_indicators(df)
        return df

    def run_alpha_decay_test(self, df: pl.DataFrame, state: FlowState) -> Dict[int, float]:
        """
        Mede o Alpha Decay: E[R | State] para múltiplos horizontes.
        """
        horizons = [1, 2, 3, 5, 10, 20, 50]
        decay = {}
        
        for h in horizons:
            fwd_ret = (pl.col("close").shift(-h) / pl.col("close") - 1)
            state_df = df.filter(pl.col("flow_state") == state.value)
            if len(state_df) < 10: 
                decay[h] = 0
                continue
                
            # Calcular retorno médio ponderado ( bps )
            avg_ret = state_df.select(fwd_ret.mean())[0,0]
            decay[h] = avg_ret * 10000
            
        return decay

    def run_volatility_neutralization(self, df: pl.DataFrame, state: FlowState) -> Dict[str, float]:
        """
        Provar que o sinal não é apenas vol disfarçada usando quintis de volatilidade.
        """
        # Calcular vol realizada (20 períodos)
        df = df.with_columns([
            (pl.col("close").log().diff().rolling_std(20) * np.sqrt(252 * 40)).alias("ann_vol")
        ]).drop_nulls()
        
        # Criar quintis de vol
        vol_values = df["ann_vol"].to_numpy()
        q_low, q_high = np.percentile(vol_values, [20, 80])
        
        # Medir edge em cada bucket
        buckets = {
            "low_vol": df.filter(pl.col("ann_vol") <= q_low),
            "med_vol": df.filter((pl.col("ann_vol") > q_low) & (pl.col("ann_vol") < q_high)),
            "high_vol": df.filter(pl.col("ann_vol") >= q_high)
        }
        
        results = {}
        for b_name, b_df in buckets.items():
            state_df = b_df.filter(pl.col("flow_state") == state.value)
            if len(state_df) < 5:
                results[b_name] = 0
            else:
                fwd_ret = (pl.col("close").shift(-5) / pl.col("close") - 1).mean()
                results[b_name] = state_df.select(fwd_ret)[0,0] * 10000
                
        return results

    def full_audit(self):
        print(f"[{datetime.now()}] Iniciando Auditoria Institucional Global...")
        report = []

        for asset in self.assets:
            for tf in self.timeframes:
                print(f"Auditando {asset} {tf}m...")
                df = self.load_and_prepare(asset, tf)
                if df is None: continue
                
                # Testar apenas estados institucionais críticos
                critical_states = [
                    FlowState.ABSORPTION_BULLISH,
                    FlowState.ABSORPTION_BEARISH,
                    FlowState.TRAPPED_BUYERS,
                    FlowState.TRAPPED_SELLERS
                ]
                
                for state in critical_states:
                    decay = self.run_alpha_decay_test(df, state)
                    vol_results = self.run_volatility_neutralization(df, state)
                    
                    report.append({
                        "asset": asset,
                        "tf": tf,
                        "state": state.name,
                        "decay_h5": decay.get(5, 0),
                        "decay_h20": decay.get(20, 0),
                        "low_vol_edge": vol_results.get("low_vol", 0),
                        "med_vol_edge": vol_results.get("med_vol", 0),
                        "high_vol_edge": vol_results.get("high_vol", 0),
                    })

        report_df = pd.DataFrame(report)
        print("\n--- RELATÓRIO DE ROBUSTEZ GLOBAL (Retorno em BPS) ---")
        print(report_df.to_string(index=False))
        
        # Salvar para análise posterior
        report_df.to_csv(r"c:\Users\JC INFO\Documents\AlcivinyEdger\research\experiments\exp_001_institutional_core\global_validation_report.csv")
        return report_df

if __name__ == "__main__":
    validator = InstitutionalValidator()
    validator.full_audit()
