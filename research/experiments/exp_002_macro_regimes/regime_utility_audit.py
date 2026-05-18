import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from typing import List, Dict, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.models.macro_regime_detector import MacroRegimeDetector
from research.experiments.exp_002_macro_regimes.regime_persistence_audit import MacroRegimeResearcher

class RegimeUtilityAuditor:
    """
    Auditor de Utilidade e Ganho Informacional dos Regimes.
    Desafia a redundância e a validade preditiva do HMM.
    """
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def run_cardinality_audit(self):
        print("\n--- REGIME CARDINALITY AUDIT (BIC Analysis) ---")
        results = []
        for n in [2, 3, 4, 5]:
            detector = MacroRegimeDetector(n_states=n)
            X = detector.prepare_features(self.df)
            detector.model.fit(X)
            bic = detector.model.bic(X)
            results.append({"n_states": n, "BIC": bic})
            print(f"States: {n} | BIC: {bic:.2f}")
        
        best_n = min(results, key=lambda x: x["BIC"])["n_states"]
        print(f"MELHOR CARDINALIDADE (Min BIC): {best_n}")
        return best_n

    def run_information_gain_audit(self, n_states: int):
        print(f"\n--- REGIME INFORMATION GAIN AUDIT (n={n_states}) ---")
        
        detector = MacroRegimeDetector(n_states=n_states)
        detector.fit(self.df)
        states = detector.predict(self.df)
        
        # Alvo: Volatilidade Futura (t+1) - O que regimes deveriam prever
        target = self.df["vol_realized"].shift(-1).fill_null(strategy="forward").to_numpy()
        features = ["vol_realized", "dcc_proxy", "ofi_agg", "hurst", "vpin_smooth"]
        X_base = self.df.select(features).to_numpy()
        X_regime = np.column_stack([X_base, states])
        
        # Split (70/30)
        split_idx = int(len(target) * 0.7)
        
        # 1. Baseline Model (Sem Regime)
        reg_base = Ridge()
        reg_base.fit(X_base[:split_idx], target[:split_idx])
        pred_base = reg_base.predict(X_base[split_idx:])
        r2_base = r2_score(target[split_idx:], pred_base)
        
        # 2. Augmented Model (Com Regime)
        reg_aug = Ridge()
        reg_aug.fit(X_regime[:split_idx], target[:split_idx])
        pred_aug = reg_aug.predict(X_regime[split_idx:])
        r2_aug = r2_score(target[split_idx:], pred_aug)
        
        print(f"R2 Baseline (Sem Regime): {r2_base:.4f}")
        print(f"R2 Augmented (Com Regime): {r2_aug:.4f}")
        
        gain = (r2_aug - r2_base) if r2_base > 0 else (r2_aug)
        print(f"Ganho de Informação Incremental: {gain:.4f}")
        
        if gain <= 0:
            print("STATUS: REGIME REDUNDANTE (Narrativa apenas).")
        else:
            print("STATUS: REGIME ÚTIL (Adiciona valor preditivo).")

    def run_orthogonality_check(self, n_states: int):
        print(f"\n--- REGIME ORTHOGONALITY CHECK ---")
        detector = MacroRegimeDetector(n_states=n_states)
        detector.fit(self.df)
        states = detector.predict(self.df)
        
        # Correlação entre o estado do regime e a volatilidade realizada
        corr = np.corrcoef(states, self.df["vol_realized"].to_numpy())[0,1]
        print(f"Correlação Regime ID vs Realized Vol: {corr:.4f}")
        
        if abs(corr) > 0.8:
            print("STATUS: PROXY DE VOLATILIDADE. O HMM está apenas renomeando a vol.")
        else:
            print("STATUS: ESTRUTURAL. O regime captura dinâmicas além da vol pura.")

if __name__ == "__main__":
    researcher = MacroRegimeResearcher()
    df = researcher.load_and_aggregate()
    
    auditor = RegimeUtilityAuditor(df)
    best_n = auditor.run_cardinality_audit()
    auditor.run_information_gain_audit(best_n)
    auditor.run_orthogonality_check(best_n)
