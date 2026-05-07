import polars as pl
import numpy as np
from src.core.paths import get_data_path
from src.backtest.engine.vectorized import VectorizedEngine
from src.backtest.strategies.ifr_pullback_trinity import IFRPullbackTrinity

def run_ma_robustness_study():
    """
    Estudo de Sensibilidade: Qual o impacto do filtro de média móvel na robustez?
    """
    tf = "15"
    win = pl.read_parquet(get_data_path("WIN$", tf)).select(["time", "open", "high", "low", "close"]).rename({
        "close": "win_close", "high": "win_high", "low": "win_low", "open": "win_open"
    })
    wdo = pl.read_parquet(get_data_path("WDO$", tf)).select(["time", "close"]).rename({"close": "wdo_close"})
    di = pl.read_parquet(get_data_path("DI1$", tf)).select(["time", "close"]).rename({"close": "di_close"})
    data = win.join(wdo, on="time", how="inner").join(di, on="time", how="inner").sort("time")

    ma_ranges = [100, 200, 400, 600, 800]
    engine = VectorizedEngine(exit_horizon=40, target_asset="win_close")
    
    results = []
    
    print("\n" + "="*50)
    print(" ESTUDO DE ROBUSTEZ: FILTRO DE MÉDIA MÓVEL ".center(50, "="))
    print("="*50)

    for ma in ma_ranges:
        strategy = IFRPullbackTrinity(target_asset="win", ma_period=ma)
        metrics = engine.run(data, strategy)
        results.append({
            "ma": ma,
            "pf": metrics["profit_factor"],
            "trades": metrics["trades_count"]
        })
        print(f"MA {ma}: PF = {metrics['profit_factor']:.2f} | Trades = {metrics['trades_count']}")

    # Cálculo de Robustez
    pfs = [r["pf"] for r in results]
    robustness_score = (np.array(pfs) > 1.0).sum() / len(pfs)
    print("\n" + "="*50)
    print(f"SCORE DE ROBUSTEZ: {robustness_score*100:.1f}%")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_ma_robustness_study()
