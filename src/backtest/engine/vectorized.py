from src.backtest.engine.base import BacktestEngine
from src.backtest.metrics.calculators import PerformanceCalculator
from src.backtest.utils.costs import CostModel
import polars as pl
from typing import Dict, Any

class VectorizedEngine(BacktestEngine):
    """
    Motor de backtesting ultra-rápido baseado em operações vetorizadas.
    Ideal para pesquisa e validação inicial de hipóteses.
    """
    def __init__(self, 
                 exit_horizon: int = 20, 
                 cost_model: CostModel = None,
                 target_asset: str = "win_close"):
        self.exit_horizon = exit_horizon
        self.cost_model = cost_model or CostModel()
        self.target_asset = target_asset
        self.trades_log = None

    def run(self, 
            data: pl.DataFrame, 
            strategy: Any, 
            risk_manager: Any = None, 
            initial_capital: float = 100000.0) -> Dict[str, Any]:
        """
        Executa o backtest vetorizado com realismo industrial (validação de stops).
        """
        # 1. Gerar Sinais (Alfa)
        df = strategy.generate_signals(data)
        
        # Identificar ativos base para stops (ex: win_high, win_low)
        base_asset = self.target_asset.replace("_close", "")
        high_col = f"{base_asset}_high"
        low_col = f"{base_asset}_low"

        # 2. Calcular Retornos com Realismo (Stops Intra-Horizonte)
        # Se risk_manager estiver presente, validamos SL/TP
        if risk_manager and high_col in df.columns:
            # Priorizar colunas dinâmicas da estratégia (sl_pct, tp_pct)
            # Se não existirem, usar valores fixos do RiskManager
            df = df.with_columns([
                pl.col("sl_pct") if "sl_pct" in df.columns else pl.lit(risk_manager.params.stop_loss_pct).alias("sl_pct"),
                pl.col("tp_pct") if "tp_pct" in df.columns else pl.lit(risk_manager.params.take_profit_pct).alias("tp_pct"),
            ])
            
            # Rolling Extremes nos próximos N candles (shift negativo para olhar frente)
            df = df.with_columns([
                pl.col(low_col).shift(-self.exit_horizon).rolling_min(window_size=self.exit_horizon).alias("next_min"),
                pl.col(high_col).shift(-self.exit_horizon).rolling_max(window_size=self.exit_horizon).alias("next_max"),
                ((pl.col(self.target_asset).shift(-self.exit_horizon) / pl.col(self.target_asset) - 1) * 100).alias("horizon_ret")
            ])

            # Lógica de PnL com Stops (Vetorizada)
            df = df.with_columns([
                pl.when(pl.col("signal") == 1)
                .then(
                    pl.when(pl.col("next_min") <= pl.col(self.target_asset) * (1 - pl.col("sl_pct")/100))
                    .then(-pl.col("sl_pct"))
                    .when(pl.col("next_max") >= pl.col(self.target_asset) * (1 + pl.col("tp_pct")/100))
                    .then(pl.col("tp_pct"))
                    .otherwise(pl.col("horizon_ret"))
                )
                .when(pl.col("signal") == -1)
                .then(
                    pl.when(pl.col("next_max") >= pl.col(self.target_asset) * (1 + pl.col("sl_pct")/100))
                    .then(-pl.col("sl_pct"))
                    .when(pl.col("next_min") <= pl.col(self.target_asset) * (1 - pl.col("tp_pct")/100))
                    .then(pl.col("tp_pct"))
                    .otherwise(pl.col("horizon_ret") * -1)
                )
                .otherwise(0.0)
                .alias("raw_ret")
            ])
        else:
            # Fallback para saída cega (antiga)
            df = df.with_columns([
                ((pl.col(self.target_asset).shift(-self.exit_horizon) / pl.col(self.target_asset) - 1) * 100).alias("raw_ret")
            ])

        # 3. Identificar Trades
        trades = df.filter(pl.col("signal") != 0).with_columns([
            pl.col(self.target_asset).alias("entry_price")
        ])
        
        if trades.height == 0:
            return {
                "trades_count": 0, "win_rate": 0.0, "profit_factor": 0.0, 
                "avg_ret": 0.0, "max_dd": 0.0, "final_capital": initial_capital
            }

        # 4. Aplicar Modelo de Custos
        total_cost_pct = self.cost_model.commission + self.cost_model.slippage
        trades = trades.with_columns([
            (pl.col("raw_ret") - total_cost_pct).alias("pnl_pct")
        ])
        
        # Calcular preço de saída aproximado para log
        trades = trades.with_columns([
            (pl.col("entry_price") * (1 + pl.col("pnl_pct")/100)).alias("exit_price")
        ])

        # 5. Simulação de Equity e Position Sizing
        capital = initial_capital
        equity_curve = [capital]
        
        pnl_array = trades["pnl_pct"].to_numpy() / 100 # Decimal
        signals = trades["signal"].to_numpy()
        
        sizer = risk_manager.sizer if risk_manager and hasattr(risk_manager, 'sizer') else None

        for i in range(len(pnl_array)):
            if sizer:
                allocated_capital = sizer.calculate_size(signals[i], capital)
            else:
                allocated_capital = capital 
            
            trade_pnl = allocated_capital * pnl_array[i]
            capital += trade_pnl
            equity_curve.append(capital)

            # Se o sizer for adaptativo, atualizamos com o resultado real deste trade
            if sizer and hasattr(sizer, 'update'):
                sizer.update(pnl_array[i] * 100) # Passamos em % para consistência

        # 6. Calcular Métricas Consolidadas
        calc = PerformanceCalculator()
        equity_series = pl.Series("equity", equity_curve)
        trades_with_pnl = trades.with_columns(pl.Series("pnl", pnl_array))

        metrics = {
            "trades_count": trades.height,
            "win_rate": (trades_with_pnl.filter(pl.col("pnl") > 0).height / trades.height) * 100,
            "profit_factor": calc.profit_factor(trades_with_pnl),
            "avg_ret": trades_with_pnl["pnl"].mean() * 100,
            "max_dd": calc.max_drawdown(equity_series) * 100,
            "recovery_factor": calc.recovery_factor(metrics_return_pct := (capital / initial_capital - 1) * 100, calc.max_drawdown(equity_series) * 100),
            "expectancy": calc.mathematical_expectation(trades_with_pnl) * 100,
            "final_capital": capital,
            "total_return_pct": metrics_return_pct
        }

        self.trades_log = trades.with_columns(pl.Series("equity", equity_curve[1:]))
        return metrics

    def get_trades(self) -> pl.DataFrame:
        """Retorna o log de trades detalhado."""
        return self.trades_log
