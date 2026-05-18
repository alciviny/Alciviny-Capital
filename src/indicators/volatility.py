import pandas as pd
import numpy as np
import polars as pl
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

def add_vwap_bands(df, period_type='D', atr_period=300, multipliers=[1.5, 3.0, 6.0, 9.0]):
    """
    Calcula VWAP Periódica com Bandas de ATR.
    period_type: 'D' (Diário), 'W' (Semanal), 'M' (Mensal)
    """
    df = df.copy()
    
    # 1. Definir a chave de agrupamento conforme o período
    if period_type == 'D':
        group_key = df['time'].dt.date
    elif period_type == 'W':
        group_key = df['time'].dt.to_period('W').apply(lambda r: r.start_time)
    elif period_type == 'M':
        group_key = df['time'].dt.to_period('M').apply(lambda r: r.start_time)
    else:
        group_key = df['time'].dt.date

    # 2. Calcular VWAP Acumulada no Período
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = df['tp'] * df['tick_volume']
    
    # Agrupar e calcular somas cumulativas
    groups = df.groupby(group_key)
    df['cum_pv'] = groups['pv'].cumsum()
    df['cum_v'] = groups['tick_volume'].cumsum()
    
    vwap_col = f'VWAP_{period_type}'
    df[vwap_col] = df['cum_pv'] / df['cum_v']

    # 3. Calcular ATR (Welles Wilder) - Período 300
    high_low = df['high'] - df['low']
    high_cp = (df['high'] - df['close'].shift(1)).abs()
    low_cp = (df['low'] - df['close'].shift(1)).abs()
    
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    # Welles Wilder Smoothing = EMA com alpha = 1/N
    atr = tr.ewm(alpha=1/atr_period, adjust=False).mean()
    
    # 4. Calcular Bandas
    for mult in multipliers:
        mult_str = str(mult).replace('.', '')
        df[f'{vwap_col}_U{mult_str}'] = df[vwap_col] + (atr * mult)
        df[f'{vwap_col}_L{mult_str}'] = df[vwap_col] - (atr * mult)

    # Limpeza de colunas temporárias
    return df.drop(columns=['tp', 'pv', 'cum_pv', 'cum_v'])

def calculate_atr_pl(high: str, low: str, close: str, period: int = 14) -> pl.Expr:
    """
    Calcula o Average True Range (ATR) usando Polars.
    """
    tr = pl.max_horizontal([
        pl.col(high) - pl.col(low),
        (pl.col(high) - pl.col(close).shift(1)).abs(),
        (pl.col(low) - pl.col(close).shift(1)).abs()
    ])
    
    # O primeiro valor de TR é High - Low (onde o shift do close é null)
    tr = tr.fill_null(pl.col(high) - pl.col(low))
    
    # RMA (Welles Wilder Smoothing)
    return tr.ewm_mean(alpha=1.0/period, adjust=False)

# --- OBTR (ON-BALANCE TRUE RANGE) ---

@dataclass
class OBTRBollingerConfig:
    bb_period: int = 200
    bb_std: float = 0.45
    atr_period: int = 14
    atr_mult_1: float = 1.5
    atr_mult_2: float = 3.0

class OBTRBollinger:
    """
    On Balance True Range com Bandas de Bollinger (Welles Wilder).
    Otimizado para Polars para performance institucional.
    """
    def __init__(self, config: Optional[OBTRBollingerConfig] = None):
        self.cfg = config or OBTRBollingerConfig()

    def _calculate_rma_pl(self, series: pl.Expr, period: int) -> pl.Expr:
        """Média Móvel de Welles Wilder (RMA) via EWM."""
        return series.ewm_mean(alpha=1.0/period, adjust=False)

    def compute(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Calcula o indicador de forma totalmente vetorizada usando Polars.
        """
        # 1. Normalização de Colunas
        cols = {c.lower(): c for c in df.columns}
        c_close = cols.get("close")
        c_high = cols.get("high")
        c_low = cols.get("low")
        
        if not all([c_close, c_high, c_low]):
            raise ValueError(f"Colunas OHLC necessárias não encontradas.")

        # 2. Cálculo do True Range (TR)
        df = df.with_columns([
            pl.max_horizontal([
                pl.col(c_high) - pl.col(c_low),
                (pl.col(c_high) - pl.col(c_close).shift(1)).abs(),
                (pl.col(low) - pl.col(close).shift(1)).abs()
            ]).fill_null(0).alias("_tr")
        ])

        # 3. Cálculo do OBTR
        df = df.with_columns([
            pl.when(pl.col(c_close) > pl.col(c_close).shift(1)).then(1)
              .when(pl.col(c_close) < pl.col(c_close).shift(1)).then(-1)
              .otherwise(0).alias("_dir")
        ])
        
        df = df.with_columns([
            (pl.col("_dir") * pl.col("_tr")).cum_sum().alias("obtr")
        ])

        # 4. Cálculo do ATR sobre OBTR
        df = df.with_columns([
            self._calculate_rma_pl(pl.col("_tr"), self.cfg.atr_period).alias("atr_obtr")
        ])

        # 5. Média Welles Wilder (RMA) e Desvio Padrão sobre OBTR
        df = df.with_columns([
            self._calculate_rma_pl(pl.col("obtr"), self.cfg.bb_period).alias("obtr_rma_200"),
            pl.col("obtr").rolling_std(window_size=self.cfg.bb_period).alias("_obtr_std")
        ])

        # 6. Bandas de Bollinger e Envelopes ATR
        df = df.with_columns([
            (pl.col("obtr_rma_200") + self.cfg.bb_std * pl.col("_obtr_std")).alias("bb_upper"),
            (pl.col("obtr_rma_200") - self.cfg.bb_std * pl.col("_obtr_std")).alias("bb_lower"),
            (pl.col("obtr") + self.cfg.atr_mult_1 * pl.col("atr_obtr")).alias("atr_upper_1"),
            (pl.col("obtr") - self.cfg.atr_mult_1 * pl.col("atr_obtr")).alias("atr_lower_1")
        ])

        # 7. Sinais e %B
        df = df.with_columns([
            ((pl.col("obtr") - pl.col("bb_lower")) / (pl.col("bb_upper") - pl.col("bb_lower") + 1e-9)).alias("bb_pct_b")
        ])

        return df.drop(["_tr", "_dir", "_obtr_std"])

# --- KELTNER CHANNEL ---

class SignalType(str, Enum):
    """Tipos de sinal gerados pelo indicador."""
    BREAKOUT_UP    = "BREAKOUT_UP"    # Preço rompeu banda superior
    BREAKOUT_DOWN  = "BREAKOUT_DOWN"  # Preço rompeu banda inferior
    REENTRY_UP     = "REENTRY_UP"     # Preço retornou de cima para dentro do canal
    REENTRY_DOWN   = "REENTRY_DOWN"   # Preço retornou de baixo para dentro do canal
    SQUEEZE_ON     = "SQUEEZE_ON"     # Squeeze ativado (Keltner > Bollinger)
    SQUEEZE_OFF    = "SQUEEZE_OFF"    # Squeeze desativado
    NEUTRAL        = "NEUTRAL"        # Sem sinal relevante

class ATRMethod(str, Enum):
    """Método de cálculo do ATR."""
    WILDER  = "wilder"    # EMA de Wilder (clássico, padrão)
    EMA     = "ema"       # EMA padrão
    SMA     = "sma"       # Média Simples

@dataclass
class KeltnerConfig:
    """Configuração completa do indicador Keltner Channel."""
    ema_period   : int       = 20
    atr_period   : int       = 10
    multiplier   : float     = 2.0
    atr_method   : ATRMethod = ATRMethod.WILDER
    upper_mult   : Optional[float] = None
    lower_mult   : Optional[float] = None
    use_squeeze  : bool      = True
    bb_period    : int       = 20
    bb_std       : float     = 2.0
    signal_column: str       = "close"

    def __post_init__(self) -> None:
        if self.ema_period < 1:
            raise ValueError(f"ema_period deve ser >= 1, recebido: {self.ema_period}")
        if self.atr_period < 1:
            raise ValueError(f"atr_period deve ser >= 1, recebido: {self.atr_period}")
        if self.multiplier <= 0:
            raise ValueError(f"multiplier deve ser > 0, recebido: {self.multiplier}")
        if self.upper_mult is None:
            self.upper_mult = self.multiplier
        if self.lower_mult is None:
            self.lower_mult = self.multiplier

@dataclass
class KeltnerResult:
    """Resultado completo do cálculo do Keltner Channel."""
    middle  : pd.Series
    upper   : pd.Series
    lower   : pd.Series
    atr     : pd.Series
    width   : pd.Series
    pct_b   : pd.Series
    signal  : pd.Series
    squeeze : pd.Series
    meta    : dict = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Retorna todos os resultados em um único DataFrame com prefixo 'keltner_'."""
        return pd.DataFrame({
            "keltner_middle" : self.middle,
            "keltner_upper"  : self.upper,
            "keltner_lower"  : self.lower,
            "keltner_atr"    : self.atr,
            "keltner_width"  : self.width,
            "keltner_pct_b"  : self.pct_b,
            "keltner_signal" : self.signal,
            "keltner_squeeze": self.squeeze,
        })

class KeltnerChannel:
    """Indicador Keltner Channel profissional integrado ao sistema."""
    REQUIRED_COLUMNS = {"open", "high", "low", "close"}

    def __init__(self, config: KeltnerConfig | None = None, **kwargs) -> None:
        from src.core.logger import logging
        self.logger = logging.getLogger("AlcivinyEdger.Indicators.KeltnerChannel")
        
        if config is not None:
            self.config = config
        else:
            self.config = KeltnerConfig(**kwargs)

        self.logger.info(
            "KeltnerChannel inicializado | EMA=%d | ATR=%d | mult=%.2f",
            self.config.ema_period,
            self.config.atr_period,
            self.config.multiplier,
        )

    def compute(self, df: pd.DataFrame) -> KeltnerResult:
        df_norm = self._validate_and_normalize(df)
        cfg = self.config

        try:
            # 1. Linha central (EMA do close)
            middle = df_norm["close"].ewm(span=cfg.ema_period, adjust=False, min_periods=cfg.ema_period).mean()

            # 2. ATR
            prev_close = df_norm["close"].shift(1)
            tr = pd.concat([
                df_norm["high"] - df_norm["low"],
                (df_norm["high"] - prev_close).abs(),
                (df_norm["low"] - prev_close).abs(),
            ], axis=1).max(axis=1)

            if cfg.atr_method == ATRMethod.WILDER:
                atr = tr.ewm(alpha=1.0/cfg.atr_period, adjust=False, min_periods=cfg.atr_period).mean()
            elif cfg.atr_method == ATRMethod.EMA:
                atr = tr.ewm(span=cfg.atr_period, adjust=False, min_periods=cfg.atr_period).mean()
            else:
                atr = tr.rolling(window=cfg.atr_period, min_periods=cfg.atr_period).mean()

            # 3. Bandas
            upper = middle + cfg.upper_mult * atr
            lower = middle - cfg.lower_mult * atr

            # 4. Métricas derivadas
            width = upper - lower
            pct_b = (df_norm[cfg.signal_column] - lower) / width.replace(0, np.nan)

            # 5. Sinais
            signal = self._generate_signals(df_norm[cfg.signal_column], upper, lower)

            # 6. Squeeze
            squeeze = self._detect_squeeze(df_norm["close"], upper, lower) if cfg.use_squeeze else pd.Series(False, index=df_norm.index)

            return KeltnerResult(
                middle=middle, upper=upper, lower=lower, atr=atr,
                width=width, pct_b=pct_b, signal=signal, squeeze=squeeze
            )

        except Exception as exc:
            self.logger.error(f"Erro no cálculo Keltner: {exc}")
            raise

    def _generate_signals(self, price: pd.Series, upper: pd.Series, lower: pd.Series) -> pd.Series:
        above = price > upper
        below = price < lower
        inside = ~above & ~below
        prev_above = above.shift(1).fillna(False).astype(bool)
        prev_below = below.shift(1).fillna(False).astype(bool)

        conditions = [above, below, inside & prev_above, inside & prev_below]
        choices = [SignalType.BREAKOUT_UP.value, SignalType.BREAKOUT_DOWN.value, 
                   SignalType.REENTRY_UP.value, SignalType.REENTRY_DOWN.value]

        return pd.Series(np.select(conditions, choices, default=SignalType.NEUTRAL.value), index=price.index)

    def _detect_squeeze(self, close: pd.Series, kc_upper: pd.Series, kc_lower: pd.Series) -> pd.Series:
        cfg = self.config
        bb_mid = close.rolling(window=cfg.bb_period).mean()
        bb_std = close.rolling(window=cfg.bb_period).std(ddof=0)
        bb_upper = bb_mid + cfg.bb_std * bb_std
        bb_lower = bb_mid - cfg.bb_std * bb_std
        return (bb_upper <= kc_upper) & (bb_lower >= kc_lower)

    def _validate_and_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.str.lower()
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing: raise ValueError(f"Colunas ausentes: {missing}")
        return df

def add_keltner_channels(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Wrapper para integrar Keltner Channel no pipeline do DataProcessor."""
    kc = KeltnerChannel(**kwargs)
    result = kc.compute(df)
    return pd.concat([df, result.to_dataframe()], axis=1)

def calculate_keltner_pl(high: str, low: str, close: str, 
                         ema_period: int = 20, 
                         atr_period: int = 10, 
                         multiplier: float = 2.0) -> List[pl.Expr]:
    """
    Calcula as bandas do Keltner Channel usando Polars Expressions.
    Retorna uma lista de expressões [middle, upper, lower].
    """
    middle = pl.col(close).ewm_mean(span=ema_period, adjust=False)
    atr = calculate_atr_pl(high, low, close, atr_period)
    
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)
    
    return [
        middle.alias("keltner_mid"),
        upper.alias("keltner_upper"),
        lower.alias("keltner_lower")
    ]

def calculate_hurst_pl(series_col: str, window: int = 100) -> pl.Expr:
    """
    Expoente de Hurst para detecção de persistência em Polars.
    H > 0.5: Tendência (Persistente)
    H < 0.5: Reversão à média (Anti-persistente)
    H = 0.5: Movimento aleatório
    """
    def _hurst_rs(vals: pl.Series) -> float:
        # Converter para numpy explicitamente para evitar conflitos de axis no all()
        x = vals.to_numpy()
        if len(x) < 20 or np.all(x == x[0]):
            return 0.5
        
        # Calcular desvios e range acumulado
        mean = np.mean(x)
        z = np.cumsum(x - mean)
        r = np.max(z) - np.min(z)
        s = np.std(x)
        
        if s == 0: return 0.5
        
        # Rescaled Range R/S
        return np.log(r / s + 1e-9) / np.log(len(x) + 1e-9)

    return pl.col(series_col).rolling_map(_hurst_rs, window_size=window).alias("hurst_exponent")
