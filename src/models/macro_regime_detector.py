import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
from typing import Dict, List, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class MacroRegimeDetector:
    """
    Motor de Regimes Macro Baseado em HMM.
    Foca em persistência estrutural e transições de regime (1h-4h).
    """
    def __init__(self, n_states: int = 3, n_iter: int = 100):
        self.n_states = n_states
        self.model = GaussianHMM(n_components=n_states, covariance_type="diag", n_iter=n_iter, random_state=42)
        self.is_fitted = False

    def prepare_features(self, df: pl.DataFrame) -> np.ndarray:
        # Garantir que as features são robustas e normalizadas
        cols = ["vol_realized", "dcc_proxy", "ofi_agg", "hurst", "vpin_smooth"]
        data = df.select(cols).to_numpy()
        
        # Z-Score Normalization (crucial para HMM)
        means = np.nanmean(data, axis=0)
        stds = np.nanstd(data, axis=0)
        data = (data - means) / (stds + 1e-9)
        
        return np.nan_to_num(data)

    def fit(self, df: pl.DataFrame):
        X = self.prepare_features(df)
        self.model.fit(X)
        self.is_fitted = True

    def predict(self, df: pl.DataFrame) -> np.ndarray:
        X = self.prepare_features(df)
        return self.model.predict(X)

    def get_persistence_stats(self, states: np.ndarray) -> Dict[str, Any]:
        """
        Calcula a persistência média de cada regime.
        """
        persistence = []
        current_state = states[0]
        count = 0
        
        for s in states:
            if s == current_state:
                count += 1
            else:
                persistence.append((current_state, count))
                current_state = s
                count = 1
        persistence.append((current_state, count))
        
        # Agrupar por estado
        stats = {}
        for s in range(self.n_states):
            durations = [d for st, d in persistence if st == s]
            if durations:
                stats[f"regime_{s}_mean_duration"] = np.mean(durations)
                stats[f"regime_{s}_max_duration"] = np.max(durations)
                stats[f"regime_{s}_count"] = len(durations)
            else:
                stats[f"regime_{s}_mean_duration"] = 0
        
        return stats

    def get_transition_matrix(self) -> np.ndarray:
        return self.model.transmat_

if __name__ == "__main__":
    print("MacroRegimeDetector pronto para integração.")
