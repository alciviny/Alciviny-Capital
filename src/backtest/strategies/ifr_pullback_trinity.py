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
                 rsi_period: int = 200, 
                 quantile_window: int = 1000,
                 low_q: float = 0.45,
                 high_q: float = 0.55,
                 atr_period: int = 20,
                 atr_mult_sl: float = 2.5,
                 atr_mult_tp: float = 3.0,
                 ma_period: int = 400):
        self.target_asset = target_asset
        self.rsi_period = rsi_period
        self.quantile_window = quantile_window
        self.low_q = low_q
        self.high_q = high_q
        self.atr_period = atr_period
        self.atr_mult_sl = atr_mult_sl
        self.atr_mult_tp = atr_mult_tp
        self.ma_period = ma_period

    def generate_signals(self, data: pl.DataFrame) -> pl.DataFrame:
        """
        Gera sinais e define Stops/Alvos Dinâmicos de forma agnóstica ao ativo.
        """
        target = self.target_asset.lower()
        others = ["win", "wdo", "di"]
        others.remove(target)
        
        # 1. Cálculos de IFR e Volatilidade
        df = data.with_columns([
            calculate_rsi_pl(f"{target}_close", self.rsi_period).alias("target_rsi"),
            calculate_rsi_pl(f"{others[0]}_close", self.rsi_period).alias("other1_rsi"),
            calculate_rsi_pl(f"{others[1]}_close", self.rsi_period).alias("other2_rsi"),
            calculate_atr_pl(f"{target}_high", f"{target}_low", f"{target}_close", self.atr_period).alias("target_atr"),
            pl.col(f"{target}_close").rolling_mean(window_size=self.ma_period).alias("target_ma")
        ])

        df = df.drop_nulls()

        # 2. Quantis Dinâmicos
        df = df.with_columns([
            pl.col("target_rsi").rolling_quantile(self.low_q, window_size=self.quantile_window).alias("t_dyn_low"),
            pl.col("target_rsi").rolling_quantile(self.high_q, window_size=self.quantile_window).alias("t_dyn_high"),
            pl.col("other1_rsi").rolling_quantile(self.low_q, window_size=self.quantile_window).alias("o1_dyn_low"),
            pl.col("other2_rsi").rolling_quantile(self.low_q, window_size=self.quantile_window).alias("o2_dyn_low"),
        ])

        df = df.drop_nulls()

        # 3. Stops Adaptativos
        df = df.with_columns([
            ((pl.col("target_atr") * self.atr_mult_sl) / pl.col(f"{target}_close") * 100).alias("sl_pct"),
            ((pl.col("target_atr") * self.atr_mult_tp) / pl.col(f"{target}_close") * 100).alias("tp_pct")
        ])

        # 4. Lógica de Gatilho e Confluência
        # Pullback na zona neutra
        target_pullback = (pl.col("target_rsi") >= pl.col("t_dyn_low")) & \
                          (pl.col("target_rsi") <= pl.col("t_dyn_high")) & \
                          (pl.col("target_rsi").shift(1) > pl.col("t_dyn_high"))
        
        # Filtro de Tendência Macro
        trend_up = pl.col(f"{target}_close") > pl.col("target_ma")

        # Confluência Inter-mercado (Simplificada: Outros devem estar 'fracos' ou 'estressados')
        # Para WIN Long -> WDO/DI Fracos.
        # Para WDO Long -> WIN Fraco / DI Forte (Normalmente WDO/DI andam juntos).
        if target == "win":
            confluence = (pl.col("other1_rsi") < pl.col("o1_dyn_low")) & (pl.col("other2_rsi") < pl.col("o2_dyn_low"))
        else: # WDO
            confluence = (pl.col("other1_rsi") < pl.col("o1_dyn_low")) # WIN Fraco
            # DI costuma acompanhar o WDO, então não exigimos DI fraco para WDO Long.

        df = df.with_columns([
            (target_pullback & confluence & trend_up).cast(pl.Int8).alias("signal")
        ])

        return df

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_period": self.rsi_period,
            "quantile_window": self.quantile_window,
            "low_q": self.low_q,
            "high_q": self.high_q,
            "atr_period": self.atr_period,
            "atr_mult_sl": self.atr_mult_sl,
            "atr_mult_tp": self.atr_mult_tp,
            "ma_period": self.ma_period
        }
