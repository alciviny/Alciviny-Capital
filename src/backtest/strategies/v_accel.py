import polars as pl
from src.backtest.strategies.base import BaseStrategy
from src.research.obtr_research.obtr_bollinger import OBTRBollinger
from src.research.utils import calculate_rsi_200, get_rsi_level_advance_pl, get_rsi_slope_pl

class VAccelStrategy(BaseStrategy):
    """
    Estratégia 5: V-ACCEL (OBTR Confluence).
    Combina Pullback de IFR 200 com Aceleração de Volatilidade OBTR.
    """
    def __init__(self):
        super().__init__("V-ACCEL")
        self.obtr_indicator = OBTRBollinger()

    def generate_signals(self, df: pl.DataFrame) -> pl.DataFrame:
        # 1. Indicadores de Preço (IFR)
        df = df.with_columns([
            pl.Series("rsi", calculate_rsi_200(df['close'].to_numpy()))
        ])
        
        df = df.with_columns([
            get_rsi_level_advance_pl("rsi").alias("advance"),
            get_rsi_slope_pl("rsi", period=10).alias("slope"),
            ((pl.col("rsi") >= 48) & (pl.col("rsi") <= 52)).alias("in_zone")
        ])

        # 2. Indicador OBTR
        df = self.obtr_indicator.compute(df)
        df = df.with_columns([
            (pl.col("obtr") - pl.col("obtr").shift(10)).alias("obtr_slope_10")
        ])

        # 3. Lógica de Entrada
        # Compra: IFR na zona + Slope IFR > 0 + OBTR > BB Upper + Slope OBTR > 0
        df = df.with_columns([
            (pl.col("in_zone") & (pl.col("advance") == 1) & (pl.col("slope") > 0) & 
             (pl.col("obtr") > pl.col("bb_upper")) & (pl.col("obtr_slope_10") > 0)).alias("entry_buy"),
            
            # Venda: IFR na zona + Slope IFR < 0 + OBTR < BB Lower + Slope OBTR < 0
            (pl.col("in_zone") & (pl.col("advance") == -1) & (pl.col("slope") < 0) & 
             (pl.col("obtr") < pl.col("bb_lower")) & (pl.col("obtr_slope_10") < 0)).alias("entry_sell")
        ])

        return df
