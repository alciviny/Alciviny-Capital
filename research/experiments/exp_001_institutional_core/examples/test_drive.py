import polars as pl
import numpy as np
import sys
import os

# Adicionar a raiz do projeto ao path para importação local
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from research.institutional_engine.engine import InstitutionalCore

def generate_mock_institutional_data(n=1000):
    """Gera dados que simulam o Tripé de Risco Brasileiro."""
    np.random.seed(42)
    
    # Target: WIN (Ações)
    win_ret = np.random.randn(n) * 0.01
    
    # Confluência: WDO (Dólar) - Correlação negativa que aumenta em crises
    wdo_ret = -0.6 * win_ret + np.random.randn(n) * 0.005
    
    # Confluência: DI (Juros)
    di_ret = -0.4 * win_ret + np.random.randn(n) * 0.002
    
    # Criando regimes (Volatilidade aumenta no final)
    win_ret[800:] = win_ret[800:] * 3 
    wdo_ret[800:] = wdo_ret[800:] * 3
    
    return pl.DataFrame({
        "index": np.arange(n),
        "win": np.cumsum(win_ret) + 100,
        "wdo": np.cumsum(wdo_ret) + 5,
        "di": np.cumsum(di_ret) + 12
    })

def main():
    print("--- INICIANDO TESTE DRIVE INSTITUCIONAL ---")
    data = generate_mock_institutional_data()
    
    core = InstitutionalCore()
    results = core.run_full_analysis(data, target="win", confluences=["wdo", "di"])
    
    print("\nResultados da Análise (Primeiras 5 linhas):")
    print(results.head())
    
    print("\nResumo de Regimes Detectados:")
    regime_counts = results.group_by("dominant_regime").count()
    print(regime_counts)
    
    print("\n--- TESTE CONCLUÍDO COM SUCESSO ---")

if __name__ == "__main__":
    main()
