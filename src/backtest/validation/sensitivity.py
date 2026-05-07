from src.backtest.validation.base import BaseValidator
import polars as pl
from typing import Any, Dict, List
import numpy as np
import copy

class SensitivityValidator(BaseValidator):
    """
    Teste de Sensibilidade de Parâmetros.
    Verifica se a estratégia é robusta a pequenas variações nos parâmetros (Anti-Curve-Fitting).
    """
    def __init__(self, engine: Any, perturbation_pct: float = 0.05, n_iterations: int = 10):
        super().__init__(engine)
        self.perturbation_pct = perturbation_pct
        self.n_iterations = n_iterations

    def run(self, data: pl.DataFrame, strategy: Any) -> Dict[str, Any]:
        """
        Perturba os parâmetros numéricos da estratégia e mede a variação do Profit Factor.
        """
        base_params = strategy.get_parameters()
        base_metrics = self.engine.run(data, strategy)
        base_pf = base_metrics["profit_factor"]
        
        pfs = []
        
        for _ in range(self.n_iterations):
            # Criar uma cópia da estratégia com parâmetros perturbados
            perturbed_strategy = copy.deepcopy(strategy)
            
            for param, value in base_params.items():
                if isinstance(value, (int, float)) and param != "rsi_period": # RSI period deve ser int
                    noise = 1 + np.random.uniform(-self.perturbation_pct, self.perturbation_pct)
                    new_val = value * noise
                    setattr(perturbed_strategy, param, type(value)(new_val))
            
            try:
                metrics = self.engine.run(data, perturbed_strategy)
                pfs.append(metrics["profit_factor"])
            except Exception:
                pfs.append(0.0)

        pfs = np.array(pfs)
        stability_score = (pfs > 1.0).sum() / len(pfs)
        pf_variance = np.std(pfs) / base_pf if base_pf > 0 else 1.0

        return {
            "base_pf": base_pf,
            "mean_perturbed_pf": np.mean(pfs),
            "stability_score": stability_score,
            "pf_variance": pf_variance
        }

    def get_verdict(self, results: Dict[str, Any]) -> bool:
        # Padrão Industrial: Estabilidade > 70% e variância baixa
        return results["stability_score"] >= 0.7 and results["pf_variance"] < 0.3
