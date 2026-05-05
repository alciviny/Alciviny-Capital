"""
============================================================
ON BALANCE TRUE RANGE (OBTR) com Bandas de Bollinger
============================================================
Versão Otimizada para o Sistema AlcivinyEdger (Polars Native)
"""

import polars as pl
import numpy as np
from dataclasses import dataclass
from typing import Optional

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
        # RMA(n) é equivalente a EWM com alpha = 1/n
        return series.ewm_mean(alpha=1.0/period, adjust=False)

    def compute(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calcula o indicador de forma totalmente vetorizada.
        Aceita colunas em lowercase (padrão do sistema) ou Uppercase.
        """
        # 1. Normalização de Colunas
        cols = {c.lower(): c for c in df.columns}
        c_close = cols.get("close")
        c_high = cols.get("high")
        c_low = cols.get("low")
        
        if not all([c_close, c_high, c_low]):
            raise ValueError(f"Colunas OHLC necessárias não encontradas. Colunas disponíveis: {df.columns}")

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

        # 4. Cálculo do ATR sobre OBTR (Welles Wilder)
        # TR do OBTR é o valor absoluto da sua variação (que é o TR do preço)
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
            (pl.col("obtr") + self.cfg.atr_mult_2 * pl.col("atr_obtr")).alias("atr_upper_2"),
            (pl.col("obtr") - self.cfg.atr_mult_1 * pl.col("atr_obtr")).alias("atr_lower_1"),
            (pl.col("obtr") - self.cfg.atr_mult_2 * pl.col("atr_obtr")).alias("atr_lower_2")
        ])

        # 7. Sinais e %B
        df = df.with_columns([
            ((pl.col("obtr") - pl.col("bb_lower")) / (pl.col("bb_upper") - pl.col("bb_lower") + 1e-9)).alias("bb_pct_b"),
            pl.when(pl.col("obtr") > pl.col("obtr_rma_200")).then(1).otherwise(-1).alias("obtr_signal")
        ])

        # Limpeza de colunas auxiliares
        return df.drop(["_tr", "_dir", "_obtr_std"])
