import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.experiments.exp_001_institutional_core.engine import InstitutionalCore
from src.data.factory import StateVectorFactory
from src.models.meta import InstitutionalClassifier

def run_walk_forward_analysis():
    print(f"[{datetime.now()}] Iniciando Walk-Forward Analysis (WFA)...")
    
    # 1. Carregar dados históricos (15min)
    base_path = "data/storage/"
    win = pl.read_parquet(base_path + "WIN$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "WIN"})
    wdo = pl.read_parquet(base_path + "WDO$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "WDO"})
    di1 = pl.read_parquet(base_path + "DI1$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "DI1"})
    data = win.join(wdo, on="time").join(di1, on="time").sort("time")
    
    # Configurações de Janela
    train_months = 12
    test_months = 3
    
    start_date = data["time"].min()
    end_date = data["time"].max()
    
    curr_train_start = start_date
    results_oos = []

    core = InstitutionalCore()
    factory = StateVectorFactory()
    
    while True:
        train_end = curr_train_start + timedelta(days=30 * train_months)
        test_end = train_end + timedelta(days=30 * test_months)
        
        if test_end > end_date:
            break
            
        print(f"\nJanela: Treino até {train_end.date()} | Teste até {test_end.date()}")
        
        # Filtrar Dados
        train_data = data.filter((pl.col("time") >= curr_train_start) & (pl.col("time") < train_end))
        test_data = data.filter((pl.col("time") >= train_end) & (pl.col("time") < test_end))
        
        if len(train_data) < 1000 or len(test_data) < 100:
            curr_train_start += timedelta(days=30 * test_months)
            continue

        # --- TREINO ---
        train_results = core.run_full_analysis(train_data, target="WIN", confluences=["WDO", "DI1"])
        bull_id = next(k for k, v in core.markov.regime_map.items() if v == "BULL")
        
        sv_train = factory.generate(train_results, "WIN", f"regime_{bull_id}_prob", "corr_WIN_WDO")
        sv_train = sv_train.with_columns([
            ((pl.col("WIN").shift(-30) / pl.col("WIN") - 1)).alias("fwd_ret")
        ]).drop_nulls()
        
        pdf_train = sv_train.to_pandas()
        # Hybrid Labeling simples para o audit
        pdf_train['label'] = (pdf_train['regime_name'] == "BULL").astype(int)
        
        clf = InstitutionalClassifier()
        clf.train(pdf_train[factory.get_feature_names()], pdf_train['label'])
        
        # --- TESTE (OOS) ---
        test_results = core.run_full_analysis(test_data, target="WIN", confluences=["WDO", "DI1"])
        sv_test = factory.generate(test_results, "WIN", f"regime_{bull_id}_prob", "corr_WIN_WDO")
        sv_test = sv_test.with_columns([
            ((pl.col("WIN").shift(-30) / pl.col("WIN") - 1)).alias("fwd_ret")
        ]).drop_nulls()
        
        pdf_test = sv_test.to_pandas()
        probs = clf.predict_proba(pdf_test[factory.get_feature_names()])
        
        # Calcular Sharpe da Janela OOS
        returns = (probs[:, 1] > 0.6).astype(float) * pdf_test['fwd_ret']
        sharpe = (returns.mean() / returns.std() * np.sqrt(28 * 252)) if returns.std() > 0 else 0
        
        results_oos.append({
            "window_end": train_end,
            "oos_sharpe": sharpe,
            "samples": len(pdf_test)
        })
        
        print(f"  OOS Sharpe: {sharpe:.2f}")
        
        # Deslocar Janela
        curr_train_start += timedelta(days=30 * test_months)

    # Relatório Final
    df_wfa = pd.DataFrame(results_oos)
    print("\n--- Relatório Final Walk-Forward ---")
    print(df_wfa)
    print(f"\nSharpe Médio OOS: {df_wfa['oos_sharpe'].mean():.2f}")
    print(f"Estabilidade (Std Sharpe): {df_wfa['oos_sharpe'].std():.2f}")

if __name__ == "__main__":
    run_walk_forward_analysis()
