import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime

# Root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.experiments.exp_001_institutional_core.engine import InstitutionalCore
from src.data.factory import StateVectorFactory
from src.models.meta import InstitutionalClassifier

def train_institutional_meta_model():
    print(f"[{datetime.now()}] Iniciando Treinamento do Meta-Classificador...")
    
    # 1. Carregamento de Dados (15-min para estabilidade)
    base_path = "data/storage/"
    assets = {
        "WIN": "WIN$_15_CLEAN.parquet",
        "WDO": "WDO$_15_CLEAN.parquet",
        "DI1": "DI1$_15_CLEAN.parquet"
    }
    
    dfs = {}
    for name, filename in assets.items():
        # Carregar OHLCV completo para microestrutura
        df = pl.read_parquet(os.path.join(base_path, filename))
        if name == "WIN":
            # Manter nomes originais para o target (usado pelo OFIEngine)
            dfs[name] = df
        else:
            # Outros ativos apenas close
            dfs[name] = df.select(["time", "close"]).rename({"close": name})
    
    data = dfs["WIN"].join(dfs["WDO"], on="time").join(dfs["DI1"], on="time").sort("time")
    # data = data.tail(15000) # Usar amostra grande para treino
    
    # 2. Executar Análise Institucional (MRS + DCC)
    core = InstitutionalCore()
    analysis_results = core.run_full_analysis(data, target="close", confluences=["WDO", "DI1"])
    
    # Unir as colunas originais (OHLCV) de volta para a microestrutura
    results = data.join(analysis_results, on="time", how="inner")
    
    # 3. Gerar State Vector
    # MRS Column: 'regime_0_prob' (Statsmodels prob do regime 0 - BULL)
    # DCC Column: 'corr_WIN_WDO'
    factory = StateVectorFactory()
    mrs_probs = ["regime_0_prob", "regime_1_prob", "regime_2_prob"]
    
    sv_df = factory.generate(
        results, 
        target_col="close", 
        mrs_prob_cols=mrs_probs, 
        dcc_corr_col="corr_close_WDO",
        use_microstructure=True # Ativar OFI e VRP
    )
    
    # 4. Hybrid Labeling (Anti-Circularidade)
    # Forward Return N=30
    sv_df = sv_df.with_columns([
        ((pl.col("close").shift(-30) - pl.col("close")) / pl.col("close")).alias("fwd_ret")
    ]).drop_nulls()
    
    # Mapeamento de Labels: 0: BEAR, 1: BULL, 2: CRISIS
    label_map = {"BEAR": 0, "BULL": 1, "CRISIS": 2}
    
    def calculate_hybrid_label(row):
        regime = row['regime_name']
        fwd_ret = row['fwd_ret']
        
        label = label_map.get(regime, 0)
        weight = 1.0
        
        # Lógica de validação por retorno
        if regime == "BULL" and fwd_ret < -0.001:
            weight = 0.3 # Penaliza MRS quando errou a direção futura
        elif regime == "BEAR" and fwd_ret > 0.001:
            weight = 0.3
            
        return pd.Series([label, weight])

    # Converter para Pandas para o apply (mais fácil para lógica condicional complexa)
    pdf = sv_df.to_pandas()
    pdf[['label', 'weight']] = pdf.apply(calculate_hybrid_label, axis=1)
    
    # 5. Treinamento
    features = factory.get_feature_names(mrs_probs, use_microstructure=True)
    X = pdf[features]
    y = pdf['label']
    weights = pdf['weight']
    
    model_path = "src/models/weights/institutional_meta_v1.joblib"
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    clf = InstitutionalClassifier(model_path=model_path)
    clf.train(X, y, sample_weights=weights)
    
    print(f"[{datetime.now()}] Treinamento Concluído.")
    print("Importância das Features:")
    print(clf.get_feature_importance(features))
    
    return clf

if __name__ == "__main__":
    train_institutional_meta_model()
