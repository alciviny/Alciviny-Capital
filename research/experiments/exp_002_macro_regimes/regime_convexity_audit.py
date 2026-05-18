import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from typing import List, Dict, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.models.macro_regime_detector import MacroRegimeDetector
from research.experiments.exp_002_macro_regimes.regime_persistence_audit import MacroRegimeResearcher

class RegimeConvexityAuditor:
    """
    Auditor de Convexidade e Fragilidade de Recalibrao.
    Investiga se o overlay remove o upside de crise e mede o churn operacional.
    """
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def run_convexity_audit(self, states: np.ndarray, strategy_ret: np.ndarray, adaptive_ret: np.ndarray):
        print("\n--- CRISIS CONVEXITY AUDIT ---")
        
        # Identificar percentis extremos dos retornos da estratgia
        p5_worst = np.percentile(strategy_ret, 5)
        p95_best = np.percentile(strategy_ret, 95)
        
        worst_mask = strategy_ret <= p5_worst
        best_mask = strategy_ret >= p95_best
        
        # Captura de Downside e Upside
        loss_avoided = np.mean(strategy_ret[worst_mask]) - np.mean(adaptive_ret[worst_mask])
        gain_lost = np.mean(strategy_ret[best_mask]) - np.mean(adaptive_ret[best_mask])
        
        print(f"Downside Avoided (Worst 5%): {loss_avoided:.2f} bps per trade")
        print(f"Upside Lost (Best 5%):      {gain_lost:.2f} bps per trade")
        
        convexity_ratio = loss_avoided / (gain_lost + 1e-9)
        print(f"CONVEXITY RATIO: {convexity_ratio:.2f}")
        
        if convexity_ratio > 1.2:
            print("STATUS: POSITIVE CONVEXITY. O overlay protege mais do que limita.")
        elif convexity_ratio < 0.8:
            print("STATUS: NEGATIVE CONVEXITY. O overlay est cortando o seu alpha de crise.")
        else:
            print("STATUS: NEUTRAL. O overlay apenas escala o risco linearmente.")

    def run_turnover_audit(self, adaptive_sizing: np.ndarray):
        print("\n--- RISK OVERLAY TURNOVER AUDIT ---")
        
        # Mudanas de sizing entre candles
        changes = np.diff(adaptive_sizing) != 0
        n_changes = np.sum(changes)
        turnover_rate = n_changes / len(adaptive_sizing)
        
        print(f"Total Resizing Events: {n_changes} in {len(adaptive_sizing)} samples")
        print(f"Turnover Rate per Sample: {turnover_rate * 100:.2f}%")
        
        # Annualized Churn (8h/dia * 252 dias)
        annual_churn = turnover_rate * 8 * 252
        print(f"Estimated Annual Resizing Churn: {annual_churn:.2f} events")
        
        if annual_churn > 500:
            print("STATUS: HYPERACTIVE OVERLAY. Risco de 'Execution Tax Machine'.")
        else:
            print("STATUS: STABLE OVERLAY. Churn operacional aceitvel.")

    def run_recalibration_audit(self):
        print("\n--- RECALIBRATION FRAGILITY AUDIT ---")
        
        # Testar frequencias (Semanal, Quinzenal, Mensal)
        # 1h bars: 40h/semana, 80h/quinzena, 160h/mes
        for freq_label, window in [("Weekly", 40), ("Bi-Weekly", 80), ("Monthly", 160)]:
            errors = []
            for i in range(window, len(self.df) - window, window):
                # Treinar em T, testar estabilidade em T+1
                df_t = self.df.slice(i - window, window)
                df_t1 = self.df.slice(i, window)
                
                det = MacroRegimeDetector(n_states=3)
                det.fit(df_t)
                tm_t = det.get_transition_matrix()
                
                det.fit(df_t1)
                tm_t1 = det.get_transition_matrix()
                
                errors.append(np.mean(np.abs(tm_t - tm_t1)))
                
            print(f"{freq_label:10} | TM Stability Error: {np.mean(errors):.4f}")

if __name__ == "__main__":
    researcher = MacroRegimeResearcher()
    df = researcher.load_and_aggregate()
    
    # 1. Simular o sistema para obter retornos
    detector = MacroRegimeDetector(n_states=3)
    detector.fit(df)
    states = detector.predict(df)
    
    fwd_ret = (df["price"].shift(-1) / df["price"] - 1).fill_null(0).to_numpy() * 10000
    signals = np.sign(df["price"].pct_change(5).fill_null(0).to_numpy())
    strategy_ret = signals * fwd_ret
    
    # Sizing simplificado para o auditor
    regime_vols = [df.filter(pl.Series(states) == s)["vol_realized"].mean() for s in range(3)]
    weights = 1.0 / (np.array(regime_vols) + 1e-9)
    weights = weights / np.max(weights)
    adaptive_sizing = np.array([weights[s] for s in states])
    adaptive_ret = strategy_ret * adaptive_sizing
    
    auditor = RegimeConvexityAuditor(df)
    auditor.run_convexity_audit(states, strategy_ret, adaptive_ret)
    auditor.run_turnover_audit(adaptive_sizing)
    auditor.run_recalibration_audit()
