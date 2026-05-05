import polars as pl
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Interface profissional para geração de sinais de trading.
    Toda nova estratégia deve herdar desta classe e implementar o método 'generate_signals'.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Recebe o DataFrame com OHLC e retorna o mesmo DataFrame 
        com colunas 'entry_buy' e 'entry_sell' (booleanas).
        """
        pass
