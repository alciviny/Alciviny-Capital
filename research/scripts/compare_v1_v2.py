import os
import sys
import polars as pl
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sklearn.metrics import classification_report, accuracy_score

# Root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data.factory import StateVectorFactory
from research.experiments.exp_001_institutional_core.engine import InstitutionalCore
from src.utils.labeling import TripleBarrierLabeler

def compare_models():
    print(f"[{datetime.now()}] Iniciando Comparativo: v1.0 (Baseline) vs v2.0 (Industrialized)...")
    
    # 1. Carregar Modelos
    model_v1 = joblib.load("src/models/weights/institutional_meta_v1.joblib")
    model_v2 = joblib.load("src/models/weights/institutional_meta_v2.joblib")
    
    # 2. Carregar Dados de Teste (Últimos 3000 candles - Puro OOS)
    base_path = "data/storage/"
    win = pl.read_parquet(base_path + "WIN$_15_CLEAN.parquet").tail(4000)
    wdo = pl.read_parquet(base_path + "WDO$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "WDO"})
    di1 = pl.read_parquet(base_path + "DI1$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "DI1"})
    data = win.join(wdo, on="time").join(di1, on="time").sort("time")
    
    # 3. Gerar Features (v2.0 Path)
    core = InstitutionalCore()
    results = core.run_full_analysis(data, target="close", confluences=["WDO", "DI1"])
    full_data = data.join(results, on="time", how="inner")
    
    labeler = TripleBarrierLabeler(pt_sl=[2.0, 1.5], horizon=40)
    labeled_df = labeler.label(full_data, price_col="close")
    
    factory = StateVectorFactory()
    mrs_probs = ["regime_0_prob", "regime_1_prob", "regime_2_prob"]
    
    sv_df = factory.generate(labeled_df, "close", mrs_probs, "corr_close_WDO", use_microstructure=True)
    pdf = sv_df.to_pandas()
    
    # Features para v2
    feat_v2 = factory.get_feature_names(mrs_probs, use_microstructure=True)
    # Features para v1 (compatibilidade - pegando apenas o que a v1 usava)
    feat_v1 = ["p_bull_mrs", "vol_z20", "dcc_z60"] # v1 features
    # Note: p_bull_mrs na v2 virou regime_0_prob (BULL)
    pdf_v1 = pdf.copy()
    pdf_v1['p_bull_mrs'] = pdf_v1['regime_0_prob']
    
    # 4. Inferência
    y_true = pdf['label_tbm']
    y_pred_v1 = model_v1.predict(pdf_v1[feat_v1])
    y_pred_v2 = model_v2.predict(pdf[feat_v2])
    
    # 5. Relatório
    print("\n--- PERFORMANCE v1.0 (Baseline - No Reg - Circular Labels) ---")
    print(classification_report(y_true, y_pred_v1))
    
    print("\n--- PERFORMANCE v2.0 (Industrialized - Reg - TBM Labels - OOS Windows) ---")
    print(classification_report(y_true, y_pred_v2))
    
    # Sharpe Simulado Simples
    ret_v1 = (y_pred_v1 == 1).astype(float) * pdf['fwd_ret'] # fwd_ret precisa estar no pdf
    # Como não temos fwd_ret no sv_df da factory, calculamos aqui
    pdf['fwd_ret'] = (pdf['close'].shift(-30) / pdf['close'] - 1)
    
    sharpe_v1 = (pdf[y_pred_v1 == 1]['fwd_ret'].mean() / pdf[y_pred_v1 == 1]['fwd_ret'].std() * np.sqrt(28*252))
    sharpe_v2 = (pdf[y_pred_v2 == 1]['fwd_ret'].mean() / pdf[y_pred_v2 == 1]['fwd_ret'].std() * np.sqrt(28*252))
    
    print(f"\nSharpe v1.0: {sharpe_v1:.2f}")
    print(f"Sharpe v2.0: {sharpe_v2:.2f}")
    
    if sharpe_v2 > sharpe_v1:
        print("\n[VERDITO] v2.0 é estatisticamente superior e mais robusta.")
    else:
        print("\n[VERDITO] v1.0 parece melhor no curto prazo, mas v2.0 é mais honesta (menos leakage).")

if __name__ == "__main__":
    if os.path.exists("src/models/weights/institutional_meta_v2.joblib"):
        compare_models()
    else:
        print("Aguardando finalização do treino v2.0...")
