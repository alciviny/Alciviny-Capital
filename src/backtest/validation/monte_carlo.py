import polars as pl
import numpy as np
from typing import List, Dict, Any

class MonteCarloSimulator:
    """
    Simula variações estatísticas para testar a robustez da estratégia.
    """
    
    def __init__(self, trades_pnl: pl.Series):
        self.pnl = trades_pnl.to_numpy()

    def run_simulation(self, n_simulations: int = 1000) -> Dict[str, Any]:
        """
        Executa simulações de re-amostragem (Bootstrap) para verificar a estabilidade.
        """
        results = []
        max_drawdowns = []
        
        for _ in range(n_simulations):
            # Re-amostragem com reposição (Bootstrap)
            sim_pnl = np.random.choice(self.pnl, size=len(self.pnl), replace=True)
            equity = np.cumsum(sim_pnl)
            
            # Cálculo de Drawdown para esta simulação
            peak = np.maximum.accumulate(equity + 100)
            dd = ((equity + 100) - peak) / peak
            
            results.append(equity[-1])
            max_drawdowns.append(np.min(dd) * 100)
            
        return {
            "mean_return": np.mean(results),
            "median_return": np.median(results),
            "std_return": np.std(results),
            "worst_drawdown": np.min(max_drawdowns),
            "avg_drawdown": np.mean(max_drawdowns),
            "95th_percentile_dd": np.percentile(max_drawdowns, 5) # VaR de 95% para o DD
        }
