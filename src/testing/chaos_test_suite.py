import os
import sys
import polars as pl
import numpy as np
import time

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.monitoring.integrity_monitor import ProductionIntegrityMonitor, StrategyKillSwitch

class ChaosEngine:
    """
    Motor de Engenharia de Caos.
    Ataca o sistema para validar a resilincia dos Kill-Switches.
    """
    def __init__(self, monitor: ProductionIntegrityMonitor, kill_switch: StrategyKillSwitch):
        self.monitor = monitor
        self.kill_switch = kill_switch

    def run_latency_attack(self):
        print("\n--- ATTACK: LATENCY DRIFT INJECTION ---")
        # Simular delay de 1.5 segundos entre Exchange e Local
        now = int(time.time() * 1000)
        df = pl.DataFrame({
            "exchange_time": [now - 1500] * 10,
            "local_time": [now] * 10
        })
        self.monitor.audit_feed_health(df)

    def run_spread_explosion(self):
        print("\n--- ATTACK: LIQUIDITY HOLE (SPREAD EXPLOSION) ---")
        # Simular spread de 50 pontos (Z-Score alto)
        df = pl.DataFrame({
            "bid": [10.0] * 20 + [5.0],
            "ask": [10.5] * 20 + [55.0]
        })
        self.monitor.audit_feed_health(df)

    def run_strategy_meltdown(self):
        print("\n--- ATTACK: STRATEGY PERFORMANCE COLLAPSE ---")
        # Forar kill-switch via métricas tóxicas
        metrics = {
            "regime_entropy": 0.95,        # Alta incerteza
            "feature_psi": 0.40,           # Drift estrutural
            "realized_slippage_percentile": 99, # Slippage insuportvel
            "rolling_sharpe": -0.5         # Perda de alpha
        }
        status = self.kill_switch.check_gates(metrics)
        print(f"CHAOS RESULT: {status}")

if __name__ == "__main__":
    monitor = ProductionIntegrityMonitor(drift_threshold_ms=500)
    kill_switch = StrategyKillSwitch()
    
    chaos = ChaosEngine(monitor, kill_switch)
    
    # 1. Atacar Infraestrutura
    chaos.run_latency_attack()
    chaos.run_spread_explosion()
    
    # 2. Atacar Estratégia
    chaos.run_strategy_meltdown()
