import pandas as pd
import numpy as np
import polars as pl
import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, print_research_header
from src.indicators.oscillators import calculate_rsi_wilder

def analyze_multi_ifr_confluence(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    # 1. Carregar Dados via Polars para performance
    df_pl = pl.read_parquet(path)
    
    # 2. Calcular IFRs
    df_pl = df_pl.with_columns([
        pl.Series("ifr_200", calculate_rsi_wilder(df_pl["close"].to_pandas(), 200)),
        pl.Series("ifr_50", calculate_rsi_wilder(df_pl["close"].to_pandas(), 50)),
        pl.Series("ifr_14", calculate_rsi_wilder(df_pl["close"].to_pandas(), 14))
    ])
    
    # 3. Definir "Tendência de Território" (Slope de 5 barras)
    df_pl = df_pl.with_columns([
        (pl.col("ifr_200") - pl.col("ifr_200").shift(5)).alias("slope_200"),
        (pl.col("ifr_50") - pl.col("ifr_50").shift(5)).alias("slope_50"),
        (pl.col("ifr_14") - pl.col("ifr_14").shift(5)).alias("slope_14")
    ])
    
    # 4. Retornos Futuros (20 barras)
    df_pl = df_pl.with_columns([
        (pl.col("close").shift(-20) / pl.col("close") - 1).alias("fwd_ret_20")
    ])
    
    # 5. Criar Matriz de Estados
    # 1: Avançando, -1: Recuando
    df_pl = df_pl.with_columns([
        pl.when(pl.col("slope_200") > 0).then(1).when(pl.col("slope_200") < 0).then(-1).otherwise(0).alias("st_200"),
        pl.when(pl.col("slope_50") > 0).then(1).when(pl.col("slope_50") < 0).then(-1).otherwise(0).alias("st_50"),
        pl.when(pl.col("slope_14") > 0).then(1).when(pl.col("slope_14") < 0).then(-1).otherwise(0).alias("st_14")
    ])
    
    # Filtrar nulos
    df_pl = df_pl.drop_nulls()
    
    # 6. Agregação da Matriz de Saúde
    # Vamos agrupar por (st_200, st_50, st_14) e ver o retorno médio
    results = df_pl.group_by(["st_200", "st_50", "st_14"]).agg([
        pl.col("fwd_ret_20").mean().alias("avg_ret"),
        pl.col("fwd_ret_20").count().alias("samples"),
        (pl.col("fwd_ret_20") > 0).mean().alias("win_rate")
    ]).sort(["st_200", "st_50", "st_14"])
    
    return results.to_pandas()

def interpret_state(row):
    mapping = {1: "Avanço", -1: "Recuo", 0: "Estável"}
    s200 = mapping.get(row['st_200'])
    s50 = mapping.get(row['st_50'])
    s14 = mapping.get(row['st_14'])
    
    if s200 == "Avanço" and s50 == "Avanço" and s14 == "Avanço": return "[ALTA] SAUDE MAXIMA (Sincronia)"
    if s200 == "Avanço" and s14 == "Recuo": return "[PULLBACK] EM TENDENCIA"
    if s200 == "Avanço" and s50 == "Recuo" and s14 == "Recuo": return "[AVISO] REVERSAO MACRO"
    if s200 == "Recuo" and s50 == "Recuo" and s14 == "Recuo": return "[BAIXA] QUEDA LIVRE (Sincronia)"
    if s200 == "Recuo" and s14 == "Avanço": return "[REPIQUE] EM BAIXA"
    return "---"

def main():
    print_research_header("AUDITORIA MULTI-PERÍODO: SINCRONIA DE TERRITÓRIOS")
    
    assets = ["WIN$", "WDO$", "DI1$"]
    
    for asset in assets:
        print(f"\n[ANALISANDO SINCRONIA: {asset}] ...")
        df = analyze_multi_ifr_confluence(asset)
        
        if df is not None:
            df['Interpretacao'] = df.apply(interpret_state, axis=1)
            # Converter ret para %
            df['avg_ret'] = df['avg_ret'] * 100
            df['win_rate'] = df['win_rate'] * 100
            
            # Mostrar os estados mais relevantes
            relevant = df[df['Interpretacao'] != "---"].sort_values('avg_ret', ascending=False)
            print(relevant[['st_200', 'st_50', 'st_14', 'avg_ret', 'win_rate', 'samples', 'Interpretacao']].to_string(index=False))
            
            # Salvar
            output_path = f"results/multi_conquest_{asset.replace('$', '')}.csv"
            df.to_csv(output_path, index=False)

if __name__ == "__main__":
    main()
