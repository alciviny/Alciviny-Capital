import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.microstructure import add_microstructure_indicators, FlowState
from src.data.factory import StateVectorFactory

class AdversarialAuditor:
    def __init__(self, asset: str = "WIN", tf: str = "15"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        self.factory = StateVectorFactory()

    def load_data(self) -> pl.DataFrame:
        path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}_CLEAN.parquet")
        df = pl.read_parquet(path)
        df = add_microstructure_indicators(df)
        
        # Extrair Ano
        df = df.with_columns([
            pl.col("time").dt.year().alias("year")
        ])
        return df

    def calculate_psi(self, expected, actual, buckets=10):
        """
        Calcula o Population Stability Index (PSI).
        """
        def scale_range(data, n):
            return np.histogram(data, bins=n, range=(data.min(), data.max()))[0]

        expected_percents = scale_range(expected, buckets) / len(expected)
        actual_percents = scale_range(actual, buckets) / len(actual)

        # Evitar divisão por zero
        expected_percents = np.clip(expected_percents, 0.0001, 1.0)
        actual_percents = np.clip(actual_percents, 0.0001, 1.0)

        psi_value = np.sum((expected_percents - actual_percents) * np.log(expected_percents / actual_percents))
        return psi_value

    def run_adversarial_test(self, df: pl.DataFrame, year_a: int, year_b: int):
        """
        Tenta prever se um dado pertence ao Ano A ou Ano B.
        AUC > 0.7 indica drift severo.
        """
        print(f"\n--- Teste Adversário: {year_a} vs {year_b} ---")
        
        # Filtrar anos e preparar features
        sub_df = df.filter(pl.col("year").is_in([year_a, year_b])).drop_nulls()
        
        # Usamos uma factory simplificada para o teste
        features = [
            "open", "high", "low", "close", "volume", 
            "ofi", "vol_risk_premium", "flow_state"
        ]
        features = [f for f in features if f in sub_df.columns]
        
        # One-hot encoding manual para o RF
        X = sub_df.select(features).to_pandas()
        X = pd.get_dummies(X, columns=["flow_state"])
        y = (sub_df["year"] == year_b).cast(pl.Int8).to_numpy()
        
        # Cross-validation
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        aucs = []
        
        for train_idx, test_idx in skf.split(X, y):
            clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            clf.fit(X.iloc[train_idx], y[train_idx])
            probs = clf.predict_proba(X.iloc[test_idx])[:, 1]
            aucs.append(roc_auc_score(y[test_idx], probs))
            
        avg_auc = np.mean(aucs)
        print(f"Adversarial AUC: {avg_auc:.4f}")
        
        # Identificar Features Tóxicas
        importances = pd.Series(clf.feature_importances_, index=X.columns).sort_values(ascending=False)
        print("Top Drift Drivers:")
        print(importances.head(5))
        
        return avg_auc, importances

    def run_temporal_edge_stability(self, df: pl.DataFrame):
        """
        Verifica se o edge de ABSORPTION e TRAPPED persiste através dos anos.
        """
        print("\n--- Estabilidade Temporal de Edge (Retorno 5 candles) ---")
        
        states = [FlowState.ABSORPTION_BULLISH, FlowState.TRAPPED_BUYERS]
        results = []
        
        # Adicionar retornos forward
        df = df.with_columns([
            (pl.col("close").shift(-5) / pl.col("close") - 1).alias("fwd_ret_5")
        ])
        
        years = df["year"].unique().sort().to_list()
        
        for year in years:
            year_df = df.filter(pl.col("year") == year)
            for state in states:
                state_df = year_df.filter(pl.col("flow_state") == state.value)
                if len(state_df) < 5: 
                    edge = 0
                else:
                    edge = state_df["fwd_ret_5"].mean() * 10000
                
                results.append({"year": year, "state": state.name, "edge_bps": edge, "n": len(state_df)})
                
        res_df = pd.DataFrame(results)
        print(res_df.pivot(index="state", columns="year", values="edge_bps"))
        return res_df

    def full_audit(self):
        print(f"[{datetime.now()}] Iniciando Adversarial Audit...")
        df = self.load_data()
        
        # 1. Teste Adversário 2023 vs 2024
        self.run_adversarial_test(df, 2023, 2024)
        
        # 2. Teste de Estabilidade de Edge
        self.run_temporal_edge_stability(df)
        
        # 3. PSI de Features Críticas
        print("\n--- Feature Stability (PSI 2023 vs 2024) ---")
        features_to_check = ["ofi", "vol_risk_premium"]
        df_23 = df.filter(pl.col("year") == 2023)
        df_24 = df.filter(pl.col("year") == 2024)
        
        if len(df_23) > 0 and len(df_24) > 0:
            for f in features_to_check:
                if f in df.columns:
                    psi = self.calculate_psi(df_23[f].to_numpy(), df_24[f].to_numpy())
                    status = "STABLE" if psi < 0.1 else "MODERATE DRIFT" if psi < 0.25 else "SEVERE DRIFT"
                    print(f"{f}: PSI={psi:.4f} -> {status}")
        else:
            print("Amostra insuficiente para PSI (Verifique se há dados de 2023 e 2024)")

if __name__ == "__main__":
    auditor = AdversarialAuditor()
    auditor.full_audit()
