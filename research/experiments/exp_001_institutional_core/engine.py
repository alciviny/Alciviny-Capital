import polars as pl
import pandas as pd
from .models.correlation import DCCGARCHModel
from .models.regime import MarkovRegimeDetector
from .analysis.microstructure import MicrostructureAnalyzer
import logging

logger = logging.getLogger("InstitutionalEngine")

class InstitutionalCore:
    """
    Orquestrador da Suíte de Inteligência Institucional.
    Consolida modelos de regime, correlação e microestrutura.
    """
    def __init__(self):
        self.dcc = DCCGARCHModel()
        self.markov = MarkovRegimeDetector()
        self.micro = MicrostructureAnalyzer()

    def run_full_analysis(self, data: pl.DataFrame, target: str, confluences: list) -> pl.DataFrame:
        """
        Executa o pipeline completo de análise institucional.
        """
        logger.info("Iniciando Análise Institucional Completa.")
        
        # 1. Preparação de Dados
        df_pd = data.to_pandas()
        if 'date' in df_pd.columns: 
            df_pd = df_pd.set_index('date')
        elif 'time' in df_pd.columns:
            df_pd = df_pd.set_index('time')
        
        # 2. Correlação Dinâmica (DCC Proxy)
        returns = df_pd[[target] + confluences].pct_change().dropna()
        corr_df = self.dcc.estimate_dynamic_correlation(returns)
        
        # 3. Regimes de Markov (sobre o Target - agora usando Log Returns internos no modelo)
        # O modelo agora recebe Preços e calcula os Log Returns internamente de forma robusta
        regimes = self.markov.detect(df_pd[target])
        
        # 4. Consolidação
        # Identificar coluna temporal para o join
        join_col = "index" if "index" in corr_df.columns else "time"
        
        # Garantir que o index dos regimes (datetime) seja compatível para o join
        regimes_pl = pl.from_pandas(regimes.reset_index())
        if join_col in regimes_pl.columns:
            res_pl = corr_df.join(regimes_pl, on=join_col, how="left")
        else:
            # Fallback se reset_index der nome diferente
            res_pl = pl.concat([corr_df, regimes_pl.drop(regimes_pl.columns[0])], how="horizontal")
        
        # 5. Análise de Microestrutura (R2)
        for conf in confluences:
            res_pl = self.micro.rolling_r2(res_pl, target, conf)
            
        logger.info("Análise Institucional concluída com sucesso.")
        return res_pl
