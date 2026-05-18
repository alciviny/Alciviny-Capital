import xgboost as xgb
import pandas as pd
import numpy as np
import joblib
import os
from typing import List, Optional, Dict
from sklearn.calibration import CalibratedClassifierCV

class InstitutionalClassifier:
    """
    Meta-Classificador Baseado em XGBoost.
    Traduz o State Vector em probabilidades contínuas de regime.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def train(self, 
              X: pd.DataFrame, 
              y: pd.Series, 
              sample_weights: Optional[pd.Series] = None):
        """
        Treina o meta-classificador.
        
        Args:
            X: DataFrame com o State Vector.
            y: Labels de regime (0: Bear/Crisis, 1: Bull, etc).
            sample_weights: Pesos para lidar com labels ambíguos (híbridos).
        """
        # 1. Base Model com Regularização Forte
        unique_classes = np.unique(y)
        num_classes = len(unique_classes)
        objective = 'binary:logistic' if num_classes <= 2 else 'multi:softprob'
        
        base_model = xgb.XGBClassifier(
            objective=objective,
            n_estimators=100,
            max_depth=3,
            learning_rate=0.03,
            reg_lambda=15.0,
            reg_alpha=10.0,
            subsample=0.6,
            colsample_bytree=0.6,
            random_state=42
        )
        
        if num_classes > 2:
            base_model.set_params(num_class=num_classes)
        
        # 2. Calibration Layer (Isotonic para datasets > 1000 amostras)
        # Prevenimos leakage usando cv='prefit' se tivéssemos validação separada, 
        # mas aqui usamos 3-fold CV interno para calibração.
        self.model = CalibratedClassifierCV(
            base_model, 
            method='isotonic', 
            cv=3
        )
        
        self.model.fit(X, y, sample_weight=sample_weights)
        
        if self.model_path:
            self.save(self.model_path)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Retorna probabilidades contínuas para cada regime."""
        if self.model is None:
            raise RuntimeError("Modelo não treinado ou carregado.")
        return self.model.predict_proba(X)

    def predict_with_uncertainty(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Retorna a probabilidade média e o desvio padrão (incerteza) entre os modelos do ensemble.
        Apenas disponível se o CalibratedClassifierCV foi treinado com CV > 1.
        """
        if not hasattr(self.model, 'calibrated_classifiers_'):
            # Fallback se não for ensemble
            probs = self.predict_proba(X)
            return {"mean": probs, "std": np.zeros_like(probs)}
            
        # Coletar predições de todos os modelos calibrados no ensemble
        all_probs = np.array([clf.predict_proba(X) for clf in self.model.calibrated_classifiers_])
        
        return {
            "mean": np.mean(all_probs, axis=0),
            "std": np.std(all_probs, axis=0)
        }

    def get_feature_importance(self, feature_names: List[str]) -> Dict[str, float]:
        """Extrai importância das features do modelo base dentro do CalibratedClassifierCV."""
        if self.model is None:
            return {}
            
        # O CalibratedClassifierCV encapsula o modelo base em .base_estimator ou .calibrated_classifiers_
        if hasattr(self.model, 'calibrated_classifiers_'):
            # Média da importância em todos os classificadores do ensemble
            importances = np.mean([
                clf.estimator.feature_importances_ for clf in self.model.calibrated_classifiers_
            ], axis=0)
        else:
            importances = self.model.feature_importances_
            
        return dict(zip(feature_names, importances))

    def save(self, path: str):
        joblib.dump(self.model, path)

    def load(self, path: str):
        self.model = joblib.load(path)
