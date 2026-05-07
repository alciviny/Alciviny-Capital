import matplotlib.pyplot as plt
import seaborn as sns
import polars as pl
from pathlib import Path

def plot_backtest_results(data: pl.DataFrame, trades_log: pl.DataFrame, output_dir: str = "src/backtest/reports/plots"):
    """
    Gera plots de alta qualidade para as entradas, saídas e curva de patrimônio.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Configuração de Estilo (Premium Dark)
    plt.style.use('dark_background')
    sns.set_palette("viridis")
    
    # 1. Plot de Trades no Gráfico de Preço
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 14), gridspec_kw={'height_ratios': [3, 1, 1]}, sharex=True)
    
    # Subplot 1: Preço e Médias
    ax1.plot(data["time"], data["win_close"], color='#4a90e2', alpha=0.6, label="WIN Close")
    if "target_ma" in data.columns:
        ax1.plot(data["time"], data["target_ma"], color='#f39c12', linestyle='--', label="MA Trend Filter")
    elif "win_ma400" in data.columns:
        ax1.plot(data["time"], data["win_ma400"], color='#f39c12', linestyle='--', label="MA 400")

    # Plotar Entradas e Saídas
    buy_signals = trades_log.filter(pl.col("signal") == 1)
    ax1.scatter(buy_signals["time"], buy_signals["entry_price"], color='#2ecc71', marker='^', s=100, label="ENTRY (Long)", zorder=5)
    
    # Saídas (Profit vs Loss)
    tp_exits = trades_log.filter(pl.col("pnl_pct") > 0)
    sl_exits = trades_log.filter(pl.col("pnl_pct") <= 0)
    ax1.scatter(tp_exits["time"], tp_exits["exit_price"], color='#27ae60', marker='v', s=80, label="EXIT (TP)", zorder=5)
    ax1.scatter(sl_exits["time"], sl_exits["exit_price"], color='#e74c3c', marker='x', s=80, label="EXIT (SL)", zorder=5)

    ax1.set_title("TRINITY STRATEGY: ENTRADAS E SAÍDAS", fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(alpha=0.2)

    # Subplot 2: IFR Adaptativo (P45/P55)
    if "target_rsi" in data.columns:
        ax2.plot(data["time"], data["target_rsi"], color='#9b59b6', label="RSI Target")
        ax2.fill_between(data["time"], data["t_dyn_low"], data["t_dyn_high"], color='#9b59b6', alpha=0.2, label="P45-P55 Zone")
    elif "win_rsi" in data.columns:
        ax2.plot(data["time"], data["win_rsi"], color='#9b59b6', label="WIN RSI")
        ax2.fill_between(data["time"], data["win_dyn_low"], data["win_dyn_high"], color='#9b59b6', alpha=0.2, label="P45-P55 Zone")

    ax2.set_title("RSI ADAPTATIVO (P45/P55)", fontsize=12)
    ax2.legend(loc='upper left')
    ax2.grid(alpha=0.2)

    # Subplot 3: Curva de Patrimônio (Equity)
    ax3.plot(trades_log["time"], trades_log["equity"], color='#1abc9c', linewidth=2, label="Equity Curve")
    ax3.fill_between(trades_log["time"], trades_log["equity"], trades_log["equity"].min(), color='#1abc9c', alpha=0.1)
    ax3.set_title("CURVA DE PATRIMÔNIO (REALISMO INDUSTRIAL)", fontsize=12)
    ax3.legend(loc='upper left')
    ax3.grid(alpha=0.2)

    plt.tight_layout()
    plot_path = f"{output_dir}/trinity_backtest_visual.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()
    
    print(f"  > Gráfico de trades gerado: {plot_path}")
    return plot_path
