import pandas as pd
import numpy as np
import polars as pl
from dataclasses import dataclass
from typing import Optional, List

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

def calculate_atr_pl(high: str, low: str, close: str, period: int = 14) -> pl.Expr:
    """
    Calcula o Average True Range (ATR) usando Polars.
    """
    tr = pl.max_horizontal([
        pl.col(high) - pl.col(low),
        (pl.col(high) - pl.col(close).shift(1)).abs(),
        (pl.col(low) - pl.col(close).shift(1)).abs()
    ]).fill_null(0)
    
    # RMA (Welles Wilder Smoothing)
    return tr.ewm_mean(alpha=1.0/period, adjust=False)

# --- OBTR (ON-BALANCE TRUE RANGE) ---

@dataclass
class OBTRBollingerConfig:
    bb_period: int = 200
    bb_std: float = 0.45
    atr_period: int = 14
    atr_mult_1: float = 1.5
    atr_mult_2: float = 3.0

class OBTRBollinger:
    """
    On Balance True Range com Bandas de Bollinger (Welles Wilder).
    Otimizado para Polars para performance institucional.
    """
    def __init__(self, config: Optional[OBTRBollingerConfig] = None):
        self.cfg = config or OBTRBollingerConfig()

    def _calculate_rma_pl(self, series: pl.Expr, period: int) -> pl.Expr:
        """Média Móvel de Welles Wilder (RMA) via EWM."""
        return series.ewm_mean(alpha=1.0/period, adjust=False)

    def compute(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calcula o indicador de forma totalmente vetorizada usando Polars.
        """
        # 1. Normalização de Colunas
        cols = {c.lower(): c for c in df.columns}
        c_close = cols.get("close")
        c_high = cols.get("high")
        c_low = cols.get("low")
        
        if not all([c_close, c_high, c_low]):
            raise ValueError(f"Colunas OHLC necessárias não encontradas.")

        # 2. Cálculo do True Range (TR)
        df = df.with_columns([
            pl.max_horizontal([
                pl.col(c_high) - pl.col(c_low),
                (pl.col(c_high) - pl.col(c_close).shift(1)).abs(),
                (pl.col(c_low) - pl.col(c_close).shift(1)).abs()
            ]).fill_null(0).alias("_tr")
        ])

        # 3. Cálculo do OBTR
        df = df.with_columns([
            pl.when(pl.col(c_close) > pl.col(c_close).shift(1)).then(1)
              .when(pl.col(c_close) < pl.col(c_close).shift(1)).then(-1)
              .otherwise(0).alias("_dir")
        ])
        
        df = df.with_columns([
            (pl.col("_dir") * pl.col("_tr")).cum_sum().alias("obtr")
        ])

        # 4. Cálculo do ATR sobre OBTR
        df = df.with_columns([
            self._calculate_rma_pl(pl.col("_tr"), self.cfg.atr_period).alias("atr_obtr")
        ])

        # 5. Média Welles Wilder (RMA) e Desvio Padrão sobre OBTR
        df = df.with_columns([
            self._calculate_rma_pl(pl.col("obtr"), self.cfg.bb_period).alias("obtr_rma_200"),
            pl.col("obtr").rolling_std(window_size=self.cfg.bb_period).alias("_obtr_std")
        ])

        # 6. Bandas de Bollinger e Envelopes ATR
        df = df.with_columns([
            (pl.col("obtr_rma_200") + self.cfg.bb_std * pl.col("_obtr_std")).alias("bb_upper"),
            (pl.col("obtr_rma_200") - self.cfg.bb_std * pl.col("_obtr_std")).alias("bb_lower"),
            (pl.col("obtr") + self.cfg.atr_mult_1 * pl.col("atr_obtr")).alias("atr_upper_1"),
            (pl.col("obtr") - self.cfg.atr_mult_1 * pl.col("atr_obtr")).alias("atr_lower_1")
        ])

        # 7. Sinais e %B
        df = df.with_columns([
            ((pl.col("obtr") - pl.col("bb_lower")) / (pl.col("bb_upper") - pl.col("bb_lower") + 1e-9)).alias("bb_pct_b")
        ])

        return df.drop(["_tr", "_dir", "_obtr_std"])
