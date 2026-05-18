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

class ExecutionAuditor:
    def __init__(self, asset: str = "WIN", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        
        # Parâmetros de Custo Institucional
        if asset == "WIN":
            self.tick_size = 5.0
            self.contract_value = 0.2
            self.fee_per_contract = 0.25 # Estimativa B3 + Corretagem
        elif asset == "WDO":
            self.tick_size = 0.5
            self.contract_value = 10.0
            self.fee_per_contract = 1.10
        else:
            self.tick_size = 0.01
            self.contract_value = 1.0
            self.fee_per_contract = 0.01

    def load_data(self) -> pl.DataFrame:
        clean_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}_CLEAN.parquet")
        base_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        
        path = clean_path if os.path.exists(clean_path) else base_path
        if not os.path.exists(path):
            print(f"Erro: Arquivo {path} não encontrado.")
            return None
            
        df = pl.read_parquet(path)
        df = add_microstructure_indicators(df)
        return df

    def run_net_alpha_audit(self, df: pl.DataFrame):
        """
        Calcula o Alpha Líquido após custos e latência.
        """
        print(f"\n--- AUDITORIA DE EXECUÇÃO: {self.asset} {self.tf}m ---")
        
        # Horizontes de saída
        horizons = [1, 3, 5, 10]
        # Cenários de Slippage (em ticks)
        slippage_scenarios = [0, 0.5, 1.0, 2.0]
        # Cenários de Delay (em candles)
        delays = [0, 1, 2]

        results = []
        states = [FlowState.ABSORPTION_BULLISH, FlowState.TRAPPED_BUYERS]
        
        for state in states:
            state_df = df.filter(pl.col("flow_state") == state.value)
            if len(state_df) < 20: continue
            
            for delay in delays:
                for slippage_ticks in slippage_scenarios:
                    for h in horizons:
                        # 1. Simulação de Entrada com Delay
                        # O retorno é do momento (t + delay) até (t + delay + h)
                        # Mas o slippage é aplicado no momento da entrada (t + delay)
                        
                        entry_price = pl.col("close").shift(-delay)
                        exit_price = pl.col("close").shift(-(delay + h))
                        
                        # Aplicar Slippage no preço de entrada (Piorar o preço)
                        # Se é BUY (Absorption Bullish), preço de entrada sobe
                        # Se é SELL (Trapped Buyers), preço de entrada desce
                        side = 1 if "BULLISH" in state.name or "SELLERS" in state.name else -1
                        
                        slippage_val = slippage_ticks * self.tick_size
                        effective_entry = entry_price + (side * slippage_val)
                        
                        # Retorno Bruto (bps)
                        gross_ret = (exit_price / entry_price - 1) * side * 10000
                        
                        # Retorno Líquido (bps)
                        # (Exit - Entry_eff) / Entry_eff
                        net_ret = (exit_price / effective_entry - 1) * side * 10000
                        
                        # Subtrair Taxas (bps aproximado)
                        # Taxa por contrato / (Preço * Valor Contrato)
                        avg_price = df["close"].mean()
                        fee_bps = (self.fee_per_contract / (avg_price * self.contract_value)) * 10000
                        net_ret = net_ret - fee_bps

                        results.append({
                            "state": state.name,
                            "delay": delay,
                            "slippage_ticks": slippage_ticks,
                            "horizon": h,
                            "gross_bps": state_df.select(gross_ret.mean())[0,0],
                            "net_bps": state_df.select(net_ret.mean())[0,0],
                            "n": len(state_df)
                        })

        res_df = pd.DataFrame(results)
        return res_df

    def audit_report(self, res_df: pd.DataFrame):
        print("\n--- TRADABLE ALPHA ANALYSIS ---")
        
        # 1. Survival Analysis: Alpha Net vs Slippage (H5, Delay 0)
        survival = res_df[(res_df["horizon"] == 5) & (res_df["delay"] == 0)]
        print("\nSlippage Sensitivity (H5, Delay 0):")
        print(survival.pivot(index="state", columns="slippage_ticks", values="net_bps"))

        # 2. Latency Analysis: Alpha Net vs Delay (Slippage 0.5, H5)
        latency = res_df[(res_df["horizon"] == 5) & (res_df["slippage_ticks"] == 0.5)]
        print("\nLatency Sensitivity (Slippage 0.5, H5):")
        print(latency.pivot(index="state", columns="delay", values="net_bps"))

        # 3. Decision Point
        for state in res_df["state"].unique():
            max_net = res_df[res_df["state"] == state]["net_bps"].max()
            if max_net < 0:
                print(f"AVISO: {state} eh ECONOMICAMENTE INVIAVEL (Alpha Net Negativo em todos os cenarios)")
            elif max_net < 5:
                print(f"AVISO: {state} eh MARGINAL (Alpha Net < 5bps). Risco de execucao alto.")
            else:
                print(f"OK: {state} eh TRADABLE (Max Net Alpha: {max_net:.2f} bps)")

if __name__ == "__main__":
    auditor = ExecutionAuditor(asset="WIN", tf="5")
    df = auditor.load_data()
    results = auditor.run_net_alpha_audit(df)
    auditor.audit_report(results)
    
    # Repetir para WDO
    print("\n" + "="*50 + "\n")
    auditor_wdo = ExecutionAuditor(asset="WDO", tf="5")
    df_wdo = auditor_wdo.load_data()
    results_wdo = auditor_wdo.run_net_alpha_audit(df_wdo)
    auditor_wdo.audit_report(results_wdo)
