import pandas as pd
import numpy as np
import polars as pl
import sys
import os

# Adicionar src ao path
sys.path.append(os.getcwd())

from src.indicators.oscillators import calculate_rsi_wilder, calculate_rsi_pl

def test_rsi_parity():
    print("\n[TEST] Iniciando Validação de Paridade RSI (Pandas vs Polars)...")
    
    # Criar dados sintéticos (Random Walk)
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(1000))
    df_pd = pd.DataFrame({'close': prices})
    df_pl = pl.DataFrame({'close': prices})
    
    period = 200
    
    # 1. Calcular via Pandas
    rsi_pd = calculate_rsi_wilder(df_pd['close'], period=period)
    
    # 2. Calcular via Polars
    rsi_pl_expr = calculate_rsi_pl("close", period=period)
    df_pl = df_pl.with_columns(rsi_pl_expr.alias("rsi_pl"))
    rsi_pl = df_pl["rsi_pl"].to_pandas()
    
    # 3. Comparação (ignorar primeiros N valores devido ao warming up)
    # Wilder Smoothing estabiliza após aproximadamente 2-3x o período
    start_idx = period * 2
    
    diff = np.abs(rsi_pd.values[start_idx:] - rsi_pl.values[start_idx:])
    max_diff = np.max(diff)
    
    print(f"Diferença Máxima após warmup: {max_diff:.2e}")
    
    if max_diff < 1e-6:
        print("[SUCESSO] Paridade confirmada! Erro desprezível.")
        return True
    else:
        print("[FALHA] Diferença significativa detectada.")
        return False

if __name__ == "__main__":
    success = test_rsi_parity()
    if not success:
        sys.exit(1)
