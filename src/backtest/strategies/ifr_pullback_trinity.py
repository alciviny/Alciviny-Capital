from src.backtest.strategies.base import BaseStrategy
from src.indicators.oscillators import calculate_rsi_pl
from src.indicators.volatility import calculate_atr_pl
import polars as pl
from typing import Dict, Any

class IFRPullbackTrinity(BaseStrategy):
    """
    Estratégia de Pullback no IFR com zonas adaptativas (P45-P55) 
    e confluência inter-mercado (WDO e DI1).
    Agora inclui Stops Dinâmicos baseados em ATR.
    """
    def __init__(self, 
                 target_asset: str = "win",
                 confluence_assets: list = None,
                 rsi_period: int = 200, 
                 quantile_window: int = 1000,
                 low_q: float = 0.45,
                 high_q: float = 0.55,
                 atr_period: int = 20,
                 atr_mult_sl: float = 2.5,
                 atr_mult_tp: float = 3.0,
                 ma_period: int = 400,
                 use_micro: bool = False,
                 micro_period: int = 2,
                 micro_threshold: float = 15.0,
                 allow_short: bool = True):
        self.target_asset = target_asset
        self.confluence_assets = confluence_assets or []
        self.rsi_period = rsi_period
        self.quantile_window = quantile_window
        self.low_q = low_q
        self.high_q = high_q
        self.atr_period = atr_period
        self.atr_mult_sl = atr_mult_sl
        self.atr_mult_tp = atr_mult_tp
        self.ma_period = ma_period
        self.use_micro = use_micro
        self.micro_period = micro_period
        self.micro_threshold = micro_threshold
        self.allow_short = allow_short

    def generate_signals(self, data: pl.DataFrame) -> pl.DataFrame:
        """
        Gera sinais Long e Short de forma agnóstica ao ativo.
        Otimizado para reduzir cópias de memória e chamadas sequenciais.
        """
        target = self.target_asset.lower()
        
        # 1. Pipeline de Indicadores Base e Confluência
        indicator_exprs = [
            calculate_rsi_pl(f"{target}_close", self.rsi_period).alias("target_rsi"),
            calculate_rsi_pl(f"{target}_close", self.micro_period).alias("target_rsi_micro"),
            calculate_atr_pl(f"{target}_high", f"{target}_low", f"{target}_close", self.atr_period).alias("target_atr"),
            pl.col(f"{target}_close").rolling_mean(window_size=self.ma_period).alias("target_ma")
        ]
        
        for i, asset in enumerate(self.confluence_assets):
            indicator_exprs.append(
                calculate_rsi_pl(f"{asset.lower()}_close", self.rsi_period).alias(f"conf_{i}_rsi")
            )

        # 2. Pipeline de Quantis e Parâmetros Adaptativos
        # Nota: Precisamos dos indicadores base calculados para rodar os quantis
        df = data.with_columns(indicator_exprs).drop_nulls()

        quantile_exprs = [
            pl.col("target_rsi").rolling_quantile(self.low_q, window_size=self.quantile_window).alias("t_dyn_low"),
            pl.col("target_rsi").rolling_quantile(self.high_q, window_size=self.quantile_window).alias("t_dyn_high"),
            ((pl.col("target_atr") * self.atr_mult_sl) / pl.col(f"{target}_close") * 100).alias("sl_pct"),
            ((pl.col("target_atr") * self.atr_mult_tp) / pl.col(f"{target}_close") * 100).alias("tp_pct")
        ]
        
        for i in range(len(self.confluence_assets)):
            quantile_exprs.extend([
                pl.col(f"conf_{i}_rsi").rolling_quantile(self.low_q, window_size=self.quantile_window).alias(f"c{i}_dyn_low"),
                pl.col(f"conf_{i}_rsi").rolling_quantile(self.high_q, window_size=self.quantile_window).alias(f"c{i}_dyn_high")
            ])

        df = df.with_columns(quantile_exprs).drop_nulls()

        # 3. Lógica de Gatilho e Filtros Consolidados
        # Long: Pullback na Zona Neutra vindo de cima + Confluência Fraca + Tendência Alta + Micro Exaustão
        long_pullback = (pl.col("target_rsi") >= pl.col("t_dyn_low")) & \
                        (pl.col("target_rsi") <= pl.col("t_dyn_high")) & \
                        (pl.col("target_rsi").shift(1) > pl.col("t_dyn_high"))
        
        # Short: Pullback na Zona Neutra vindo de baixo + Confluência Forte + Tendência Baixa + Micro Exaustão
        short_pullback = (pl.col("target_rsi") >= pl.col("t_dyn_low")) & \
                         (pl.col("target_rsi") <= pl.col("t_dyn_high")) & \
                         (pl.col("target_rsi").shift(1) < pl.col("t_dyn_low"))

        long_confluence = pl.lit(True)
        short_confluence = pl.lit(True)
        
        for i in range(len(self.confluence_assets)):
            long_confluence = long_confluence & (pl.col(f"conf_{i}_rsi") < pl.col(f"c{i}_dyn_low"))
            short_confluence = short_confluence & (pl.col(f"conf_{i}_rsi") > pl.col(f"c{i}_dyn_high"))

        trend_up = pl.col(f"{target}_close") > pl.col("target_ma")
        trend_down = pl.col(f"{target}_close") < pl.col("target_ma")

        if self.use_micro:
            long_micro = pl.col("target_rsi_micro") < self.micro_threshold
            short_micro = pl.col("target_rsi_micro") > (100 - self.micro_threshold)
        else:
            long_micro = pl.lit(True)
            short_micro = pl.lit(True)

        # Geração Final Vetorizada
        return df.with_columns([
            pl.when(long_pullback & long_confluence & trend_up & long_micro).then(1)
            .when(self.allow_short & short_pullback & short_confluence & trend_down & short_micro).then(-1)
            .otherwise(0).cast(pl.Int8).alias("signal")
        ])

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "target_asset": self.target_asset,
            "confluence_assets": self.confluence_assets,
            "rsi_period": self.rsi_period,
            "quantile_window": self.quantile_window,
            "low_q": self.low_q,
            "high_q": self.high_q,
            "atr_period": self.atr_period,
            "atr_mult_sl": self.atr_mult_sl,
            "atr_mult_tp": self.atr_mult_tp,
            "ma_period": self.ma_period,
            "use_micro": self.use_micro,
            "micro_period": self.micro_period,
            "micro_threshold": self.micro_threshold,
            "allow_short": self.allow_short
        }
