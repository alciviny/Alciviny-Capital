import polars as pl

class RiskManager:
    """
    Gerencia as regras de saída e dimensionamento de risco.
    """
    def __init__(self, stop_pts: float = None, target_pts: float = None, time_exit: int = 40):
        self.stop_pts = stop_pts
        self.target_pts = target_pts
        self.time_exit = time_exit

    def apply_fixed_risk(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calcula os preços de saída teóricos baseados em pontos fixos.
        """
        df = df.with_columns([
            pl.when(pl.col("entry_buy")).then(pl.col("close") - self.stop_pts).otherwise(None).alias("sl_buy"),
            pl.when(pl.col("entry_buy")).then(pl.col("close") + self.target_pts).otherwise(None).alias("tp_buy"),
            pl.when(pl.col("entry_sell")).then(pl.col("close") + self.stop_pts).otherwise(None).alias("sl_sell"),
            pl.when(pl.col("entry_sell")).then(pl.col("close") - self.target_pts).otherwise(None).alias("tp_sell"),
        ])
        return df
