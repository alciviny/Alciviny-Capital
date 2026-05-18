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

class ExecutionSimulator:
    """
    Simulador de Execução Institucional de Alta Fidelidade.
    Modela Adverse Selection, Queue Priority e Fill Uncertainty.
    """
    def __init__(self, asset: str = "WDO", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        
        if asset == "WDO":
            self.tick_size = 0.5
            self.contract_value = 10.0
            self.fee_per_contract = 1.10
            self.avg_spread_ticks = 1.0 # Dólar costuma ter spread de 1-2 ticks
        else:
            self.tick_size = 5.0
            self.contract_value = 0.2
            self.fee_per_contract = 0.25
            self.avg_spread_ticks = 1.0

    def load_data(self) -> pl.DataFrame:
        clean_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}_CLEAN.parquet")
        base_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        path = clean_path if os.path.exists(clean_path) else base_path
        
        df = pl.read_parquet(path)
        df = add_microstructure_indicators(df)
        return df

    def run_simulation(self, df: pl.DataFrame, size: int = 50):
        print(f"\n--- EXECUTION SIMULATION RESEARCH: {self.asset} {self.tf}m (Size: {size}) ---")
        
        # 1. Preparação
        target_state = FlowState.TRAPPED_BUYERS
        state_df = df.filter(pl.col("flow_state") == target_state.value).drop_nulls()
        
        if len(state_df) < 20: return None

        # 2. Modelagem de Adverse Selection
        # Se o preço cai IMEDIATAMENTE após a entrada (t+1) e o sinal é SHORT, 
        # isso é bom. Se sobe, é Adverse Selection (toxicidade).
        # Vamos medir o "Toxic Momentum" (t a t+1)
        state_df = state_df.with_columns([
            (pl.col("close").shift(-1) / pl.col("close") - 1).alias("toxic_mom")
        ])
        
        # 3. Modelagem de Custos e Fricção
        avg_price = state_df["close"].mean()
        fee_bps = (self.fee_per_contract / (avg_price * self.contract_value)) * 10000
        
        # 4. Cenários de Execução
        results = []
        
        # Cenário A: AGGRESSIVE (Market Order)
        # Paga spread + Slippage + Impacto
        spread_bps = (self.avg_spread_ticks * self.tick_size / avg_price) * 10000
        impact_bps = 0.5 * (size / 100.0) # Simplificação: 0.5 bps para cada 100 contratos (mais severo que sqrt)
        
        gross_ret = (pl.col("close").shift(-5) / pl.col("close") - 1) * -1 * 10000
        
        # Adverse Selection Loss: Se o momentum t+1 é contra nós, perdemos timing.
        # Se toxic_mom > 0 (em um Short), perdemos.
        adverse_selection_loss = pl.col("toxic_mom").clip(lower_bound=0) * 10000 
        
        net_agg = gross_ret - fee_bps - spread_bps - impact_bps - (0.3 * adverse_selection_loss)
        
        # Cenário B: PASSIVE (Limit Order)
        # Ganha o spread, mas tem risco de "Missed Fill"
        # Probabilidade de execução = 1 - (Momentum_Alpha / Sigma)
        # Se o mercado foge rápido demais, a limit não pega.
        fill_prob = 0.65 # Estimativa conservadora para eventos microestruturais
        net_pass = (gross_ret + spread_bps - fee_bps - (0.1 * impact_bps)) * fill_prob
        
        # Cenário C: HYBRID (Cross the spread if alpha is high)
        # Implementaremos via cálculo simples
        
        metrics = {
            "Cenário": ["Aggressive (Market)", "Passive (Limit)"],
            "Net Alpha (bps)": [
                state_df.select(net_agg.mean())[0,0],
                state_df.select(net_pass.mean())[0,0]
            ],
            "Adverse Selection Impact (bps)": [
                state_df.select(adverse_selection_loss.mean())[0,0] * 0.3,
                0 # Passive sofre menos adverse imediato (ou vira missed fill)
            ],
            "Fill Rate (%)": [100.0, fill_prob * 100.0],
            "Effective Cost (bps)": [
                fee_bps + spread_bps + impact_bps,
                fee_bps - spread_bps
            ]
        }
        
        res_df = pd.DataFrame(metrics)
        print(res_df.to_string(index=False))
        return res_df

if __name__ == "__main__":
    sim = ExecutionSimulator(asset="WDO", tf="5")
    df = sim.load_data()
    res = sim.run_simulation(df, size=100)
    
    # Repetir para WIN
    print("\n" + "="*50 + "\n")
    sim_win = ExecutionSimulator(asset="WIN", tf="5")
    df_win = sim_win.load_data()
    res_win = sim_win.run_simulation(df_win, size=100)
