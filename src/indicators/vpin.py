import polars as pl
import numpy as np
from typing import List, Dict, Any

class VPINEngine:
    """
    Motor de VPIN (Volume-based Probability of Informed Trading).
    Usa Event-Based Sampling (Volume Buckets) para medir toxicidade informacional.
    """
    def __init__(self, bucket_size: int = 5000):
        self.bucket_size = bucket_size

    def calculate_vpin(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calcula VPIN baseado em buckets de volume.
        Exige colunas: 'volume', 'bid_volume', 'ask_volume' (ou delta).
        """
        # 1. Transformação para Tempo de Informação (Volume Buckets)
        # Identificar o acumulado de volume
        df = df.with_columns([
            pl.col("volume").cum_sum().alias("cum_vol")
        ])
        
        # Atribuir cada linha a um Bucket ID
        df = df.with_columns([
            (pl.col("cum_vol") // self.bucket_size).cast(pl.Int64).alias("bucket_id")
        ])
        
        # 2. Agregação por Bucket
        # Precisamos de V_buy e V_sell por bucket
        # Se não houver bid/ask real, usamos a estimativa tick-test (OHLCV fallback)
        if "bid_volume" not in df.columns or "ask_volume" not in df.columns:
            # Fallback Tick Test: Close > Open -> Buy Volume = Total Volume
            df = df.with_columns([
                pl.when(pl.col("close") > pl.col("open")).then(pl.col("volume")).otherwise(0).alias("v_buy"),
                pl.when(pl.col("close") < pl.col("open")).then(pl.col("volume")).otherwise(0).alias("v_sell")
            ])
        else:
            df = df.rename({"bid_volume": "v_sell", "ask_volume": "v_buy"})
            
        bucket_agg = df.group_by("bucket_id").agg([
            pl.col("v_buy").sum().alias("vb"),
            pl.col("v_sell").sum().alias("vs"),
            pl.col("time").last().alias("bucket_time_end")
        ])
        
        # 3. Cálculo do Desequilíbrio (Imbalance)
        bucket_agg = bucket_agg.with_columns([
            (pl.col("vb") - pl.col("vs")).abs().alias("oi") # Order Imbalance
        ]).sort("bucket_id")
        
        # 4. VPIN Calculation (Rolling window over N buckets)
        # VPIN = sum(|Vb - Vs|) / (n * V_bucket)
        n_buckets = 50 # Janela padrão institucional
        vpin_expr = pl.col("oi").rolling_sum(window_size=n_buckets) / (n_buckets * self.bucket_size)
        
        bucket_agg = bucket_agg.with_columns([
            vpin_expr.alias("vpin")
        ])
        
        # 5. Join de volta para o tempo cronológico (Re-sampling)
        # Mapeamos o VPIN do bucket para o tempo real
        df = df.join(bucket_agg.select(["bucket_id", "vpin"]), on="bucket_id", how="left")
        
        return df.drop(["cum_vol", "bucket_id", "v_buy", "v_sell"])

def add_vpin_to_state(df: pl.DataFrame, bucket_size: int = 5000) -> pl.DataFrame:
    """
    Integra VPIN ao State Vector.
    """
    engine = VPINEngine(bucket_size=bucket_size)
    return engine.calculate_vpin(df)
