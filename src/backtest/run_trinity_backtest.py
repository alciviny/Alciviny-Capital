import polars as pl
from src.backtest.engine.vectorized import VectorizedEngine
from src.backtest.strategies.ifr_pullback_trinity import IFRPullbackTrinity
from src.backtest.risk.sizing import KellySizer
from src.backtest.risk.manager import RiskManager, RiskParameters
from src.backtest.utils.costs import CostModel
from src.core.paths import get_data_path
import os

def main():
    print("\n" + "="*50)
    print("EXECUTANDO BACKTEST TRINITY (MODULAR)".center(50))
    print("="*50)

    # 1. Carregar e Sincronizar Dados
    # Usando 15min conforme o script de pesquisa
    win_path = get_data_path("WIN$", "15")
    wdo_path = get_data_path("WDO$", "15")
    di_path = get_data_path("DI1$", "15")

    if not all(os.path.exists(p) for p in [win_path, wdo_path, di_path]):
        print("[ERRO] Arquivos de dados não encontrados.")
        return

    win = pl.read_parquet(win_path).select(["time", "close"]).rename({"close": "win_close"})
    wdo = pl.read_parquet(wdo_path).select(["time", "close"]).rename({"close": "wdo_close"})
    di = pl.read_parquet(di_path).select(["time", "close"]).rename({"close": "di_close"})

    # Join para garantir alinhamento temporal
    data = win.join(wdo, on="time", how="inner").join(di, on="time", how="inner").sort("time")
    print(f"[INFO] Dados sincronizados: {data.height} linhas.")

    # 2. Configurar Estratégia (Trinity 2.0 Bi-Direcional)
    strategy = IFRPullbackTrinity(
        target_asset="win",
        confluence_assets=["wdo", "di"],
        rsi_period=200,
        quantile_window=1000,
        low_q=0.45,
        high_q=0.55,
        use_micro=True,
        allow_short=True
    )

    # 3. Configurar Motor, Custos e Gerenciamento de Capital
    costs = CostModel(commission_per_trade=0.02)
    
    # Kelly Sizer baseado nas estatísticas validadas
    # Agora o sizer pode ser atualizado dinamicamente se a engine suportar
    kelly_sizer = KellySizer(win_rate=0.56, win_loss_ratio=1.0, fraction=0.3)
    
    risk_params = RiskParameters(stop_loss_pct=0.02, take_profit_pct=0.04)
    risk_manager = RiskManager(risk_params)
    risk_manager.sizer = kelly_sizer

    engine = VectorizedEngine(exit_horizon=40, cost_model=costs, target_asset="win_close")

    # 4. Executar com Capital Inicial de R$ 100.000
    print("[INFO] Executando backtest industrial (Long & Short)...")
    results = engine.run(data, strategy, risk_manager=risk_manager, initial_capital=100000.0)

    # 5. Exibir Resultados
    print("\nRESULTADOS CONSOLIDADOS (TRINITY 2.0):")
    print("-" * 50)
    for k, v in results.items():
        if isinstance(v, float):
            print(f"{k:20}: {v:>15.2f}")
        else:
            print(f"{k:20}: {v:>15}")
    
    trades = engine.get_trades()
    if not trades.is_empty():
        l_count = trades.filter(pl.col("signal") == 1).height
        s_count = trades.filter(pl.col("signal") == -1).height
        print(f"Trades Long     : {l_count:>15}")
        print(f"Trades Short    : {s_count:>15}")
    
    print("-" * 50 + "\n")

if __name__ == "__main__":
    main()
