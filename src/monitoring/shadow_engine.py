import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.indicators.microstructure import add_microstructure_indicators, FlowState
from src.indicators.vpin import add_vpin_to_state

class RiskGuard:
    """
    Motor de Risco de Produção.
    Atua como Kill-Switch baseado em condições de mercado anômalas.
    """
    def __init__(self):
        self.max_slippage_bps = 5.0
        self.max_spread_bps = 10.0
        self.vpin_threshold = 1.2e14 # Exemplo baseado na auditoria anterior
        
    def check_execution_risk(self, vpin: float, spread_bps: float) -> bool:
        if vpin > self.vpin_threshold: return False # Toxic Collapse
        if spread_bps > self.max_spread_bps: return False # Liquidity Gap
        return True

class ShadowEngine:
    """
    Simulador de Shadow Mode.
    Processa dados históricos como se estivessem chegando em tempo real.
    """
    def __init__(self, asset: str = "WDO", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.risk_guard = RiskGuard()
        self.logs = []

    def run_shadow_simulation(self, df: pl.DataFrame):
        print(f"\n--- SHADOW MODE DEPLOYMENT SIMULATION: {self.asset} ---")
        
        # 1. Preparação (Simular chegada de dados ponto a ponto)
        target_state = FlowState.TRAPPED_BUYERS
        
        # Filtramos apenas os eventos para agilizar a simulação, 
        # mas a lógica de monitoramento roda em "tempo real"
        events = df.filter(pl.col("flow_state") == target_state.value).to_dicts()
        
        for i, event in enumerate(events):
            # Simular Telemetria de Produção
            current_vpin = event["vpin"]
            current_spread = 1.2 # Placeholder para spread real-time
            
            # Risk Check
            is_allowed = self.risk_guard.check_execution_risk(current_vpin, current_spread)
            
            # Alpha Attribution Simulation
            # Aqui comparamos o Signal Alpha vs Realized Execution
            gross_alpha = (event["close_shift_5"] / event["close"] - 1) * -1 * 10000
            
            # Slippage Real-time (Simulado com base no VPIN)
            realized_slippage = 0.5 + (current_vpin / 1e14) * 2.0 
            
            if is_allowed:
                net_pnl = gross_alpha - realized_slippage - 0.3 # Fees
                status = "EXECUTED"
            else:
                net_pnl = 0.0
                status = "RISK_REJECTED"
            
            self.logs.append({
                "time": event["time"],
                "status": status,
                "vpin": current_vpin,
                "gross_alpha": gross_alpha,
                "net_pnl": net_pnl,
                "slippage": realized_slippage
            })

    def report_telemetry(self):
        log_df = pd.DataFrame(self.logs)
        print("\n--- PRODUCTION TELEMETRY REPORT ---")
        print(f"Total Signals: {len(log_df)}")
        print(f"Executed: {len(log_df[log_df['status'] == 'EXECUTED'])}")
        print(f"Rejected by Risk: {len(log_df[log_df['status'] == 'RISK_REJECTED'])}")
        
        if len(log_df[log_df['status'] == 'EXECUTED']) > 0:
            avg_pnl = log_df[log_df['status'] == 'EXECUTED']['net_pnl'].mean()
            avg_slip = log_df[log_df['status'] == 'EXECUTED']['slippage'].mean()
            print(f"Avg Realized PnL: {avg_pnl:.2f} bps")
            print(f"Avg Realized Slippage: {avg_slip:.2f} bps")
            
        return log_df

if __name__ == "__main__":
    # Carregar dados preparados com shift para simulação
    base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
    df = pl.read_parquet(os.path.join(base_path, "WDO$_5.parquet"))
    df = add_vpin_to_state(df)
    df = add_microstructure_indicators(df)
    
    # Criar alvos para simulação
    df = df.with_columns([
        pl.col("close").shift(-5).alias("close_shift_5")
    ]).drop_nulls()
    
    engine = ShadowEngine()
    engine.run_shadow_simulation(df)
    engine.report_telemetry()
