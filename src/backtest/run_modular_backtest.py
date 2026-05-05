import polars as pl
import os
from src.backtest.core.engine import BacktestEngine
from src.backtest.strategies.v_accel import VAccelStrategy
from src.research.utils import get_data_path

def run_professional_backtest(symbol="WIN$", tf="15", stop_pts=300, target_pts=600):
    print(f"\n[INICIANDO BACKTEST MODULAR] {symbol} {tf}M")
    print(f"Config: Stop={stop_pts} pts | Alvo={target_pts} pts\n")

    # 1. Carregar Dados
    path = get_data_path(symbol, tf)
    df = pl.read_parquet(path)

    # 2. Instanciar Estratégia
    strategy = VAccelStrategy()
    df_with_signals = strategy.generate_signals(df)

    # 3. Configurar Motor e Risco
    engine = BacktestEngine(transaction_cost=0.02)
    risk_config = {
        "stop_pts": stop_pts,
        "target_pts": target_pts,
        "time_exit": 40
    }

    # 4. Executar
    trades = engine.run(df_with_signals, risk_config)

    # 5. Relatório Rápido
    if len(trades) > 0:
        win_rate = (trades["return_pct"] > 0).mean() * 100
        pf = trades.filter(pl.col("return_pct") > 0)["return_pct"].sum() / \
             abs(trades.filter(pl.col("return_pct") <= 0)["return_pct"].sum() + 1e-9)
        
        print("-" * 40)
        print(f"RESULTADOS {strategy.name}")
        print("-" * 40)
        print(f"Total Trades: {len(trades)}")
        print(f"Win Rate:     {win_rate:.1f}%")
        print(f"Profit Factor:{pf:.2f}")
        print(f"Retorno Médio:{trades['return_pct'].mean():.3f}%")
        print("-" * 40)
        
        # Salvar trades para auditoria
        output_dir = f"src/backtest/reports/{symbol}_{tf}_{strategy.name}"
        os.makedirs(output_dir, exist_ok=True)
        trades.write_parquet(f"{output_dir}/trades_audit.parquet")
        print(f"[OK] Auditoria salva em: {output_dir}")
    else:
        print("[AVISO] Nenhum trade gerado com os parâmetros atuais.")

if __name__ == "__main__":
    # Exemplo de execução profissional
    run_professional_backtest(symbol="WIN$", tf="15", stop_pts=250, target_pts=500)
