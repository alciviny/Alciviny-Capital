import pandas as pd
import numpy as np

def add_vwap_bands(df, period_type='D', atr_period=300, multipliers=[1.5, 3.0, 6.0, 9.0]):
    """
    Calcula VWAP Periódica com Bandas de ATR.
    period_type: 'D' (Diário), 'W' (Semanal), 'M' (Mensal)
    """
    df = df.copy()
    
    # 1. Definir a chave de agrupamento conforme o período
    if period_type == 'D':
        group_key = df['time'].dt.date
    elif period_type == 'W':
        group_key = df['time'].dt.to_period('W').apply(lambda r: r.start_time)
    elif period_type == 'M':
        group_key = df['time'].dt.to_period('M').apply(lambda r: r.start_time)
    else:
        group_key = df['time'].dt.date

    # 2. Calcular VWAP Acumulada no Período
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = df['tp'] * df['tick_volume']
    
    # Agrupar e calcular somas cumulativas
    groups = df.groupby(group_key)
    df['cum_pv'] = groups['pv'].cumsum()
    df['cum_v'] = groups['tick_volume'].cumsum()
    
    vwap_col = f'VWAP_{period_type}'
    df[vwap_col] = df['cum_pv'] / df['cum_v']

    # 3. Calcular ATR (Welles Wilder) - Período 300
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift(1)).abs()
    low_cp = (df['low'] - df['close'].shift(1)).abs()
    
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    # Welles Wilder Smoothing = EMA com alpha = 1/N
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    # 4. Calcular Bandas
    for mult in multipliers:
        mult_str = str(mult).replace('.', '')
        df[f'{vwap_col}_U{mult_str}'] = df[vwap_col] + (atr * mult)
        df[f'{vwap_col}_L{mult_str}'] = df[vwap_col] - (atr * mult)

    # Limpeza de colunas temporárias
    return df.drop(columns=['tp', 'pv', 'cum_pv', 'cum_v'])
