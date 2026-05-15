import numpy as np
import pandas as pd
import polars as pl
import logging
from typing import Dict, Tuple, List, Optional
from sklearn.decomposition import PCA
from statsmodels.tsa.stattools import adfuller
from src.indicators.regime.utils import validate_regime_data

logger = logging.getLogger("AlcivinyEdger.Regime.FCI")

class FinancialConditionsIndex:
    """
    Índice de Condições Financeiras (FCI) dinâmico baseado em PCA.
    Otimizado para produção.
    """

    def __init__(self, 
                 rolling_window: int = 252,
                 feature_window: int = 21,
                 crisis_val: float = 2.5,
                 crisis_ve: float = 0.45,
                 stress_threshold: float = 1.5,
                 tightening_threshold: float = 0.5,
                 expansion_threshold: float = -0.5,
                 pos_full: float = 1.0,
                 pos_moderate: float = 0.6,
                 pos_low: float = 0.3,
                 pos_flat: float = 0.0):
        self.rolling_window = rolling_window
        self.feature_window = feature_window
        self.thresholds = {
            'crisis_val': crisis_val,
            'crisis_ve': crisis_ve,
            'stress': stress_threshold,
            'tightening': tightening_threshold,
            'expansion': expansion_threshold
        }
        self.position_sizing = {
            'FULL': pos_full,
            'MODERATE': pos_moderate,
            'LOW': pos_low,
            'FLAT': pos_flat
        }

        self.data = None
        self.features = None
        self.fci = None
        self.ve1 = None
        self.regime_df = None

    def preprocess(self, data: pd.DataFrame) -> None:
        """Pré-processamento FCI otimizado via Polars."""
        logger.info("Iniciando pré-processamento FCI.")
        data = validate_regime_data(data, ['ibov', 'dol', 'di1'])
        
        df_pl = pl.from_pandas(data.reset_index())
        
        # Construção de Features via Polars (Vetorizado)
        df_pl = df_pl.with_columns([
            (pl.col('ibov').replace(0, np.nan).log().diff()).alias('r_ibov_raw'),
            (pl.col('dol').replace(0, np.nan).log().diff()).alias('r_dol_raw'),
            (pl.col('di1').diff()).alias('di1_diff')
        ])
        
        df_pl = df_pl.with_columns([
            pl.col('r_ibov_raw').rolling_sum(self.feature_window).alias('ibov_ret_21'),
            pl.col('r_ibov_raw').rolling_std(self.feature_window).alias('ibov_vol_21'),
            pl.col('r_dol_raw').rolling_sum(self.feature_window).alias('dol_ret_21'),
            pl.col('r_dol_raw').rolling_std(self.feature_window).alias('dol_vol_21'),
            pl.col('di1_diff').rolling_std(self.feature_window).alias('di1_vol_21')
        ])

        # Adicionar fatores globais se existirem
        for col in ['cds', 'embi', 'vix', 'dxy', 'commodity']:
            if col in df_pl.columns:
                if col == 'vix':
                    df_pl = df_pl.with_columns(pl.col(col).replace(0, np.nan).log().alias('vix_log'))
                else:
                    df_pl = df_pl.with_columns(pl.col(col).diff().alias(f'{col}_diff'))

        # Seleção de colunas existentes
        candidate_cols = [
            'ibov_ret_21', 'ibov_vol_21', 'dol_ret_21', 'dol_vol_21',
            'di1_diff', 'di1_vol_21', 'cds_diff', 
            'embi_diff', 'vix_log', 'dxy_diff', 'commodity_diff'
        ]
        feature_cols = [c for c in candidate_cols if c in df_pl.columns]
        
        # Filtro de estacionaridade simplificado para produção (ou assume estacionaridade nas diffs)
        # Manter limpeza e normalização expansiva
        z_df = df_pl.select(['date'] + feature_cols).drop_nulls()
        
        for col in feature_cols:
            z_df = z_df.with_columns([
                ((pl.col(col) - pl.col(col).rolling_mean(z_df.height, min_periods=1)) / 
                 pl.col(col).rolling_std(z_df.height, min_periods=1)).alias(col)
            ])
            
        self.features = z_df.drop_nulls().to_pandas().set_index('date')
        logger.info(f"Pré-processamento FCI concluído: {len(self.features)} linhas.")

    def rolling_pca(self) -> None:
        """Executa PCA em janela móvel."""
        if self.features is None:
            raise ValueError("Execute preprocess() primeiro.")

        X = self.features.values
        T, N = X.shape
        fci_vals = np.full(T, np.nan)
        ve1_vals = np.full(T, np.nan)
        prev_w = None

        logger.info(f"Iniciando PCA Dinâmico (Janela: {self.rolling_window}).")
        
        for i in range(self.rolling_window, T):
            Xw = X[i - self.rolling_window : i]
            pca = PCA(n_components=1)
            pca.fit(Xw)
            
            w = pca.components_[0]

            # Estabilização de Sinal
            if prev_w is not None:
                if np.dot(w, prev_w) < 0:
                    w = -w
            else:
                if 'ibov_ret_21' in self.features.columns:
                    ibov_idx = self.features.columns.get_loc('ibov_ret_21')
                    if w[ibov_idx] > 0: w = -w
            
            prev_w = w
            fci_vals[i] = np.dot(w, X[i])
            ve1_vals[i] = pca.explained_variance_ratio_[0]

        self.fci = pd.Series(fci_vals, index=self.features.index)
        self.ve1 = pd.Series(ve1_vals, index=self.features.index)
        logger.info("FCI Dinâmico calculado.")

    def classify_regimes(self) -> pd.DataFrame:
        """Classifica os regimes macrofinanceiros."""
        if self.fci is None:
            raise ValueError("Execute rolling_pca() primeiro.")

        # Z-Score relativo via Polars
        fci_pl = pl.DataFrame({'fci': self.fci.values})
        z = ((fci_pl['fci'] - fci_pl['fci'].rolling_mean(252)) / 
             fci_pl['fci'].rolling_std(252)).to_pandas()
        z.index = self.fci.index
        
        def _get_macro_label(val, ve):
            if pd.isna(val): return None
            if val > self.thresholds['crisis_val'] and ve > self.thresholds['crisis_ve']:
                return 'CRISIS'
            if val > self.thresholds['stress']:
                return 'STRESS'
            if val > self.thresholds['tightening']:
                return 'TIGHTENING'
            if val < self.thresholds['expansion']:
                return 'EXPANSION'
            return 'NEUTRAL'

        regimes = [
            _get_macro_label(z.iloc[i], self.ve1.iloc[i]) 
            for i in range(len(z))
        ]

        self.regime_df = pd.DataFrame({
            'fci': self.fci,
            'z_fci': z,
            've_1': self.ve1,
            'macro_regime': regimes
        }, index=self.features.index)
        
        return self.regime_df

    def compute_master_signal(self, dcc_regime: pd.Series, pe_signal: pd.Series) -> pd.DataFrame:
        """Consolidador Final."""
        if self.regime_df is None:
            self.classify_regimes()
            
        df = self.regime_df.copy()
        df['dcc_regime'] = dcc_regime
        df['pe_signal'] = pe_signal

        def _master_logic(row):
            macro, dcc, pe = row['macro_regime'], row['dcc_regime'], row['pe_signal']
            if macro in ['STRESS', 'CRISIS'] or pe == 'FLAT':
                return 'FLAT', self.position_sizing['FLAT']
            if macro == 'EXPANSION' and dcc == 'NORMAL' and pe == 'TRADE':
                return 'FULL', self.position_sizing['FULL']
            if macro == 'NEUTRAL' and dcc == 'NORMAL' and pe == 'TRADE':
                return 'MODERATE', self.position_sizing['MODERATE']
            return 'LOW', self.position_sizing['LOW']

        results = df.apply(_master_logic, axis=1)
        df['master_signal'] = [r[0] for r in results]
        df['position_size'] = [r[1] for r in results]
        return df
