import polars as pl
import numpy as np
from typing import List, Optional
from src.indicators.microstructure import OFIEngine, add_microstructure_indicators, FlowState
from src.indicators.volatility import calculate_hurst_pl

class StateVectorFactory:
    """
    Consolida múltiplos sinais institucionais em um vetor de estado normalizado.
    Especializado para o Meta-Classificador do AlcivinyEdger.
    """
    
    def __init__(self, 
                 vol_lookback: int = 20, 
                 corr_lookback: int = 60):
        self.vol_lookback = vol_lookback
        self.corr_lookback = corr_lookback

    def generate(self, 
                 df: pl.DataFrame, 
                 target_col: str,
                 mrs_prob_cols: List[str], # Lista de todas as probs
                 dcc_corr_col: str,
                 use_microstructure: bool = False) -> pl.DataFrame:
        """
        Gera o State Vector de Alta Resolução (Institutional Grade).
        """
        if isinstance(mrs_prob_cols, str):
            raise TypeError("mrs_prob_cols deve ser uma lista de strings, não uma string única.")
        
        # 1. Cálculo da Volatilidade e Incerteza (Entropia)
        # Shannon Entropy: -sum(p * log(p))
        entropy_expr = pl.lit(0.0)
        for col in mrs_prob_cols:
            # Proteção contra log(0)
            entropy_expr = entropy_expr - (pl.col(col) * (pl.col(col) + 1e-9).log())
            
        df = df.with_columns([
            (pl.col(target_col).log() - pl.col(target_col).log().shift(1)).alias("_log_ret"),
            entropy_expr.alias("regime_entropy")
        ])
        
        df = df.with_columns([
            pl.col("_log_ret").rolling_std(window_size=self.vol_lookback).alias("_raw_vol"),
            # Delta Probs (Velocidade de transição)
            *[pl.col(c).diff().alias(f"{c}_delta") for c in mrs_prob_cols]
        ])
        
        # 2. Normalização Z-Score
        df = df.with_columns([
            ((pl.col("_raw_vol") - pl.col("_raw_vol").rolling_mean(window_size=self.vol_lookback)) / 
             (pl.col("_raw_vol").rolling_std(window_size=self.vol_lookback) + 1e-9)).alias("vol_z20"),
            
            ((pl.col(dcc_corr_col) - pl.col(dcc_corr_col).rolling_mean(window_size=self.corr_lookback)) / 
             (pl.col(dcc_corr_col).rolling_std(window_size=self.corr_lookback) + 1e-9)).alias("dcc_z60")
        ])
        
        # 3. Microestrutura e Inteligência Comportamental
        if use_microstructure:
            # add_microstructure_indicators já calcula OFI, VRP e FlowStates
            df = add_microstructure_indicators(df)
            
            # Normalização das métricas contínuas
            df = df.with_columns([
                ((pl.col("cum_delta_ofi") - pl.col("cum_delta_ofi").rolling_mean(window_size=self.vol_lookback)) / 
                 (pl.col("cum_delta_ofi").rolling_std(window_size=self.vol_lookback) + 1e-9)).alias("ofi_z20"),
                ((pl.col("vol_risk_premium") - pl.col("vol_risk_premium").rolling_mean(window_size=self.vol_lookback)) / 
                 (pl.col("vol_risk_premium").rolling_std(window_size=self.vol_lookback) + 1e-9)).alias("vrp_z20"),
                calculate_hurst_pl(target_col, window=100).alias("hurst_100")
            ])
            
            # One-Hot Encoding dos Estados de Fluxo (Intenção Institucional)
            flow_states = [s.value for s in FlowState]
            for state in flow_states:
                df = df.with_columns([
                    (pl.col("flow_state") == state).cast(pl.Int8).alias(f"is_{state}")
                ])

            # Normalizar Hurst (centralizado em 0.5)
            df = df.with_columns([
                ((pl.col("hurst_100") - 0.5) / 0.1).alias("hurst_z")
            ])
        
        # Limpeza
        cols_to_drop = ["_log_ret", "_raw_vol"]
        if use_microstructure:
            cols_to_drop.extend(["ofi", "cum_delta_ofi", "vol_risk_premium", "hurst_100", "flow_state"])
            
        return df.drop(cols_to_drop).drop_nulls()

    def get_feature_names(self, mrs_prob_cols: List[str], use_microstructure: bool = False) -> List[str]:
        features = ["regime_entropy", "vol_z20", "dcc_z60"]
        features.extend(mrs_prob_cols)
        features.extend([f"{c}_delta" for c in mrs_prob_cols])
        if use_microstructure:
            features.extend(["ofi_z20", "vrp_z20", "hurst_z"])
            # Adicionar flags de estados de fluxo
            features.extend([f"is_{s.value}" for s in FlowState])
        return features
