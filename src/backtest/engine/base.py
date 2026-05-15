from abc import ABC, abstractmethod
import polars as pl
from typing import Any, Dict

class BacktestEngine(ABC):
    """
    Interface base para motores de backtesting.
    Responsável por orquestrar dados, estratégia e risco.
    """
    
    @abstractmethod
    def run(self, data: pl.DataFrame, strategy: Any, risk_manager: Any) -> Dict[str, Any]:
        """
        Executa a simulação.
        """
        pass

    @abstractmethod
    def get_trades(self) -> pl.DataFrame:
        """
        Retorna o log de trades executados.
        """
        pass
