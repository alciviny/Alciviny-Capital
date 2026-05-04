import pandas as pd
import numpy as np

def calculate_rsi_wilder(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula o RSI (IFR) usando o método de Welles Wilder vetorizado.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def add_ifr_grid(df: pd.DataFrame, period: int = 14, lines: list = None, col_name: str = None) -> pd.DataFrame:
    df = df.copy()
    target_col = col_name if col_name else f"IFR_{period}"
    df[target_col] = calculate_rsi_wilder(df['close'], period)
    return df
