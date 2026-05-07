import polars as pl
from src.core.paths import get_data_path
from src.backtest.engine.vectorized import VectorizedEngine
from src.backtest.strategies.ifr_pullback_trinity import IFRPullbackTrinity
from src.backtest.utils.costs import CostModel
from src.backtest.risk.sizing import KellySizer
from src.backtest.risk.manager import RiskManager, RiskParameters
from src.backtest.visuals.strategy_plots import plot_backtest_results

def generate_full_visual_report():
    print("\n" + "="*70)
    print(" GERANDO RELATÓRIO VISUAL: TRINITY WIN 15MIN ".center(70, "="))
    print("="*70 + "\n")

    # 1. Preparar Dados
    tf = "15"
    win = pl.read_parquet(get_data_path("WIN$", tf)).select(["time", "open", "high", "low", "close"]).rename({
        "close": "win_close", "high": "win_high", "low": "win_low", "open": "win_open"
    })
    wdo = pl.read_parquet(get_data_path("WDO$", tf)).select(["time", "close"]).rename({"close": "wdo_close"})
    di = pl.read_parquet(get_data_path("DI1$", tf)).select(["time", "close"]).rename({"close": "di_close"})
    data = win.join(wdo, on="time", how="inner").join(di, on="time", how="inner").sort("time")

    # 2. Configurar Risco e Engine
    sizer = KellySizer(win_rate=0.55, win_loss_ratio=1.5, fraction=0.3)
    rm = RiskManager(RiskParameters(stop_loss_pct=0.5, take_profit_pct=1.0), sizer=sizer)
    costs = CostModel(commission_per_trade=0.01, slippage_pct=0.005) 
    engine = VectorizedEngine(exit_horizon=40, cost_model=costs)
    
    # 3. Rodar Estratégia
    strategy = IFRPullbackTrinity(target_asset="win", ma_period=400, atr_mult_sl=2.5)
    metrics = engine.run(data, strategy, risk_manager=rm)
    trades_log = engine.get_trades()
    
    # Adicionar os indicadores calculados de volta ao dataframe para plotagem
    processed_data = strategy.generate_signals(data)

    # 4. Gerar Plots
    plot_backtest_results(processed_data, trades_log)

    print("\n" + "="*70)
    print(f" RESULTADO FINAL: PF {metrics['profit_factor']:.2f} | Trades: {metrics['trades_count']} ")
    print("="*70 + "\n")

if __name__ == "__main__":
    generate_full_visual_report()
