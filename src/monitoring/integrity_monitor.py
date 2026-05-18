import os
import sys
import numpy as np
import polars as pl
from datetime import datetime
from typing import Dict, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ProductionIntegrityMonitor:
    """
    Monitor de Integridade de Dados em Produo.
    Detecta anomalias de infraestrutura antes que elas corrompam o alpha.
    """
    def __init__(self, drift_threshold_ms: int = 500):
        self.drift_threshold_ms = drift_threshold_ms

    def audit_feed_health(self, tick_df: pl.DataFrame):
        print("\n--- PRODUCTION INTEGRITY AUDIT ---")
        
        # 1. Timestamp Drift Detection
        # Assume 'exchange_time' and 'local_time' are present
        if "exchange_time" in tick_df.columns and "local_time" in tick_df.columns:
            drift = (tick_df["local_time"] - tick_df["exchange_time"]).mean()
            print(f"Average Timestamp Drift: {drift:.2f} ms")
            if drift > self.drift_threshold_ms:
                print("WARNING: HIGH LATENCY DRIFT. Sincronizao de fluxo comprometida.")
        
        # 2. Sequence Gap Detection (Missing Ticks)
        if "seq_num" in tick_df.columns:
            gaps = tick_df["seq_num"].diff().filter(pl.col("seq_num") > 1).len()
            print(f"Sequence Gaps Detected: {gaps}")
            
        # 3. Spread Anomaly Detection
        if "bid" in tick_df.columns and "ask" in tick_df.columns:
            spread = tick_df["ask"] - tick_df["bid"]
            avg_spread = spread.mean()
            std_spread = spread.std()
            curr_spread = spread.last()
            
            z_score = (curr_spread - avg_spread) / (std_spread + 1e-9)
            print(f"Spread Z-Score: {z_score:.2f} (Current: {curr_spread})")
            
            if z_score > 3.0:
                print("WARNING: LIQUIDITY COLLAPSE. Spread fora da banda estatstica.")

class StrategyKillSwitch:
    """
    Protocolo Hard de Risco e Invalidao.
    Define os 'Kill Criteria' institucionais.
    """
    def __init__(self):
        self.status = "OPERATIONAL"

    def check_gates(self, metrics: Dict[str, float]):
        print("\n--- STRATEGY KILL-SWITCH STATUS ---")
        
        # 1. Entropy Gate (Incerteza do HMM)
        if metrics.get("regime_entropy", 0) > 0.8:
            print("ALERT: REGIME ENTROPY HIGH. Modelo sem separabilidade. SUSPENDING.")
            self.status = "SUSPENDED"
            
        # 2. PSI Breaker (Feature Drift)
        if metrics.get("feature_psi", 0) > 0.25:
            print("ALERT: FEATURE DRIFT DETECTED (PSI > 0.25). RETRAIN MANDATORY.")
            self.status = "RETRAIN_REQUIRED"
            
        # 3. Execution Degradation (Slippage Percentile)
        if metrics.get("realized_slippage_percentile", 0) > 95:
            print("ALERT: SLIPPAGE EXPLOSION. Adverse selection acima do limite histrico.")
            self.status = "REDUCE_SIZE"
            
        # 4. Alpha Decay (Rolling Sharpe)
        if metrics.get("rolling_sharpe", 0) < 0.1:
            print("ALERT: ALPHA DECAY. Invalidao estatstica da estratgia.")
            self.status = "INVALIDATED"

        print(f"FINAL STATUS: {self.status}")
        return self.status

if __name__ == "__main__":
    monitor = ProductionIntegrityMonitor()
    # Simular tick data
    ticks = pl.DataFrame({
        "bid": [10.5] * 10,
        "ask": [11.0] * 10,
        "exchange_time": [1000, 1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080, 1090],
        "local_time": [1050, 1060, 1070, 1080, 1090, 1100, 1110, 1120, 1130, 1140]
    })
    monitor.audit_feed_health(ticks)
    
    ks = StrategyKillSwitch()
    ks.check_gates({"regime_entropy": 0.4, "feature_psi": 0.1, "realized_slippage_percentile": 96})
