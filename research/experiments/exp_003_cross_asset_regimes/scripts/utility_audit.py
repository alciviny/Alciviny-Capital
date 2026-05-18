import os
import sys
import polars as pl
import numpy as np
import matplotlib.pyplot as plt

# Root path setup
current_file = os.path.abspath(__file__)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
sys.path.append(ROOT_DIR)

class UtilityAuditor:
    """
    Stage 5 — Utility Audit.
    Evaluates the practical value of regimes for risk management.
    """
    def __init__(self):
        self.exp_path = os.path.join(ROOT_DIR, "research", "experiments", "exp_003_cross_asset_regimes")

    def load_data(self) -> pl.DataFrame:
        path = os.path.join(self.exp_path, "results", "regime_labeled_data.parquet")
        return pl.read_parquet(path)

    def simulate_regime_filter(self, df: pl.DataFrame):
        print("Simulating regime-based filters (Honest OOS Evaluation)...")
        
        # 1. Calculate future returns (1h forward)
        # 2. Add transaction costs (estimated 0.5 bps per regime switch)
        df = df.with_columns([
            (pl.col("close_WIN").shift(-4) / pl.col("close_WIN") - 1).alias("fwd_ret_1h"),
            (pl.col("regime").diff() != 0).cast(pl.Float64).alias("is_switch")
        ]).drop_nulls()
        
        cost_bps = 0.5 / 10000
        df = df.with_columns([
            (pl.col("fwd_ret_1h") - pl.col("is_switch") * cost_bps).alias("fwd_ret_net")
        ])
        
        # Define strategy: Long only in Regime 2 (Neutral Consensus) and Regime 1
        # Avoid Regime 0 (Stress) and Regime 3
        df = df.with_columns([
            pl.when(pl.col("regime").is_in([1, 2])).then(pl.col("fwd_ret_net"))
              .otherwise(0.0)
              .alias("strategy_ret")
        ])
        
        for split in ["train", "test"]:
            split_df = df.filter(pl.col("split") == split)
            if len(split_df) == 0: continue
            
            print(f"\n--- PERFORMANCE SUMMARY: {split.upper()} ---")
            regime_stats = split_df.group_by("regime").agg([
                pl.col("fwd_ret_1h").mean().alias("avg_ret_bps") * 10000,
                pl.col("fwd_ret_1h").std().alias("vol_bps") * 10000,
                (pl.col("fwd_ret_1h").mean() / pl.col("fwd_ret_1h").std()).alias("sharpe_proxy")
            ]).sort("regime")
            print(regime_stats.to_pandas().to_string())
            
            # Calculate equity
            split_df = split_df.with_columns([
                (pl.col("fwd_ret_1h").cum_sum() + 1).alias("equity_base"),
                (pl.col("strategy_ret").cum_sum() + 1).alias("equity_regime")
            ])
            
            plt.figure(figsize=(12, 6))
            plt.plot(split_df["datetime"].to_pandas(), split_df["equity_base"].to_pandas(), label="Baseline (Buy & Hold)")
            plt.plot(split_df["datetime"].to_pandas(), split_df["equity_regime"].to_pandas(), label="Regime Filtered (Net)")
            plt.title(f"Utility Audit: {split.upper()} Split (Costs Included)")
            plt.ylabel("Cumulative Returns")
            plt.legend()
            plot_path = os.path.join(self.exp_path, "plots", f"utility_equity_{split}.png")
            plt.savefig(plot_path)
            print(f"Plot saved to {plot_path}")

    def run_audit(self):
        df = self.load_data()
        self.simulate_regime_filter(df)

if __name__ == "__main__":
    auditor = UtilityAuditor()
    auditor.run_audit()
