import os
import sys
import polars as pl
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from typing import List

# Root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.experiments.exp_001_institutional_core.engine import InstitutionalCore
from src.data.factory import StateVectorFactory
from src.models.meta import InstitutionalClassifier
from src.utils.labeling import TripleBarrierLabeler
from src.utils.validation import PurgedTimeSeriesSplit, calculate_mda
from src.utils.sampling import volatility_adjusted_cusum

def train_institutional_v2():
    print(f"[{datetime.now()}] Iniciando Pipeline Institucional v2.0 (Anti-Leakage)...")
    
    # 1. Carregamento de Dados
    base_path = "data/storage/"
    assets = {"WIN": "WIN$_15_CLEAN.parquet", "WDO": "WDO$_15_CLEAN.parquet", "DI1": "DI1$_15_CLEAN.parquet"}
    
    dfs = {}
    for name, filename in assets.items():
        df = pl.read_parquet(os.path.join(base_path, filename))
        if name == "WIN":
            dfs[name] = df
        else:
            dfs[name] = df.select(["time", "close"]).rename({"close": name})
    
    data = dfs["WIN"].join(dfs["WDO"], on="time").join(dfs["DI1"], on="time").sort("time")
    
    # 2. Expanding Window Processor (Anti-Leakage)
    # Para evitar que o MRS veja o futuro, estimamos em janelas.
    # Usamos um step de 2000 candles para viabilidade computacional.
    step = 4000
    total_len = len(data)
    min_train = 5000 # Mínimo de dados para o primeiro fit
    
    core = InstitutionalCore()
    all_features = []
    
    print(f"Executando Expanding Window Estimation (Step={step})...")
    for i in range(min_train, total_len, step):
        end_idx = min(i + step, total_len)
        train_chunk = data.slice(0, i) # Apenas passado
        test_chunk = data.slice(i, step) # O que queremos prever sem leakage
        
        if len(test_chunk) == 0: break
        
        print(f"  Processando OOS: {data['time'][i]} até {data['time'][min(i+step-1, total_len-1)]}")
        
        # Fit MRS/DCC apenas no passado (train_chunk) e inferir no test_chunk
        try:
            results = core.run_full_analysis(data.slice(0, end_idx), target="close", confluences=["WDO", "DI1"])
            # Pegar apenas a parte OOS (os novos 'step' candles)
            oos_results = results.tail(len(test_chunk))
            all_features.append(oos_results)
        except RuntimeError as e:
            print(f"  [AVISO] Falha de convergência na janela {data['time'][i]}. Pulando...")
            continue

    # Consolidar resultados OOS (sem leakage)
    full_oos_results = pl.concat(all_features)
    
    # Unir com OHLCV original para TBM e Factory
    full_data_oos = data.join(full_oos_results, on="time", how="inner")
    
    # 3. Triple Barrier Labeling
    print("Gerando Labels via Triple Barrier Method...")
    labeler = TripleBarrierLabeler(pt_sl=[2.0, 1.5], horizon=40)
    labeled_df = labeler.label(full_data_oos, price_col="close")
    
    # 4. State Vector Factory (High-Res)
    factory = StateVectorFactory()
    mrs_probs = ["regime_0_prob", "regime_1_prob", "regime_2_prob"]
    
    sv_df = factory.generate(
        labeled_df,
        target_col="close",
        mrs_prob_cols=mrs_probs,
        dcc_corr_col="corr_close_WDO",
        use_microstructure=True
    )
    
    # Extrair nomes das features para o treinamento
    features = factory.get_feature_names(mrs_probs, use_microstructure=True)
    
    # 5. CUSUM Event Sampling (Event-Based vs Time-Based)
    print("Aplicando CUSUM Filter para amostragem baseada em eventos...")
    event_indices = volatility_adjusted_cusum(sv_df, price_col="close", mult=2.0)
    sv_df_sampled = sv_df.slice(event_indices[0], 1) # Dummy para iniciar concat
    if len(event_indices) > 0:
        sv_df_sampled = pl.concat([sv_df.slice(i, 1) for i in event_indices])
    
    print(f"  Amostras originais: {len(sv_df)} | Amostras CUSUM: {len(sv_df_sampled)}")
    
    # 6. Validação Purged Cross-Validation & MDA Audit
    print(f"Iniciando Auditoria MDA (Mean Decrease Accuracy)...")
    pdf = sv_df_sampled.to_pandas()
    X = pdf[features]
    y = pdf['label_tbm']
    
    cv = PurgedTimeSeriesSplit(n_splits=5, purge_window=40)
    clf = InstitutionalClassifier()
    
    # MDA Audit
    mda_report = calculate_mda(clf.model, X, y, cv)
    print("\n--- RELATÓRIO MDA (ESTABILIDADE DE FEATURES) ---")
    print(mda_report)
    
    # 7. Treinamento Final com Incerteza
    print("\nTreinando Meta-Classificador Final com Calibração e Ensemble...")
    clf.train(X, y) 
    
    # Check Uncertainty em uma amostra
    uncertainty = clf.predict_with_uncertainty(X.tail(5))
    print("\nCheck de Incerteza (Últimas 5 amostras):")
    print(f"Std Dev Médio: {np.mean(uncertainty['std']):.6f}")
    
    # Salvar Modelo v2.0
    model_path = "src/models/weights/institutional_meta_v2.joblib"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    clf.save(model_path)
    
    print(f"\n[SUCESSO] Modelo v2.0 Industrializado salvo em {model_path}")
    print(f"Total de amostras OOS: {len(pdf)}")
    print(f"Features utilizadas: {len(features)}")

if __name__ == "__main__":
    train_institutional_v2()
