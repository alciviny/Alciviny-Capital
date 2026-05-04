import pandas as pd
import numpy as np

def calculate_rsi_wilder(series: pd.Series, period: int = 200) -> pd.Series:
    """
    Calcula o RSI (IFR) usando o método rigoroso de Welles Wilder.
    Padrão: Primeiro valor é SMA, os seguintes são suavizados por Wilder.
    """
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 1. Calcular a primeira média (SMA)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # 2. Aplicar suavização de Wilder para os valores subsequentes
    # Fórmula: (Média Anterior * (N-1) + Ganho Atual) / N
    for i in range(period, len(series)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def add_ifr_grid(df: pd.DataFrame, period: int = 200, lines: list = None, col_name: str = None) -> pd.DataFrame:
    """
    Adiciona o IFR e as linhas de referência ao DataFrame com nome de coluna customizável.
    """
    df = df.copy()
    
    # Nome da coluna: Prioriza col_name, senão usa padrão IFR_200
    target_col = col_name if col_name else f"IFR_{period}"
    
    # Calcular IFR
    df[target_col] = calculate_rsi_wilder(df['close'], period)
    
    # Adicionar as linhas de grid
    if lines:
        for line in lines:
            df[f'ref_line_{line}'] = float(line)
            
    return df
