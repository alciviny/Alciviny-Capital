import sys
import os
import polars as pl
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Garantir que o root do projeto está no sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from research.experiments.exp_001_institutional_core.engine import InstitutionalCore

def load_real_data():
    """Carrega e alinha dados reais de WIN, WDO e DI1."""
    base_path = "data/storage/"
    assets = {
        "WIN": "WIN$_15_CLEAN.parquet",
        "WDO": "WDO$_15_CLEAN.parquet",
        "DI1": "DI1$_15_CLEAN.parquet"
    }
    
    dfs = {}
    for name, filename in assets.items():
        path = os.path.join(base_path, filename)
        if not os.path.exists(path):
            print(f"Erro: Arquivo não encontrado: {path}")
            return None
        
        # Carregar e selecionar apenas colunas essenciais
        df = pl.read_parquet(path).select(["time", "close"])
        df = df.rename({"close": name})
        dfs[name] = df
    
    # Alinhamento pelo tempo (Inner Join)
    combined = dfs["WIN"].join(dfs["WDO"], on="time").join(dfs["DI1"], on="time")
    combined = combined.sort("time").tail(12000)
    
    return combined

def run_experiment():
    print(f"[{datetime.now()}] Iniciando Experimento EXP-001 com dados reais...")
    
    data = load_real_data()
    if data is None: return
    
    print(f"Dados carregados: {len(data)} candles alinhados.")
    
    # Inicializar Engine
    core = InstitutionalCore()
    
    # Rodar Pipeline
    results = core.run_full_analysis(data, target="WIN", confluences=["WDO", "DI1"])
    
    # --- SALVAR RESULTADOS ---
    exp_dir = "research/experiments/exp_001_institutional_core"
    
    # 1. Salvar Métricas em CSV
    metrics_path = os.path.join(exp_dir, "results", "real_metrics.csv")
    results.write_csv(metrics_path)
    print(f"Métricas salvas em: {metrics_path}")
    
    # 2. Gerar Gráficos
    print("Gerando gráficos de correlação e regimes...")
    
    # Converter para pandas para facilitar o plot
    res_pd = results.to_pandas()
    # Encontrar a coluna de tempo (pode ser 'index' ou 'time')
    time_col = 'index' if 'index' in res_pd.columns else 'time'
    res_pd = res_pd.set_index(time_col)
    
    # Já temos os preços originais nos resultados
    # res_pd = res_pd.join(data_pd, how='inner')
    
    plt.figure(figsize=(15, 12))
    
    plt.subplot(3, 1, 1)
    plt.plot(res_pd.index, res_pd['WIN'], label='WIN', color='black', alpha=0.4)
    plt.title("WIN Price & Semantic Markov Regimes")
    
    if 'regime_name' in res_pd.columns:
        colors = {'BULL': 'green', 'BEAR': 'red', 'CRISIS': 'orange', 'UNKNOWN': 'gray'}
        for r_name in res_pd['regime_name'].unique():
            mask = res_pd['regime_name'] == r_name
            plt.scatter(res_pd.index[mask], res_pd['WIN'][mask], 
                        s=7, label=f'Estado: {r_name}', color=colors.get(r_name, 'gray'), alpha=0.6)
    plt.legend()

    plt.subplot(3, 1, 2)
    # Procurar colunas de correlação
    corr_cols = [c for c in res_pd.columns if 'corr' in c]
    for col in corr_cols:
        plt.plot(res_pd.index, res_pd[col], label=col)
    plt.axhline(0, color='black', linestyle='--')
    plt.title("Dynamic Conditional Correlation (DCC-GARCH Proxy)")
    plt.legend()

    plt.subplot(3, 1, 3)
    r2_cols = [c for c in res_pd.columns if 'r2' in c]
    for col in r2_cols:
        plt.plot(res_pd.index, res_pd[col], label=col)
    plt.title("Lead-Lag Strength (Rolling R²)")
    plt.legend()

    plt.tight_layout()
    plot_path = os.path.join(exp_dir, "plots", "institutional_dynamics.png")
    plt.savefig(plot_path)
    print(f"Gráfico salvo em: {plot_path}")
    
    # 3. Relatório de Auditoria de Confiança
    print(core.markov.get_confidence_report())
    
    print(f"\n[{datetime.now()}] Experimento EXP-001 Concluído.")

if __name__ == "__main__":
    run_experiment()
