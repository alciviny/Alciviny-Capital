import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.meta import InstitutionalClassifier
from src.data.factory import StateVectorFactory

def audit_feature_integrity(model_path: str):
    print(f"[{datetime.now()}] Iniciando Auditoria de Features (Anti-Overfit)...")
    
    clf = InstitutionalClassifier(model_path=model_path)
    
    # 1. Extração de Importância por diferentes métricas
    # Gain: Importância real para predição (o que SHAP mede melhor)
    # Weight: Frequência com que a feature aparece
    # Cover: Quantidade de amostras afetadas
    
    booster = clf.model.get_booster()
    
    metrics = ['gain', 'weight', 'cover']
    importance_data = {}
    
    for metric in metrics:
        importance_data[metric] = booster.get_score(importance_type=metric)
        
    # Consolidar em DataFrame
    df_imp = pd.DataFrame(importance_data).fillna(0)
    
    # Traduzir nomes de features se necessário (f0, f1... -> nomes reais)
    # No nosso caso, o XGBoost salva com os nomes se o fit recebeu Pandas
    
    print("\n--- Ranking de Importância (GAIN) ---")
    print(df_imp.sort_values('gain', ascending=False))
    
    # 2. Diagnóstico de Overfit
    # Se 'weight' for muito alto mas 'gain' for muito baixo -> Feature Ruidosa (decorou o treino)
    # Se 'gain' for concentrado em uma única feature -> Modelo Frágil (colapsou em um sinal)
    
    max_gain_ratio = df_imp['gain'].max() / df_imp['gain'].sum()
    if max_gain_ratio > 0.6:
        print("\n[AVISO] Concentração excessiva em uma feature. Risco de fragilidade.")
    
    # 3. Gerar Gráfico de Auditoria
    plt.figure(figsize=(10, 6))
    df_imp['gain'].sort_values().plot(kind='barh', color='skyblue')
    plt.title("Auditoria de Features: Ganho de Informação por Dimensão")
    plt.xlabel("Total Gain")
    
    plot_path = "research/experiments/exp_001_institutional_core/plots/feature_audit.png"
    os.makedirs(os.path.dirname(plot_path), exist_ok=True)
    plt.savefig(plot_path)
    print(f"\nGráfico de auditoria salvo em: {plot_path}")

if __name__ == "__main__":
    model_path = "src/models/weights/institutional_meta_v1.joblib"
    if os.path.exists(model_path):
        audit_feature_integrity(model_path)
    else:
        print("Erro: Modelo não encontrado.")
