import polars as pl
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import os

class OFISource(str, Enum):
    TICK    = "tick"     # Dados de bid/ask volume reais
    PARTIAL = "partial"  # Volume + Delta
    OHLCV   = "ohlcv"    # Estimativa via Price Action (Fallback)

class FlowState(str, Enum):
    BALANCED           = "balanced"
    ABSORPTION_BULLISH = "absorption_bullish" # Vendedores agridem, mas compradores seguram
    ABSORPTION_BEARISH = "absorption_bearish" # Compradores agridem, mas vendedores seguram
    AGGRESSIVE_BUYING  = "aggressive_buying"
    AGGRESSIVE_SELLING = "aggressive_selling"
    EXHAUSTION_BUY     = "exhaustion_buy"     # Preço sobe mas agressão some
    EXHAUSTION_SELL    = "exhaustion_sell"    # Preço cai mas agressão some
    LIQUIDITY_VACUUM   = "liquidity_vacuum"   # Preço desloca com baixo volume
    TRAPPED_BUYERS     = "trapped_buyers"     # Delta alto no topo seguido de queda
    TRAPPED_SELLERS    = "trapped_sellers"    # Delta alto no fundo seguido de alta

@dataclass
class OFIResult:
    source: OFISource
    data: pl.DataFrame
    predictiveness: Optional[Dict[int, float]] = None

class OFIEngine:
    """
    Motor de Microestrutura Institucional.
    Calcula Order Flow Imbalance (OFI) com detecção automática de schema e validação preditiva.
    """
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.source = self._detect_source(df)
        
    @classmethod
    def from_parquet(cls, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")
        df = pl.read_parquet(path)
        return cls(df)

    def _detect_source(self, df: pl.DataFrame) -> OFISource:
        cols = set(df.columns)
        if {"bid_volume", "ask_volume"}.issubset(cols):
            return OFISource.TICK
        if "delta_volume" in cols:
            return OFISource.PARTIAL
        return OFISource.OHLCV

    def calculate_ofi(self) -> pl.DataFrame:
        """
        Calcula o OFI baseado na melhor fonte disponível.
        OFI é normalizado entre -1 e 1 para estabilidade do State Vector.
        """
        if self.source == OFISource.TICK:
            # Fórmula Institucional: (V_bid - V_ask) / (V_bid + V_ask)
            ofi_expr = (pl.col("bid_volume") - pl.col("ask_volume")) / (pl.col("bid_volume") + pl.col("ask_volume") + 1e-9)
        elif self.source == OFISource.PARTIAL:
            ofi_expr = pl.col("delta_volume") / (pl.col("volume") + 1e-9)
        else:
            # Fallback OHLCV: Estimativa via posição do fechamento no range e direção
            # (2*Close - High - Low) / (High - Low) * Volume -> Normalizado
            range_pos = (2 * pl.col("close") - pl.col("high") - pl.col("low")) / (pl.col("high") - pl.col("low") + 1e-9)
            # Combinar com direção do candle para reduzir ruído
            direction = (pl.col("close") - pl.col("open")).sign()
            ofi_expr = (range_pos * 0.7 + direction * 0.3).clip(-1, 1)

        # Delta Cumulativo (Zerado por sessão)
        # Assumimos que a sessão muda quando o gap de tempo é grande ou data muda
        df_res = self.df.with_columns([
            ofi_expr.alias("ofi")
        ])
        
        # Identificar início de sessão (Data muda)
        df_res = df_res.with_columns([
            pl.col("time").dt.date().alias("_date")
        ])
        
        df_res = df_res.with_columns([
            pl.col("ofi").cum_sum().over("_date").alias("cum_delta_ofi")
        ])
        
        return df_res.drop("_date")

    def calculate_vrp(self, window_realized: int = 20, window_historic: int = 300) -> pl.Series:
        """
        Volatility Risk Premium (VRP) Normalized.
        Spread entre Vol Realizada Intraday (Parkinson) e Vol Histórica, 
        normalizado por um Rolling Z-Score de longo prazo para evitar drift de regime.
        """
        # Parkinson Volatility: sqrt(1 / (4 * ln(2) * N) * sum(ln(High/Low)^2))
        const = 1.0 / (4.0 * np.log(2.0))
        log_hl = (pl.col("high") / (pl.col("low") + 1e-9)).log()
        
        realized_vol = (log_hl**2).rolling_mean(window_size=window_realized).sqrt() * np.sqrt(const)
        historic_vol = (log_hl**2).rolling_mean(window_size=window_historic).sqrt() * np.sqrt(const)
        
        raw_vrp = (realized_vol - historic_vol)
        
        # Neutralização Institucional: Rolling Z-Score de 252 períodos (~1 ano se 1d, mas aqui usamos candles)
        # Para intraday 15m, 252*40 candles seria ideal, mas para estabilidade imediata usaremos 1000 candles.
        vrp_mean = raw_vrp.rolling_mean(window_size=1000)
        vrp_std = raw_vrp.rolling_std(window_size=1000)
        
        normalized_vrp = (raw_vrp - vrp_mean) / (vrp_std + 1e-9)
        
        return normalized_vrp.alias("vol_risk_premium")

    def validate_ofi_predictiveness(self, forward_windows: List[int] = [3, 5, 10, 20]) -> Dict[str, float]:
        """
        Valida se o OFI calculado tem poder preditivo sobre retornos futuros.
        Retorna a correlação de Pearson para cada janela.
        """
        df_ofi = self.calculate_ofi()
        results = {}
        
        for n in forward_windows:
            # Retorno Forward: (Close_t+n / Close_t) - 1
            fwd_ret = (pl.col("close").shift(-n) / pl.col("close") - 1)
            
            # Calcular correlação
            corr = df_ofi.select(
                pl.corr(pl.col("ofi"), fwd_ret)
            ).to_series()[0]
            
            results[f"fwd_ret_{n}"] = corr if corr is not None else 0.0
            
        return results

    def dynamic_lead_lag(self, other_df: pl.DataFrame, target_col: str, other_col: str, max_lag: int = 10) -> Dict[str, Any]:
        """
        Identifica dinamicamente qual ativo está liderando.
        Retorna o lag ótimo e a força da liderança (R2).
        """
        # Garantir alinhamento temporal
        df_joined = self.df.select(["time", target_col]).join(other_df.select(["time", other_col]), on="time")
        
        best_lag = 0
        max_corr = -1.0
        
        # Testar lags (Liderança do 'other' sobre o 'target')
        for lag in range(1, max_lag + 1):
            # Correlação entre target(t) e other(t-lag)
            corr = df_joined.select(
                pl.corr(pl.col(target_col), pl.col(other_col).shift(lag))
            ).to_series()[0]
            
            if corr is not None and abs(corr) > max_corr:
                max_corr = abs(corr)
                best_lag = lag
                
        return {
            "optimal_lag": best_lag,
            "leadership_strength": max_corr,
            "is_leading": max_corr > 0.6 # Threshold institucional
        }

class FlowStateMachine:
    """
    Máquina de Estados de Fluxo Institucional.
    Interpreta a intenção por trás dos números do OFI e VRP.
    """
    def __init__(self, df: pl.DataFrame):
        self.df = df

    def detect_states(self) -> pl.DataFrame:
        """
        Detecta estados comportamentais usando lógica de desequilíbrio e deslocamento.
        """
        # Garantir que temos OFI e VRP
        if "ofi" not in self.df.columns:
            engine = OFIEngine(self.df)
            self.df = engine.calculate_ofi()
        
        if "vol_risk_premium" not in self.df.columns:
            engine = OFIEngine(self.df)
            self.df = self.df.with_columns([
                engine.calculate_vrp().alias("vol_risk_premium")
            ])

        # 1. Parâmetros de Referência
        # Usamos janelas curtas para capturar mudanças rápidas de comportamento
        df_res = self.df.with_columns([
            (pl.col("close") - pl.col("open")).abs().alias("body_size"),
            (pl.col("high") - pl.col("low")).alias("candle_range"),
            pl.col("ofi").rolling_mean(window_size=5).alias("ofi_avg"),
            pl.col("volume").rolling_mean(window_size=20).alias("vol_avg")
        ])

        # 2. Definição das Condições
        # ABSORÇÃO: OFI alto, mas corpo do candle pequeno em relação ao range (pavio longo ou candle estreito)
        is_absorption_bullish = (pl.col("ofi") < -0.7) & (pl.col("body_size") < 0.3 * pl.col("candle_range"))
        is_absorption_bearish = (pl.col("ofi") > 0.7) & (pl.col("body_size") < 0.3 * pl.col("candle_range"))

        # EXAUSTÃO: Preço no extremo mas OFI caindo
        is_exhaustion_buy = (pl.col("close") > pl.col("close").rolling_max(window_size=10)) & (pl.col("ofi") < 0.3) & (pl.col("ofi").shift(1) > 0.6)
        is_exhaustion_sell = (pl.col("close") < pl.col("close").rolling_min(window_size=10)) & (pl.col("ofi") > -0.3) & (pl.col("ofi").shift(1) < -0.6)

        # VACUUM: Range alto com volume baixo
        is_vacuum = (pl.col("candle_range") > 1.5 * pl.col("candle_range").rolling_mean(window_size=20)) & (pl.col("volume") < 0.8 * pl.col("vol_avg"))

        # TRAPPED: OFI muito alto mas fechamento reverte o candle anterior
        is_trapped_buyers = (pl.col("ofi").shift(1) > 0.8) & (pl.col("close") < pl.col("low").shift(1))
        is_trapped_sellers = (pl.col("ofi").shift(1) < -0.8) & (pl.col("close") > pl.col("high").shift(1))

        # 3. Mapeamento Final (Hierarquia de Importância)
        df_res = df_res.with_columns([
            pl.when(is_trapped_buyers).then(pl.lit(FlowState.TRAPPED_BUYERS))
              .when(is_trapped_sellers).then(pl.lit(FlowState.TRAPPED_SELLERS))
              .when(is_absorption_bullish).then(pl.lit(FlowState.ABSORPTION_BULLISH))
              .when(is_absorption_bearish).then(pl.lit(FlowState.ABSORPTION_BEARISH))
              .when(is_exhaustion_buy).then(pl.lit(FlowState.EXHAUSTION_BUY))
              .when(is_exhaustion_sell).then(pl.lit(FlowState.EXHAUSTION_SELL))
              .when(is_vacuum).then(pl.lit(FlowState.LIQUIDITY_VACUUM))
              .when(pl.col("ofi") > 0.6).then(pl.lit(FlowState.AGGRESSIVE_BUYING))
              .when(pl.col("ofi") < -0.6).then(pl.lit(FlowState.AGGRESSIVE_SELLING))
              .otherwise(pl.lit(FlowState.BALANCED))
              .alias("flow_state")
        ])

        return df_res.drop(["body_size", "candle_range", "ofi_avg", "vol_avg"])

def add_microstructure_indicators(df: pl.DataFrame) -> pl.DataFrame:
    """
    Função de integração para o DataProcessor.
    Adiciona OFI, VRP e Estados de Fluxo.
    """
    engine = OFIEngine(df)
    df = engine.calculate_ofi()
    
    # Adicionar VRP
    df = df.with_columns([
        engine.calculate_vrp().alias("vol_risk_premium")
    ])
    
    # Adicionar Máquina de Estados
    fsm = FlowStateMachine(df)
    df = fsm.detect_states()
    
    return df
