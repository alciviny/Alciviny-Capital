from src.backtest.validation.base import BaseValidator
import polars as pl
from typing import Any, List, Dict
import numpy as np

class WalkForwardValidator(BaseValidator):
    """
    Análise de Walk-Forward (WFA) Industrial.
    Valida a estratégia comparando a performance esperada (IS) com a real (OOS).
    """
    def __init__(self, engine: Any, n_windows: int = 5, oos_ratio: float = 0.2):
        super().__init__(engine)
        self.n_windows = n_windows
        self.oos_ratio = oos_ratio

    def run(self, data: pl.DataFrame, strategy: Any) -> Dict[str, Any]:
        """
        Executa janelas deslizantes de Treino (IS) e Teste (OOS).
        """
        total_rows = data.height
        window_size = total_rows // self.n_windows
        oos_size = int(window_size * self.oos_ratio)
        is_size = window_size - oos_size
        
        oos_pfs = []
        is_pfs = []
        
        for i in range(self.n_windows):
            start = i * window_size
            if start + window_size > total_rows: break
            
            # Dados de In-Sample (Onde a estratégia deveria ter sido "calibrada")
            is_data = data.slice(start, is_size)
            # Dados de Out-of-Sample (Onde o lucro real acontece)
            oos_data = data.slice(start + is_size, oos_size)
            
            is_metrics = self.engine.run(is_data, strategy)
            oos_metrics = self.engine.run(oos_data, strategy)
            
            # Limitar PF para evitar 'inf' que quebra as médias
            is_pfs.append(min(is_metrics["profit_factor"], 10.0))
            oos_pfs.append(min(oos_metrics["profit_factor"], 10.0))

        # Walk-Forward Efficiency (WFE)
        # WFE = Avg(OOS PF) / Avg(IS PF)
        avg_is = np.mean(is_pfs)
        avg_oos = np.mean(oos_pfs)
        wfe = (avg_oos / avg_is) if avg_is > 0 else 0.0
        
        return {
            "avg_is_pf": avg_is,
            "avg_oos_pf": avg_oos,
            "wfe": wfe,
            "consistency": (np.array(oos_pfs) > 1.0).sum() / len(oos_pfs)
        }

    def get_verdict(self, results: Dict[str, Any]) -> bool:
        # Padrão Industrial: WFE > 0.5 e OOS PF médio > 1.0
        return results["wfe"] >= 0.5 and results["avg_oos_pf"] > 1.0
