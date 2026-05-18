import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.indicators.microstructure import add_microstructure_indicators, FlowState

class ToxicFillAuditor:
    def __init__(self, asset: str = "WDO", tf: str = "5"):
        self.asset = asset
        self.tf = tf
        self.base_path = r"c:\Users\JC INFO\Documents\AlcivinyEdger\data\storage"
        
        if asset == "WDO":
            self.tick_size = 0.5
            self.contract_value = 10.0
            self.fee_bps = 0.3 # Estimativa simplificada
        else:
            self.tick_size = 5.0
            self.contract_value = 0.2
            self.fee_bps = 0.1

    def load_data(self) -> pl.DataFrame:
        clean_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}_CLEAN.parquet")
        base_path = os.path.join(self.base_path, f"{self.asset}$_{self.tf}.parquet")
        path = clean_path if os.path.exists(clean_path) else base_path
        
        df = pl.read_parquet(path)
        df = add_microstructure_indicators(df)
        
        # Adicionar features de execução (Queue Imbalance & Momentum curto)
        df = df.with_columns([
            (pl.col("close") / pl.col("close").shift(1) - 1).alias("mom_1"),
            (pl.col("ofi").rolling_mean(window_size=3)).alias("ofi_3"),
            (pl.col("vol_risk_premium").rolling_mean(window_size=3)).alias("vrp_3")
        ])
        return df

    def research_toxic_fills(self, df: pl.DataFrame):
        print(f"\n--- TOXIC FILL RESEARCH: {self.asset} {self.tf}m ---")
        
        target_state = FlowState.TRAPPED_BUYERS
        state_df = df.filter(pl.col("flow_state") == target_state.value).drop_nulls()
        
        if len(state_df) < 50: 
            print("Amostra insuficiente para pesquisa de toxicidade.")
            return
            
        # 1. Definir Alvo de Toxicidade
        # Toxicidade = Preço se move CONTRA nós (Up para Short) no t+1 ou t+2
        # No WDO, se mover > 1 tick (0.5 pt) é tóxico.
        side = -1 # Trapped Buyers = SELL
        toxic_move = (pl.col("close").shift(-2) / pl.col("close") - 1) * -side # Positivo se contra nós
        state_df = state_df.with_columns([
            (toxic_move > (self.tick_size / pl.col("close"))).cast(pl.Int8).alias("is_toxic")
        ]).drop_nulls()
        
        # 2. Treinar Preditor de Toxicidade (Informação disponível no t=0)
        features = ["ofi", "vol_risk_premium", "mom_1", "ofi_3", "vrp_3"]
        X = state_df.select(features).to_pandas()
        y = state_df["is_toxic"].to_numpy()
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=False)
        
        clf = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42)
        clf.fit(X_train, y_train)
        
        probs = clf.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, probs)
        print(f"Toxic Fill Predictor AUC: {auc:.4f}")
        
        # 3. Simular Política de Execução Inteligente
        test_df = state_df.tail(len(y_test)).with_columns([
            pl.Series(name="toxic_prob", values=probs)
        ])
        
        # Cenário Baseline: Sempre Agressivo (do auditor anterior)
        # Assumimos que o alpha líquido bruto era ~17 bps
        baseline_net = (pl.col("close").shift(-5) / pl.col("close") - 1) * side * 10000 - 1.5 # 1.5 bps de custo fixo
        
        # Cenário Proposto: Execution Policy
        # - Prob > 0.65 -> SKIP (Evita adverse selection)
        # - Prob < 0.35 -> PASSIVE (Ganha spread)
        # - Else -> AGGRESSIVE
        
        policy_net = (
            pl.when(pl.col("toxic_prob") > 0.65).then(0.0) # SKIP
            .when(pl.col("toxic_prob") < 0.35).then(baseline_net + 2.0) # PASSIVE (+2 bps spread)
            .otherwise(baseline_net) # AGGRESSIVE
        )
        
        res = test_df.select([
            baseline_net.mean().alias("baseline_net_bps"),
            policy_net.mean().alias("policy_net_bps")
        ])
        
        print("\n--- EXECUTION POLICY PERFORMANCE ---")
        print(f"Baseline Net Alpha: {res[0,0]:.2f} bps")
        print(f"Smart Policy Alpha: {res[0,1]:.2f} bps")
        improvement = ((res[0,1] / res[0,0]) - 1) * 100 if res[0,0] > 0 else 0
        print(f"Improvement: {improvement:.2f}%")
        
        # 4. Semantic Asset Layer (WDO Informed vs WIN Toxic)
        if self.asset == "WDO":
            print("\nSEMANTIC LAYER: WDO identificado como 'Informed Flow'.")
        else:
            print("\nSEMANTIC LAYER: WIN identificado como 'Exit Trap' (High Toxicity).")

if __name__ == "__main__":
    # WDO
    auditor = ToxicFillAuditor(asset="WDO", tf="5")
    df = auditor.load_data()
    auditor.research_toxic_fills(df)
    
    # WIN
    print("\n" + "="*50 + "\n")
    auditor_win = ToxicFillAuditor(asset="WIN", tf="5")
    df_win = auditor_win.load_data()
    auditor_win.research_toxic_fills(df_win)
