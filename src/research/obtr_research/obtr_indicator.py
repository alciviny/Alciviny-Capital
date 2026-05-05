import polars as pl
import numpy as np

def calculate_obtr_pl(df: pl.DataFrame) -> pl.Series:
    """
    Calcula o On Balance True Range (OBTR).
    Lógica: Acumula o True Range positivamente em candles de alta 
    e negativamente em candles de baixa.
    """
    # 1. Calcular True Range (TR)
    tr = pl.max_horizontal([
        pl.col("high") - pl.col("low"),
        (pl.col("high") - pl.col("close").shift(1)).abs(),
        (pl.col("low") - pl.col("close").shift(1)).abs()
    ]).fill_null(strategy="zero")
    
    # 2. Determinar Direção
    direction = pl.when(pl.col("close") > pl.col("close").shift(1)) \
                  .then(1) \
                  .when(pl.col("close") < pl.col("close").shift(1)) \
                  .then(-1) \
                  .otherwise(0)
    
    # 3. Acumular (OBTR)
    obtr = (direction * tr).cum_sum()
    
    return obtr

def add_obtr_signals(df: pl.DataFrame, window_ma: int = 20) -> pl.DataFrame:
    """
    Adiciona o OBTR e sinais básicos de média móvel sobre o indicador.
    """
    df = df.with_columns([
        calculate_obtr_pl(df).alias("obtr")
    ])
    
    # Adicionar uma média do OBTR para identificar divergências ou cruzamentos
    df = df.with_columns([
        pl.col("obtr").rolling_mean(window_size=window_ma).alias("obtr_signal")
    ])
    
    return df
