import polars as pl
import os
from src.research.utils import (
    calculate_rsi_200, get_data_path, get_rsi_level_advance_pl, 
    get_rsi_slope_pl, print_research_header, save_experiment
)
from src.research.obtr_research.obtr_bollinger import OBTRBollinger
from src.research.config import TRANSACTION_COST

def run_global_obtr_pullback_audit():
    symbols = ["WIN$", "WDO$", "DI1$"]
    tfs = ["5", "15", "30", "60"]
    h = 40
    
    all_stats = []
    indicator = OBTRBollinger()

    print_research_header("AUDITORIA GLOBAL: PULLBACK (SLOPE 10) + OBTR BOLLINGER")

    for symbol in symbols:
        for tf in tfs:
            path = get_data_path(symbol, tf)
            if not os.path.exists(path): continue

            # 1. Pipeline de Dados
            df = pl.read_parquet(path)
            df = df.with_columns([pl.Series("rsi", calculate_rsi_200(df['close'].to_numpy()))])
            
            df = df.with_columns([
                get_rsi_level_advance_pl("rsi").alias("advance"),
                get_rsi_slope_pl("rsi", period=10).alias("slope"),
                ((pl.col("rsi") >= 48) & (pl.col("rsi") <= 52)).alias("in_zone"),
                ((pl.col("close").shift(-h) / pl.col("close") - 1) * 100 - TRANSACTION_COST).alias("buy_ret"),
                ((pl.col("close") / pl.col("close").shift(-h) - 1) * 100 - TRANSACTION_COST).alias("sell_ret")
            ])

            # 2. Gatilhos e OBTR
            df = df.with_columns([
                (pl.col("in_zone") & (pl.col("advance") == 1) & (pl.col("slope") > 0)).alias("v_buy"),
                (pl.col("in_zone") & (pl.col("advance") == -1) & (pl.col("slope") < 0)).alias("v_sell")
            ])
            df = indicator.compute(df)
            
            # Cálculo de Slope no OBTR (Variação de 10 períodos)
            df = df.with_columns([
                (pl.col("obtr") - pl.col("obtr").shift(10)).alias("obtr_slope_10")
            ])

            # 3. Auditoria de Estados
            states = [
                ("Baseline", pl.lit(True)),
                ("OBTR_Extreme_Down", pl.col("obtr") < pl.col("bb_lower")),
                ("OBTR_Slope_Confirm", (pl.col("obtr") < pl.col("bb_lower")) & (pl.col("obtr_slope_10") < 0)),
                ("OBTR_Trend_Bear", pl.col("obtr") < pl.col("obtr_rma_200"))
            ]

            for t_type, trigger_col, ret_col in [("BUY", "v_buy", "buy_ret"), ("SELL", "v_sell", "sell_ret")]:
                for state_name, state_cond in states:
                    signals = df.filter(pl.col(trigger_col) & state_cond).drop_nulls()
                    if len(signals) < 15: continue # Filtro de relevância estatística

                    wr = (signals[ret_col] > 0).mean() * 100
                    gp = signals.filter(pl.col(ret_col) > 0)[ret_col].sum()
                    gl = abs(signals.filter(pl.col(ret_col) <= 0)[ret_col].sum())
                    pf = gp / (gl + 1e-9)
                    
                    all_stats.append({
                        "Asset": symbol, "TF": tf, "Type": t_type, "State": state_name,
                        "Trades": len(signals), "WR": wr, "PF": pf
                    })

    # 4. Relatório Consolidado (Top Performers)
    import pandas as pd
    res_df = pd.DataFrame(all_stats)
    
    print("\n" + "="*85)
    print(f"{'TOP PERFORMERS: CONFLUÊNCIA OBTR (PF > 1.30)'.center(85)}")
    print("="*85)
    top = res_df[res_df['PF'] > 1.30].sort_values(by="PF", ascending=False)
    print(top.to_string(index=False))
    
    save_experiment("global_obtr_audit", {}, res_df)

if __name__ == "__main__":
    run_global_obtr_pullback_audit()
