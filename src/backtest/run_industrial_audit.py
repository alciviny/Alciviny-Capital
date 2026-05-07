import polars as pl
from src.core.paths import get_data_path
from src.backtest.engine.vectorized import VectorizedEngine
from src.backtest.strategies.ifr_pullback_trinity import IFRPullbackTrinity
from src.backtest.gatekeeper import IndustrialGatekeeper
from src.backtest.risk.manager import RiskManager, RiskParameters
from src.backtest.risk.sizing import KellySizer

def run_multi_asset_industrial_audit():
    assets = ["WIN", "WDO"]
    timeframes = ["5", "15", "30", "60"]
    
    # Configuração de Risco Padrão
    params = RiskParameters(stop_loss_pct=0.5, take_profit_pct=1.0)
    sizer = KellySizer(win_rate=0.55, win_loss_ratio=1.5, fraction=0.3)
    rm = RiskManager(params, sizer=sizer)
    
    for asset in assets:
        for tf in timeframes:
            print(f"\n>>> AUDITANDO {asset} {tf}min...")
            
            try:
                # 1. Carregar Dados
                df_target = pl.read_parquet(get_data_path(f"{asset}$", tf)).select(["time", "open", "high", "low", "close"])
                # Renomear para o formato esperado pela Trinity (win_close, wdo_close, di_close)
                # Note: Precisamos dos 3 ativos para a confluência
                
                # Para simplificar este audit, vamos carregar os 3 e dar join
                win = pl.read_parquet(get_data_path("WIN$", tf)).select(["time", "open", "high", "low", "close"]).rename({
                    "close": "win_close", "high": "win_high", "low": "win_low", "open": "win_open"
                })
                wdo = pl.read_parquet(get_data_path("WDO$", tf)).select(["time", "close"]).rename({"close": "wdo_close"})
                di = pl.read_parquet(get_data_path("DI1$", tf)).select(["time", "close"]).rename({"close": "di_close"})
                
                data = win.join(wdo, on="time", how="inner").join(di, on="time", how="inner").sort("time")

                # 2. Configurar Engine e Gatekeeper
                engine = VectorizedEngine(exit_horizon=40, target_asset=f"{asset.lower()}_close")
                gate = IndustrialGatekeeper(engine)
                
                # 3. Validar
                strategy = IFRPullbackTrinity(target_asset=asset.lower(), ma_period=400)
                gate.validate(data, strategy, risk_manager=rm)
                
            except Exception as e:
                print(f"Erro ao auditar {asset} {tf}: {e}")

if __name__ == "__main__":
    run_multi_asset_industrial_audit()
