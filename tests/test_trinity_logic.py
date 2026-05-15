import polars as pl
import numpy as np
import sys
import os

# Adicionar src ao path
sys.path.append(os.getcwd())

from src.backtest.strategies.ifr_pullback_trinity import IFRPullbackTrinity

def create_mock_data(n=2000):
    """Cria dados sintéticos para teste de sinais."""
    np.random.seed(42)
    from datetime import datetime, timedelta
    start = datetime(2026, 1, 1)
    end = start + timedelta(minutes=15 * (n - 1))
    time = pl.datetime_range(start, end, interval="15m", eager=True)
    
    # Target (WIN)
    win_close = 100 + np.cumsum(np.random.randn(n) * 0.1)
    win_high = win_close + 0.5
    win_low = win_close - 0.5
    
    # Confluence com correlação negativa (Tripé de Risco)
    # Quando WIN sobe, WDO e DI caem. Quando WIN cai, WDO e DI sobem.
    win_returns = np.diff(win_close, prepend=win_close[0])
    wdo_close = 5.0 - np.cumsum(win_returns * 0.05) + np.random.randn(n) * 0.005
    di_close = 12.0 - np.cumsum(win_returns * 0.02) + np.random.randn(n) * 0.002
    
    return pl.DataFrame({
        "time": time,
        "win_close": win_close,
        "win_high": win_high,
        "win_low": win_low,
        "wdo_close": wdo_close,
        "di_close": di_close
    })

def test_signal_generation():
    print("\n[TEST] Validando Lógica de Sinais Trinity 2.0...")
    
    df = create_mock_data(5000)
    
    # 1. Teste Long (Agnóstico)
    strategy = IFRPullbackTrinity(
        target_asset="win",
        confluence_assets=["wdo", "di"],
        use_micro=False,
        allow_short=True
    )
    
    df_results = strategy.generate_signals(df)
    
    long_signals = df_results.filter(pl.col("signal") == 1).height
    short_signals = df_results.filter(pl.col("signal") == -1).height
    
    print(f"Sinais Long gerados: {long_signals}")
    print(f"Sinais Short gerados: {short_signals}")
    
    # Verificação básica de existência de sinais
    assert long_signals > 0, "Deveria gerar sinais de Long"
    assert short_signals > 0, "Deveria gerar sinais de Short"
    
    # 2. Teste de Bloqueio por Confluência
    # Se não passarmos confluence_assets, a confluência é sempre True (vazia)
    strategy_no_conf = IFRPullbackTrinity(
        target_asset="win",
        confluence_assets=[],
        use_micro=False
    )
    df_no_conf = strategy_no_conf.generate_signals(df)
    
    print(f"Sinais sem confluência: {df_no_conf.filter(pl.col('signal') != 0).height}")
    assert df_no_conf.filter(pl.col("signal") != 0).height >= long_signals + short_signals, \
        "Sem filtros de confluência deveria gerar igual ou mais sinais"

    # 3. Teste Micro Confluence
    strategy_micro = IFRPullbackTrinity(
        target_asset="win",
        confluence_assets=["wdo", "di"],
        use_micro=True,
        micro_threshold=10.0 # Muito restritivo
    )
    df_micro = strategy_micro.generate_signals(df)
    micro_signals = df_micro.filter(pl.col("signal") != 0).height
    
    print(f"Sinais com Micro Filter (restritivo): {micro_signals}")
    assert micro_signals <= (long_signals + short_signals), \
        "Micro filter deveria reduzir ou manter o número de sinais"

    print("[SUCESSO] Lógica de sinais validada!")
    return True

if __name__ == "__main__":
    try:
        test_signal_generation()
    except AssertionError as e:
        print(f"[FALHA] Teste falhou: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
        sys.exit(1)
