import os
import sys
import polars as pl
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

# Root path setup
current_file = os.path.abspath(__file__)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
sys.path.append(ROOT_DIR)

class CrossAssetFeatureEngine:
    """
    Stage 1 — Cross-Asset Feature Engine.
    Calculates structural relationship features between WIN, WDO, and DI1.
    """
    def __init__(self, tf: str = "15"):
        self.tf = tf
        self.data_path = os.path.join(ROOT_DIR, "data", "storage")
        self.assets = ["WIN", "WDO", "DI1"]
        self.windows = [20, 60, 240] # 5h, 15h, 60h (assuming 15m candles)
        
    def load_and_sync(self) -> pl.DataFrame:
        """Loads and synchronizes the three assets by timestamp."""
        dfs = []
        for asset in self.assets:
            path = os.path.join(self.data_path, f"{asset}$_{self.tf}_CLEAN.parquet")
            if not os.path.exists(path):
                # Fallback to standard if CLEAN doesn't exist
                path = os.path.join(self.data_path, f"{asset}$_{self.tf}.parquet")
            
            df = pl.read_parquet(path).select([
                pl.col("time").alias("datetime"),
                pl.col("close").alias(f"close_{asset}")
            ])
            # Calculate returns
            df = df.with_columns([
                (pl.col(f"close_{asset}").log().diff()).alias(f"ret_{asset}")
            ])
            dfs.append(df)
            
        # Join assets
        synced = dfs[0]
        for df in dfs[1:]:
            synced = synced.join(df, on="datetime", how="inner")
            
        return synced.drop_nulls()

    def add_rolling_correlations(self, df: pl.DataFrame) -> pl.DataFrame:
        """Adds rolling Pearson correlations between all asset pairs."""
        pairs = [("WIN", "WDO"), ("WIN", "DI1"), ("WDO", "DI1")]
        
        for w in self.windows:
            for a1, a2 in pairs:
                col1 = f"ret_{a1}"
                col2 = f"ret_{a2}"
                df = df.with_columns([
                    pl.rolling_corr(
                        pl.col(col1), 
                        pl.col(col2), 
                        window_size=w
                    ).alias(f"corr_{a1}_{a2}_{w}")
                ])
        return df

    def add_correlation_dispersion(self, df: pl.DataFrame) -> pl.DataFrame:
        """Adds Correlation Dispersion Index (CDI)."""
        for w in self.windows:
            corr_cols = [f"corr_WIN_WDO_{w}", f"corr_WIN_DI1_{w}", f"corr_WDO_DI1_{w}"]
            # CDI = Standard deviation of the correlations
            df = df.with_columns([
                pl.concat_list(corr_cols).list.std().alias(f"cdi_{w}")
            ])
        return df

    def add_lead_lag_structure(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Implements a simple Lagged Cross-Correlation as proxy for Lead-Lag.
        Measures if asset A at t-1 correlates more with asset B at t than contemporaneously.
        """
        pairs = [("WIN", "WDO"), ("WIN", "DI1"), ("WDO", "DI1")]
        lags = [1, 2, 3]
        
        for w in self.windows:
            for a1, a2 in pairs:
                for lag in lags:
                    # a1 leads a2
                    df = df.with_columns([
                        pl.rolling_corr(
                            pl.col(f"ret_{a1}").shift(lag),
                            pl.col(f"ret_{a2}"),
                            window_size=w
                        ).alias(f"lead_{a1}_{a2}_lag{lag}_w{w}")
                    ])
                    # a2 leads a1
                    df = df.with_columns([
                        pl.rolling_corr(
                            pl.col(f"ret_{a2}").shift(lag),
                            pl.col(f"ret_{a1}"),
                            window_size=w
                        ).alias(f"lead_{a2}_{a1}_lag{lag}_w{w}")
                    ])
        return df

    def add_volatility_spread(self, df: pl.DataFrame) -> pl.DataFrame:
        """Adds relative volatility features."""
        for asset in self.assets:
            df = df.with_columns([
                (pl.col(f"ret_{asset}").rolling_std(window_size=20)).alias(f"vol_{asset}")
            ])
            
        # Volatility Ratios
        df = df.with_columns([
            (pl.col("vol_WDO") / (pl.col("vol_WIN") + 1e-9)).alias("vol_ratio_wdo_win"),
            (pl.col("vol_DI1") / (pl.col("vol_WIN") + 1e-9)).alias("vol_ratio_di1_win")
        ])
        return df

    def run_pipeline(self):
        print(f"--- Starting Stage 1: Feature Engine (TF: {self.tf}) ---")
        df = self.load_and_sync()
        print(f"Synced data: {len(df)} rows.")
        
        df = self.add_rolling_correlations(df)
        df = self.add_correlation_dispersion(df)
        df = self.add_lead_lag_structure(df)
        df = self.add_volatility_spread(df)
        
        df = df.drop_nulls()
        output_path = os.path.join(ROOT_DIR, "research", "experiments", "exp_003_cross_asset_regimes", "results", "features_15m.parquet")
        df.write_parquet(output_path)
        print(f"Features saved to {output_path}")
        print(f"Total features created: {len(df.columns)}")
        
        # Simple plot of CDI to verify
        plt.figure(figsize=(12, 6))
        plt.plot(df["datetime"].to_pandas(), df["cdi_60"].to_pandas(), label="CDI (60)")
        plt.title("Correlation Dispersion Index (Window: 60)")
        plt.legend()
        plot_path = os.path.join(ROOT_DIR, "research", "experiments", "exp_003_cross_asset_regimes", "plots", "cdi_initial_test.png")
        plt.savefig(plot_path)
        print(f"Test plot saved to {plot_path}")

if __name__ == "__main__":
    engine = CrossAssetFeatureEngine(tf="15")
    engine.run_pipeline()
