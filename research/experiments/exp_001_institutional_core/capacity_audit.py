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

class CapacityAuditor:
    def __init__(self, asset: str = "WIN", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        
        # Parâmetros de Mercado
        if asset == "WIN":
            self.tick_size = 5.0
            self.contract_value = 0.2
            self.fee_per_contract = 0.25
            self.gamma = 0.6  # Fator de Impacto Institucional
        elif asset == "WDO":
            self.tick_size = 0.5
            self.contract_value = 10.0
            self.fee_per_contract = 1.10
            self.gamma = 0.4
        else:
            self.tick_size = 0.01
            self.contract_value = 1.0
            self.fee_per_contract = 0.01
            self.gamma = 0.5

    def load_data(self) -> pl.DataFrame:
        clean_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}_CLEAN.parquet")
        base_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        path = clean_path if os.path.exists(clean_path) else base_path
        
        df = pl.read_parquet(path)
        df = add_microstructure_indicators(df)
        
        # Calcular Volatilidade Local (Parkinson) para Impact Model
        const = 1.0 / (4.0 * np.log(2.0))
        log_hl = (pl.col("high") / (pl.col("low") + 1e-9)).log()
        df = df.with_columns([
            ((log_hl**2).rolling_mean(window_size=20).sqrt() * np.sqrt(const)).alias("local_vol")
        ])
        return df

    def run_capacity_audit(self, df: pl.DataFrame, sizes: List[int] = [1, 5, 10, 20, 50, 100, 200]):
        print(f"\n--- CAPACITY STRESS TEST: {self.asset} {self.tf}m ---")
        
        results = []
        target_state = FlowState.TRAPPED_BUYERS
        
        # Filtrar o estado alvo
        state_df = df.filter(pl.col("flow_state") == target_state.value).drop_nulls()
        if len(state_df) < 20:
            print("Amostra insuficiente para Capacity Audit.")
            return None

        # Cálculo de Custo Fixo (Fees) em bps
        avg_price = state_df["close"].mean()
        fee_bps = (self.fee_per_contract / (avg_price * self.contract_value)) * 10000

        # Definição de Side (Trapped Buyers = SELL = -1)
        side = -1 if "BUYERS" in target_state.name or "BULLISH" in target_state.name else 1
        
        for size in sizes:
            # Modelo de Impacto: I = gamma * sigma * sqrt(S / V)
            impact_expr = (
                pl.lit(self.gamma) * 
                pl.col("local_vol") * 
                (pl.lit(size) / (pl.col("volume") + 1e-9)).sqrt()
            ) * 10000
            
            # Retorno Bruto (h5)
            # Retorno = (Exit / Entry - 1) * side
            gross_ret_expr = (pl.col("close").shift(-5) / pl.col("close") - 1) * side * 10000
            
            # Retorno Líquido = Gross - Fees - Impact - Slippage(0.5 tick)
            slippage_bps = (0.5 * self.tick_size / avg_price) * 10000
            
            net_ret_expr = gross_ret_expr - fee_bps - impact_expr - slippage_bps
            
            avg_net = state_df.select(net_ret_expr.mean())[0,0]
            avg_impact = state_df.select(impact_expr.mean())[0,0]
            
            results.append({
                "size": size,
                "net_alpha_bps": avg_net,
                "market_impact_bps": avg_impact,
                "total_cost_bps": fee_bps + avg_impact + slippage_bps,
                "n": len(state_df)
            })
            
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))
        return res_df

    def capacity_report(self, res_df: pd.DataFrame):
        # Encontrar ponto de saturação (Net Alpha < 5 bps)
        saturation_point = res_df[res_df["net_alpha_bps"] < 5]
        if len(saturation_point) > 0:
            max_capacity = saturation_point.iloc[0]["size"]
            print(f"\nCAPACITY THRESHOLD: {max_capacity} contratos")
            print(f"Acima deste tamanho, o edge eh destruido pelo impacto de mercado.")
        else:
            print(f"\nCAPACITY THRESHOLD: > {res_df['size'].max()} contratos")

if __name__ == "__main__":
    # WIN
    auditor = CapacityAuditor(asset="WIN", tf="5")
    df = auditor.load_data()
    res = auditor.run_capacity_audit(df)
    if res is not None: auditor.capacity_report(res)
    
    # WDO
    print("\n" + "="*50 + "\n")
    auditor_wdo = CapacityAuditor(asset="WDO", tf="5")
    df_wdo = auditor_wdo.load_data()
    res_wdo = auditor_wdo.run_capacity_audit(df_wdo)
    if res_wdo is not None: auditor_wdo.capacity_report(res_wdo)
