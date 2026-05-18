import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from typing import List, Dict, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.models.macro_regime_detector import MacroRegimeDetector
from research.experiments.exp_002_macro_regimes.regime_persistence_audit import MacroRegimeResearcher

class MacroRiskAuditor:
    """
    Auditor de Risco e Estrutura de Fatores Macro.
    Foca em compressão de informação e utilidade econômica dos regimes.
    """
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def run_pca_audit(self):
        print("\n--- MACRO FEATURE COMPRESSION (PCA Audit) ---")
        features = ["vol_realized", "dcc_proxy", "ofi_agg", "hurst", "vpin_smooth"]
        X = self.df.select(features).to_numpy()
        
        # Normalizar para PCA
        X_norm = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-9)
        
        pca = PCA()
        pca.fit(X_norm)
        
        explained_var = np.cumsum(pca.explained_variance_ratio_)
        print("Explained Variance Ratio (Cumulative):")
        for i, var in enumerate(explained_var):
            print(f"PC{i+1}: {var:.4f}")
            
        k_90 = np.where(explained_var >= 0.90)[0][0] + 1
        print(f"\nESTRUTURA LATENTE: 90% da variância explicada por {k_90} componentes de {len(features)}.")
        return k_90

    def run_risk_utility_audit(self):
        print("\n--- REGIME RISK UTILITY AUDIT ---")
        # 1. Gerar Regimes (3 estados para robustez)
        detector = MacroRegimeDetector(n_states=3)
        detector.fit(self.df)
        states = detector.predict(self.df)
        
        # 2. Simular Retornos de uma Estratégia Base (Ex: Momentum Simples)
        # Retorno do próximo candle de 1h
        fwd_ret = (self.df["price"].shift(-1) / self.df["price"] - 1).fill_null(0).to_numpy()
        
        # Sinais de Momentum (Proxy)
        signals = np.sign(self.df["price"].pct_change(5).fill_null(0).to_numpy())
        
        strategy_ret = signals * fwd_ret
        
        # 3. Comparar Sizing
        # Modelo A: Sizing Fixo (1.0)
        ret_fixed = strategy_ret
        
        # Modelo B: Sizing Adaptativo ao Regime (Inverse Volatility Proxy)
        # Vamos assumir que Regime 2 é Stress (Alta Vol), Regime 0 é Calmo
        regime_vols = []
        for s in range(3):
            regime_vols.append(self.df.filter(pl.Series(states) == s)["vol_realized"].mean())
        
        # Sizing = 1 / Vol do Regime
        weights = 1.0 / (np.array(regime_vols) + 1e-9)
        weights = weights / np.max(weights) # Normalizar para max 1.0
        
        adaptive_sizing = np.array([weights[s] for s in states])
        ret_adaptive = strategy_ret * adaptive_sizing
        
        # 4. Métricas de Risco
        def get_risk_metrics(rets):
            cum_ret = np.cumsum(rets)
            peak = np.maximum.accumulate(cum_ret)
            drawdown = peak - cum_ret
            max_dd = np.max(drawdown)
            sharpe = np.mean(rets) / (np.std(rets) + 1e-9) * np.sqrt(252 * 8) # Anualizado (8h dia)
            return sharpe, max_dd

        s_fixed, dd_fixed = get_risk_metrics(ret_fixed)
        s_adaptive, dd_adaptive = get_risk_metrics(ret_adaptive)
        
        print(f"BASELINE (Fixed Sizing): Sharpe: {s_fixed:.4f} | MaxDD: {dd_fixed:.4f}")
        print(f"ADAPTIVE (Regime Sizing): Sharpe: {s_adaptive:.4f} | MaxDD: {dd_adaptive:.4f}")
        
        improvement_sharpe = (s_adaptive / s_fixed - 1) * 100 if s_fixed != 0 else 0
        reduction_dd = (1 - dd_adaptive / dd_fixed) * 100 if dd_fixed != 0 else 0
        
        print(f"\nMELHORIA ECONÔMICA:")
        print(f"Sharpe Improvement: {improvement_sharpe:.2f}%")
        print(f"Drawdown Reduction: {reduction_dd:.2f}%")
        
        if reduction_dd > 10:
            print("STATUS: UTILIDADE ECONÔMICA VALIDADA. Regimes protegem a cauda.")
        else:
            print("STATUS: UTILIDADE MARGINAL. Regimes não adicionam segurança real.")

if __name__ == "__main__":
    researcher = MacroRegimeResearcher()
    df = researcher.load_and_aggregate()
    
    auditor = MacroRiskAuditor(df)
    auditor.run_pca_audit()
    auditor.run_risk_utility_audit()
