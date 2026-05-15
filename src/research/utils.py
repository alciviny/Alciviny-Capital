import pandas as pd
import numpy as np
import polars as pl
import os
import json
from datetime import datetime
from src.core.config import IFR_PERIOD, SIGNAL_COLS
from src.core.paths import EXPERIMENTS_DIR, STORAGE_DIR as DATA_STORAGE, get_data_path

# get_data_path já importado de src.core.paths

def calculate_rsi_200(prices: np.ndarray, period: int = IFR_PERIOD) -> np.ndarray:
    """Cálculo padronizado do IFR (Wilder/EWM)"""
    delta = np.diff(prices)
    alpha = 1 / period
    gain = pd.Series(np.where(delta > 0, delta, 0)).ewm(alpha=alpha, adjust=False).mean()
    loss = pd.Series(np.where(delta < 0, -delta, 0)).ewm(alpha=alpha, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    return np.insert(100 - (100 / (1 + rs.values)), 0, np.nan)


def get_rsi_mode(rsi_series: pl.Series, low=48, high=52) -> list:
    """Mapeia o regime do IFR (Bull/Bear) com histerese (versão legacy)."""
    modes = []
    curr = None
    for v in rsi_series:
        if v is None or np.isnan(v):
            modes.append(None)
            continue
        if v < low: curr = 'bear'
        elif v > high: curr = 'bull'
        modes.append(curr)
    return modes

def get_rsi_mode_pl(rsi_col: str, low=48, high=52) -> pl.Expr:
    """
    Versão Vetorizada (Polars) para mapear regime do IFR com histerese.
    Retorna uma expressão Polars.
    """
    return pl.when(pl.col(rsi_col) < low).then(pl.lit("bear")) \
             .when(pl.col(rsi_col) > high).then(pl.lit("bull")) \
             .otherwise(None).forward_fill()

def get_rsi_level_advance_pl(rsi_col: str) -> pl.Expr:
    """
    Identifica avanços de nível inteiro no IFR (ex: 48.9 -> 49.1).
    Retorna 1 para avanço (alta), -1 para recuo (baixa) e 0 para estável.
    """
    levels = pl.col(rsi_col).floor()
    diff = levels - levels.shift(1)
    return pl.when(diff > 0).then(1) \
             .when(diff < 0).then(-1) \
             .otherwise(0)

def get_rsi_slope_pl(rsi_col: str, period: int = 3) -> pl.Expr:
    """
    Calcula a inclinação (momentum) do IFR.
    Retorna a diferença bruta entre o valor atual e N períodos atrás.
    """
    return pl.col(rsi_col) - pl.col(rsi_col).shift(period)


def validate_signals(df: pl.DataFrame) -> bool:
    """Valida se o dataframe possui as colunas mínimas para backtest."""
    missing = [c for c in SIGNAL_COLS if c not in df.columns]
    if missing:
        print(f"[ERRO] Colunas ausentes no sinal: {missing}")
        return False
    return True

def save_experiment(name: str, metadata: dict, data: pd.DataFrame = None):
    """
    Salva os resultados da pesquisa de forma profissional para uso futuro em ML.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = f"{EXPERIMENTS_DIR}/{name}_{timestamp}"
    os.makedirs(exp_dir, exist_ok=True)

    # 1. Salvar Metadados (Configurações e Resultados Globais)
    meta_path = f"{exp_dir}/metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=4)

    # 2. Salvar Dados Brutos de Trades (Dataset para ML)
    if data is not None:
        data_path = f"{exp_dir}/trades.parquet"
        # Converter para Polars para salvamento eficiente em Parquet
        pl.from_pandas(data).write_parquet(data_path)
        print(f"\n[INFO] Dataset de ML salvo em: {data_path}")

    print(f"[INFO] Metadados salvos em: {meta_path}")
    return exp_dir


def print_research_header(title: str):
    print(f"\n{'='*80}")
    print(f"{title.center(80)}")
    print(f"{'='*80}")

def print_stat_row(name: str, trades: int, win_rate: float, avg_ret: float, pf: float = None):
    pf_str = f" | PF: {pf:.2f}" if pf is not None else ""
    print(f"{name:45} | Trades: {trades:4} | WR: {win_rate:5.1f}% | Ret: {avg_ret:+7.4f}%{pf_str}")
