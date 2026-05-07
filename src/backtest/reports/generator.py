import json
import os
from datetime import datetime
from typing import Dict, Any
import polars as pl

class ReportGenerator:
    """
    Gera relatórios industriais de backtesting em Markdown e JSON.
    """
    def __init__(self, output_dir: str = "src/backtest/reports/artifacts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(self, strategy_name: str, metrics: Dict[str, Any], trades: pl.DataFrame):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{strategy_name}_{timestamp}"
        
        # 1. Exportar JSON
        json_path = os.path.join(self.output_dir, f"{filename_base}.json")
        with open(json_path, 'w') as f:
            # Converter tipos do numpy/polars para nativos do python
            serializable_metrics = {k: float(v) if not isinstance(v, (int, str)) else v for k, v in metrics.items()}
            json.dump(serializable_metrics, f, indent=4)
            
        # 2. Exportar Markdown (Audit Report format)
        md_path = os.path.join(self.output_dir, f"{filename_base}.md")
        with open(md_path, 'w') as f:
            f.write(f"# BACKTEST AUDIT REPORT: {strategy_name}\n")
            f.write(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Core Metrics\n")
            f.write(f"- **Total Trades:** {metrics['trades_count']}\n")
            f.write(f"- **Win Rate:** {metrics['win_rate']:.2f}%\n")
            f.write(f"- **Profit Factor:** {metrics['profit_factor']:.2f}\n")
            f.write(f"- **Max Drawdown:** {metrics['max_dd']:.2f}%\n")
            f.write(f"- **Total Return:** {metrics['total_return_pct']:.2f}%\n")
            f.write(f"- **Final Capital:** R$ {metrics['final_capital']:,.2f}\n\n")
            
            f.write("## Execution Realism\n")
            f.write("- **Engine:** VectorizedHybrid (OHLC Validation)\n")
            f.write("- **Cost Model:** Applied (Slippage + Commissions)\n\n")
            
        print(f"Relatório gerado com sucesso: {md_path}")
        return md_path
