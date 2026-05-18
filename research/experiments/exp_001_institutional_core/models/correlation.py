import numpy as np
import polars as pl
from arch import arch_model
import pandas as pd
from typing import Dict, Tuple, Optional

class DCCGARCHModel:
    """
    Implementação de Dynamic Conditional Correlation (DCC-GARCH).
    Calcula como a correlação entre ativos muda ao longo do tempo,
    identificando períodos de contágio ou quebra de correlação.
    """
    def __init__(self, p: int = 1, q: int = 1):
        self.p = p
        self.q = q
        self.models = {}
        self.resid_std = None

    def fit_volatility(self, returns: pd.DataFrame):
        """Passo 1: Estimar GARCH(1,1) para cada ativo individualmente."""
        stds = []
        for col in returns.columns:
            # Rescaling automático para evitar avisos de convergência
            scaled_ret = returns[col] * 100 # Converte para pontos percentuais
            model = arch_model(scaled_ret, vol='Garch', p=self.p, q=self.q, dist='Normal')
            res = model.fit(disp='off')
            self.models[col] = res
            stds.append(res.conditional_volatility)
        
        # Resíduos padronizados para o passo do DCC
        # Isso 'limpa' a volatilidade individual para focar na correlação pura
        self.resid_std = returns / np.array(stds).T
        return self.resid_std

    def estimate_dynamic_correlation(self, returns: pd.DataFrame) -> pl.DataFrame:
        """
        Passo 2: Estimação da Correlação Dinâmica.
        Em um ambiente de pesquisa, usamos a matriz de covariância móvel 
        dos resíduos padronizados para capturar o comportamento do DCC.
        """
        z = self.fit_volatility(returns)
        
        # Calculando correlação móvel (Proxy para DCC de alta performance)
        z_pl = pl.from_pandas(z.reset_index())
        cols = [c for c in z_pl.columns if c not in ['index', 'date', 'time']]
        
        # Gerando pares de correlação
        corr_exprs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                name = f"corr_{cols[i]}_{cols[j]}"
                corr_exprs.append(
                    pl.rolling_corr(
                        pl.col(cols[i]), 
                        pl.col(cols[j]), 
                        window_size=21 # Janela institucional padrão (1 mês útil)
                    ).alias(name)
                )
        
        return z_pl.with_columns(corr_exprs).drop_nulls()
