import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

class PurgedTimeSeriesSplit(TimeSeriesSplit):
    """
    Time Series Cross-Validation com Purging.
    Remove amostras do final do conjunto de treino que se sobrepõem ao início do teste.
    Crucial para labels baseados em janelas (ex: TBM, Forward Return).
    """
    def __init__(self, n_splits=5, purge_window=30):
        super().__init__(n_splits=n_splits)
        self.purge_window = purge_window

    def split(self, X, y=None, groups=None):
        """
        Gera índices de treino e teste com gap de segurança.
        """
        for train_idx, test_idx in super().split(X, y, groups):
            # O Purging acontece no final do conjunto de treinamento
            # Se o label olha 'horizon' candles para o futuro, 
            # os últimos 'horizon' candles do treino conhecem o futuro do teste.
            purged_train_idx = train_idx[:-self.purge_window]
            yield purged_train_idx, test_idx

def calculate_mda(model, X, y, cv, n_iterations=5):
    """
    Mean Decrease Accuracy (MDA) via Permutation Importance.
    Mede a queda de performance ao embaralhar cada feature individualmente.
    """
    from sklearn.metrics import accuracy_score
    
    baseline_scores = []
    feature_scores = {col: [] for col in X.columns}
    
    for train_idx, val_idx in cv.split(X):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        
        model.fit(X_train, y_train)
        baseline_acc = accuracy_score(y_val, model.predict(X_val))
        baseline_scores.append(baseline_acc)
        
        for col in X.columns:
            fold_permutations = []
            for _ in range(n_iterations):
                X_val_perm = X_val.copy()
                X_val_perm[col] = np.random.permutation(X_val_perm[col].values)
                perm_acc = accuracy_score(y_val, model.predict(X_val_perm))
                fold_permutations.append(baseline_acc - perm_acc)
            feature_scores[col].append(np.mean(fold_permutations))
            
    mda_results = {col: np.mean(scores) for col, scores in feature_scores.items()}
    return pd.Series(mda_results).sort_values(ascending=False)
