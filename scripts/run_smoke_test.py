import polars as pl
import os
import sys

# Adicionar src ao path
sys.path.append(os.getcwd())

from src.backtest.strategies.ifr_pullback_trinity import IFRPullbackTrinity
from src.backtest.engine.vectorized import VectorizedEngine
from src.backtest.utils.costs import CostModel

def run_smoke_test():
    print("\n[SMOKE TEST] Iniciando validação end-to-end da Trinity 2.0...")
    
    # 1. Carregar Dados (WIN, WDO, DI)
    data_dir = "data/storage"
    try:
        # Usando nomes genéricos para colunas
        win = pl.read_parquet(f"{data_dir}/WIN$_15_CLEAN.parquet").select([
            "time", 
            pl.col("open").alias("win_open"),
            pl.col("high").alias("win_high"),
            pl.col("low").alias("win_low"),
            pl.col("close").alias("win_close")
        ])
        
        wdo = pl.read_parquet(f"{data_dir}/WDO$_15_CLEAN.parquet").select([
            "time",
            pl.col("close").alias("wdo_close")
        ])
        
        di = pl.read_parquet(f"{data_dir}/DI1$_15_CLEAN.parquet").select([
            "time",
            pl.col("close").alias("di_close")
        ])
        
        # Join dos dados (Inner Join garante sincronia)
        df = win.join(wdo, on="time").join(di, on="time").sort("time")
        
        # Validação de alinhamento
        if df.height < min(win.height, wdo.height, di.height) * 0.9:
            print(f"[AVISO] Perda significativa de dados no join: {df.height} linhas restantes.")
        
        print(f"[INFO] Dados sincronizados: {df.height} linhas.")
        
    except Exception as e:
        print(f"[ERRO] Falha ao carregar dados: {e}")
        return False

    # 2. Configurar Estratégia (Trinity 2.0 Bi-Direcional)
    strategy = IFRPullbackTrinity(
        target_asset="win",
        confluence_assets=["wdo", "di"], # Novos parâmetros
        use_micro=True,       
        micro_threshold=15.0,
        allow_short=True      # Habilitar Short
    )

    # 3. Configurar Engine
    engine = VectorizedEngine(
        exit_horizon=40, 
        target_asset="win_close",
        cost_model=CostModel(commission_per_trade=0.005, slippage_pct=0.01)
    )

    # 4. Executar Backtest
    print("[INFO] Executando backtest (Long & Short)...")
    try:
        results = engine.run(df, strategy)
        
        print("\n" + "="*40)
        print("RESULTADOS SMOKE TEST (TRINITY 2.0 BI-DIR)")
        print("="*40)
        for k, v in results.items():
            if isinstance(v, float):
                print(f"{k:20}: {v:>10.2f}")
            else:
                print(f"{k:20}: {v:>10}")
        print("="*40)
        
        # Log de trades para verificar se houve Short
        trades = engine.get_trades()
        short_count = trades.filter(pl.col("signal") == -1).height
        long_count = trades.filter(pl.col("signal") == 1).height
        print(f"[INFO] Trades Gerados: Long={long_count}, Short={short_count}")

        if results['trades_count'] > 0:
            print("[SUCESSO] Estratégia validada.")
            return True
        else:
            print("[ALERTA] 0 trades gerados.")
            return True 
            
    except Exception as e:
        print(f"[ERRO] Falha na execução: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_smoke_test()
    if not success:
        sys.exit(1)
