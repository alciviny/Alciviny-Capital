import os
import sys
import polars as pl
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import joblib

# Root path setup
current_file = os.path.abspath(__file__)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
sys.path.append(ROOT_DIR)

class RegimeDiscoveryEngine:
    """
    Stage 2 — Latent Regime Discovery.
    Identifies hidden market states using cross-asset features.
    """
    def __init__(self, n_regimes: int = 4):
        self.n_regimes = n_regimes
        self.exp_path = os.path.join(ROOT_DIR, "research", "experiments", "exp_003_cross_asset_regimes")
        self.features_to_use = [
            "corr_WIN_WDO_60",
            "corr_WIN_DI1_60",
            "corr_WDO_DI1_60",
            "cdi_60",
            "vol_ratio_wdo_win",
            "vol_ratio_di1_win"
        ]

    def load_features(self) -> pl.DataFrame:
        path = os.path.join(self.exp_path, "results", "features_15m.parquet")
        return pl.read_parquet(path)

    def find_optimal_regimes(self, df: pl.DataFrame, max_k: int = 8):
        """Uses BIC/AIC to find the optimal number of clusters."""
        print("Auditing optimal number of regimes (AIC/BIC)...")
        X = df.select(self.features_to_use).to_pandas()
        X = StandardScaler().fit_transform(X)
        
        bics = []
        aics = []
        ks = range(2, max_k + 1)
        
        for k in ks:
            gmm = GaussianMixture(n_components=k, random_state=42, n_init=5)
            gmm.fit(X)
            bics.append(gmm.bic(X))
            aics.append(gmm.aic(X))
            
        plt.figure(figsize=(10, 5))
        plt.plot(ks, bics, label="BIC", marker='o')
        plt.plot(ks, aics, label="AIC", marker='o')
        plt.title("Regime Optimization (AIC/BIC)")
        plt.xlabel("Number of Regimes")
        plt.ylabel("Score")
        plt.legend()
        plt.savefig(os.path.join(self.exp_path, "plots", "regime_optimization.png"))
        print(f"Optimization plot saved. Suggested K (min BIC): {ks[np.argmin(bics)]}")

    def train_regime_model(self, df: pl.DataFrame, train_ratio: float = 0.7):
        print(f"Training GMM with {self.n_regimes} regimes (Train Ratio: {train_ratio})...")
        
        # Sort by datetime to ensure temporal integrity
        df = df.sort("datetime")
        
        n_train = int(len(df) * train_ratio)
        train_df = df.head(n_train)
        test_df = df.tail(len(df) - n_train)
        
        X_train_raw = train_df.select(self.features_to_use).to_pandas()
        X_test_raw = test_df.select(self.features_to_use).to_pandas()
        
        # Fit scaler ONLY on train data
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train_raw)
        X_test = scaler.transform(X_test_raw) # Transform test using train params (No Leakage)
        
        # Fit GMM ONLY on train data
        gmm = GaussianMixture(n_components=self.n_regimes, random_state=42, n_init=10)
        gmm.fit(X_train)
        
        # Predict for both sets
        train_regimes = gmm.predict(X_train)
        train_probs = gmm.predict_proba(X_train)
        
        test_regimes = gmm.predict(X_test)
        test_probs = gmm.predict_proba(X_test)
        
        # Combine back
        train_df = train_df.with_columns([
            pl.Series(name="regime", values=train_regimes),
            pl.Series(name="regime_confidence", values=train_probs.max(axis=1)),
            pl.lit("train").alias("split")
        ])
        
        test_df = test_df.with_columns([
            pl.Series(name="regime", values=test_regimes),
            pl.Series(name="regime_confidence", values=test_probs.max(axis=1)),
            pl.lit("test").alias("split")
        ])
        
        final_df = pl.concat([train_df, test_df])
        
        # Save model and scaler
        joblib.dump(gmm, os.path.join(self.exp_path, "artifacts", "regime_gmm.pkl"))
        joblib.dump(scaler, os.path.join(self.exp_path, "artifacts", "regime_scaler.pkl"))
        
        return final_df, gmm

    def audit_regime_characteristics(self, df: pl.DataFrame):
        """Analyzes the mean characteristics of each detected regime, splitting by Train/Test."""
        print("\n--- REGIME CHARACTERISTICS AUDIT (OOS VALIDATION) ---")
        
        for split in ["train", "test"]:
            print(f"\n>> Split: {split.upper()}")
            summary = df.filter(pl.col("split") == split).group_by("regime").agg([
                pl.count().alias("n_samples"),
                pl.col("corr_WIN_WDO_60").mean().alias("avg_corr_win_wdo"),
                pl.col("corr_WIN_DI1_60").mean().alias("avg_corr_win_di1"),
                pl.col("ret_WIN").mean().alias("avg_ret_win"),
                pl.col("ret_WDO").mean().alias("avg_ret_wdo"),
                pl.col("cdi_60").mean().alias("avg_cdi")
            ]).sort("regime")
            
            print(summary.to_pandas().to_string())
            summary.write_csv(os.path.join(self.exp_path, "results", f"regime_summary_{split}.csv"))
            
    def run_stage_2(self):
        df = self.load_features()
        # Find optimal regimes using only training data to avoid leakage even in selection
        n_train = int(len(df) * 0.7)
        self.find_optimal_regimes(df.head(n_train))
        
        df_with_regimes, model = self.train_regime_model(df)
        self.audit_regime_characteristics(df_with_regimes)
        
        # Save final research dataset
        output_path = os.path.join(self.exp_path, "results", "regime_labeled_data.parquet")
        df_with_regimes.write_parquet(output_path)
        print(f"\nLabeled data (Train + OOS) saved to {output_path}")

if __name__ == "__main__":
    discovery = RegimeDiscoveryEngine(n_regimes=4)
    discovery.run_stage_2()
