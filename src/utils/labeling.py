import polars as pl
import numpy as np

class TripleBarrierLabeler:
    """
    Implementação institucional do Triple Barrier Method (De Prado).
    Define labels baseados em Take Profit, Stop Loss e Expiração Temporal.
    """
    def __init__(self, pt_sl=[2.0, 1.5], horizon=30):
        self.pt_sl = pt_sl
        self.horizon = horizon

    def label(self, df: pl.DataFrame, price_col="close") -> pl.DataFrame:
        """
        Vetorização em Polars para rotulagem Triple Barrier.
        """
        # 1. Calcular barreiras baseadas em volatilidade dinâmica
        # Usamos uma janela de 100 candles para a volatilidade
        df = df.with_columns([
            (pl.col(price_col).log().diff().rolling_std(window_size=100) * 1.5).alias("barrier_unit")
        ]).fill_null(strategy="forward")

        # 2. Toque de Barreira
        # Usamos shift(-horizon) e rolling_max/min para ver o futuro sem leakage no treino, 
        # mas apenas para gerar o target (label).
        
        # Simplificação vetorizada: se o max futuro atingiu PT antes do min atingir SL
        # Como o Polars não tem 'find_first' em janelas nativo de forma simples, 
        # usamos a aproximação de retorno máximo/mínimo na janela.
        
        pt = pl.col("barrier_unit") * self.pt_sl[0]
        sl = pl.col("barrier_unit") * self.pt_sl[1]

        df = df.with_columns([
            (pl.col(price_col).shift(-self.horizon).rolling_max(window_size=self.horizon) / pl.col(price_col) - 1).alias("max_fwd_ret"),
            (1 - pl.col(price_col).shift(-self.horizon).rolling_min(window_size=self.horizon) / pl.col(price_col)).alias("max_fwd_loss")
        ])

        return df.with_columns([
            pl.when(pl.col("max_fwd_ret") >= pt).then(1)   # Bullish Outcome
              .when(pl.col("max_fwd_loss") >= sl).then(0) # Bearish/Loss Outcome (Target 0 para binário ou multinomial)
              .otherwise(0)                              # Sideways/Time-out
              .alias("label_tbm")
        ]).drop(["max_fwd_ret", "max_fwd_loss", "barrier_unit"])
