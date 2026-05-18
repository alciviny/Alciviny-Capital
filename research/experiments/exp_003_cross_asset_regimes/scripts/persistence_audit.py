import os
import sys
import polars as pl
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Root path setup
current_file = os.path.abspath(__file__)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
sys.path.append(ROOT_DIR)

class PersistenceAuditor:
    """
    Stage 4 — Regime Persistence Audit.
    Measures how long regimes last and how they transition.
    """
    def __init__(self):
        self.exp_path = os.path.join(ROOT_DIR, "research", "experiments", "exp_003_cross_asset_regimes")

    def load_data(self) -> pl.DataFrame:
        path = os.path.join(self.exp_path, "results", "regime_labeled_data.parquet")
        return pl.read_parquet(path)

    def calculate_persistence(self, df: pl.DataFrame):
        print("Calculating regime persistence...")
        # Calculate streak lengths
        regimes = df["regime"].to_numpy()
        
        # Identify where regime changes
        changes = np.diff(regimes) != 0
        change_indices = np.where(changes)[0] + 1
        
        # Split into streaks
        streaks = np.split(regimes, change_indices)
        streak_lengths = [len(s) for s in streaks]
        streak_regimes = [s[0] for s in streaks]
        
        persistence_df = pl.DataFrame({
            "regime": streak_regimes,
            "duration_candles": streak_lengths
        })
        
        # Summary by regime
        summary = persistence_df.group_by("regime").agg([
            pl.count().alias("n_occurrences"),
            pl.col("duration_candles").mean().alias("avg_duration"),
            pl.col("duration_candles").median().alias("median_duration"),
            pl.col("duration_candles").max().alias("max_duration")
        ]).sort("regime")
        
        print("\n--- PERSISTENCE SUMMARY ---")
        print(summary.to_pandas().to_string())
        summary.write_csv(os.path.join(self.exp_path, "results", "persistence_summary.csv"))
        
        return persistence_df

    def calculate_transition_matrix(self, df: pl.DataFrame):
        print("\nCalculating transition matrix...")
        regimes = df["regime"].to_numpy()
        n_states = len(np.unique(regimes))
        
        matrix = np.zeros((n_states, n_states))
        for i in range(len(regimes) - 1):
            matrix[regimes[i], regimes[i+1]] += 1
            
        # Normalize rows to get probabilities
        row_sums = matrix.sum(axis=1)
        matrix_prob = matrix / row_sums[:, np.newaxis]
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(matrix_prob, annot=True, cmap="YlGnBu", fmt=".2f")
        plt.title("Regime Transition Matrix (Probabilities)")
        plt.xlabel("Next State")
        plt.ylabel("Current State")
        plt.savefig(os.path.join(self.exp_path, "plots", "transition_matrix.png"))
        
        print("Transition matrix saved to plots.")
        return matrix_prob

    def run_audit(self):
        df = self.load_data()
        self.calculate_persistence(df)
        self.calculate_transition_matrix(df)
        
        # Visualize duration distributions
        plt.figure(figsize=(12, 6))
        # Filter for better visualization if needed
        # sns.boxplot(x="regime", y="duration_candles", data=persistence_df.to_pandas())
        # plt.title("Regime Duration Distribution")
        # plt.savefig(os.path.join(self.exp_path, "plots", "duration_distribution.png"))

if __name__ == "__main__":
    auditor = PersistenceAuditor()
    auditor.run_audit()
