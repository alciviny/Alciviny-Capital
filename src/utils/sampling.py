import polars as pl
import numpy as np
from typing import List

def get_cusum_events(series: pl.Series, threshold: float) -> List[int]:
    """
    Filtro CUSUM (Symmetric Cumulative Sum Filter).
    Identifica pontos onde a mudança acumulada supera um threshold dinâmico.
    Útil para amostragem baseada em eventos (De Prado).
    """
    events = []
    s_pos, s_neg = 0, 0
    diffs = series.diff().fill_null(0).to_numpy()
    
    for i in range(1, len(diffs)):
        s_pos = max(0, s_pos + diffs[i])
        s_neg = min(0, s_neg + diffs[i])
        
        if s_pos > threshold:
            s_pos = 0
            events.append(i)
        elif s_neg < -threshold:
            s_neg = 0
            events.append(i)
            
    return events

def volatility_adjusted_cusum(df: pl.DataFrame, price_col: str, window: int = 100, mult: float = 2.0) -> List[int]:
    """
    Executa o CUSUM com threshold ajustado pela volatilidade (ATR ou StdDev).
    Garante que a amostragem seja sensível à mudança de regime de vol.
    """
    # Calcular threshold dinâmico baseado no desvio padrão logarítmico
    df = df.with_columns([
        (pl.col(price_col).log().diff().rolling_std(window_size=window) * mult).alias("dynamic_threshold")
    ]).fill_null(strategy="forward")
    
    thresholds = df["dynamic_threshold"].to_numpy()
    prices = df[price_col].log().to_numpy()
    
    events = []
    s_pos, s_neg = 0, 0
    
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        h = thresholds[i]
        
        s_pos = max(0, s_pos + diff)
        s_neg = min(0, s_neg + diff)
        
        if s_pos > h:
            s_pos = 0
            events.append(i)
        elif s_neg < -h:
            s_neg = 0
            events.append(i)
            
    return events
