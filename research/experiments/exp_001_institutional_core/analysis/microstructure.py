import polars as pl
import numpy as np
from typing import List, Dict

class MicrostructureAnalyzer:
    """
    Análise de microestrutura de mercado: Lead-Lag e R² Intraday.
    Focado em identificar liderança entre ativos (ex: DI liderando WIN).
    """
    def __init__(self, window: int = 21):
        self.window = window

    def lead_lag_analysis(self, df: pl.DataFrame, target: str, leader: str, max_lag: int = 5) -> Dict[int, float]:
        """
        Calcula a correlação cruzada para identificar o lag de liderança.
        Um lag positivo alto sugere que 'leader' antecipa 'target'.
        """
        results = {}
        for lag in range(-max_lag, max_lag + 1):
            corr = df.select(
                pl.rolling_corr(pl.col(target), pl.col(leader).shift(lag), window_size=self.window)
            ).drop_nulls().to_series().mean()
            results[lag] = corr
        
        return results

    def rolling_r2(self, df: pl.DataFrame, asset_a: str, asset_b: str) -> pl.DataFrame:
        """
        Calcula o R² móvel (coeficiente de determinação).
        Indica a força da explicação de um ativo sobre o outro.
        """
        return df.with_columns([
            (pl.rolling_corr(pl.col(asset_a), pl.col(asset_b), window_size=self.window) ** 2).alias(f"r2_{asset_a}_{asset_b}")
        ])

class InstitutionalDrivers:
    """
    Cálculo de drivers macroeconômicos fundamentais.
    """
    @staticmethod
    def calculate_carry(selic: pl.Series, fed_funds: pl.Series) -> pl.Series:
        """Diferencial de juros (Carry Trade)."""
        return selic - fed_funds

    @staticmethod
    def calculate_real_yield(juros_nominais: pl.Series, inflacao_esperada: pl.Series) -> pl.Series:
        """Juro Real (Nominal - Expectativa)."""
        return juros_nominais - inflacao_esperada
