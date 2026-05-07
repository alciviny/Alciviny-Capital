from abc import ABC, abstractmethod
import polars as pl
from typing import Dict, Any, List

class BaseValidator(ABC):
    """
    Interface base para validadores de robustez.
    Cada validador deve retornar um dicionário de métricas e um 'score' de aprovação.
    """
    def __init__(self, engine: Any):
        self.engine = engine

    @abstractmethod
    def run(self, data: pl.DataFrame, strategy: Any) -> Dict[str, Any]:
        """
        Executa o teste de validação.
        """
        pass

    @abstractmethod
    def get_verdict(self, results: Dict[str, Any]) -> bool:
        """
        Decide se a estratégia passou neste teste específico.
        """
        pass
