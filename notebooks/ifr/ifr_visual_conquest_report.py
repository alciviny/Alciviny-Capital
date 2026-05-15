import pandas as pd
import numpy as np
import polars as pl
import os
import sys
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, print_research_header
from src.indicators.oscillators import calculate_rsi_wilder

def generate_visual_report(symbol, timeframe="15", limit=500):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    # 1. Carregar Dados
    df = pl.read_parquet(path).tail(limit).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    
    # 2. Calcular IFRs
    df['ifr_200'] = calculate_rsi_wilder(df['close'], 200)
    df['ifr_50'] = calculate_rsi_wilder(df['close'], 50)
    df['ifr_14'] = calculate_rsi_wilder(df['close'], 14)
    
    # 3. Calcular Slopes (Momentum de Território)
    df['s200'] = df['ifr_200'].diff(3)
    df['s50'] = df['ifr_50'].diff(3)
    df['s14'] = df['ifr_14'].diff(3)
    
    # 4. Definir Regimes para Coloração
    df['regime'] = 0
    df.loc[(df['s200'] > 0) & (df['s50'] > 0) & (df['s14'] > 0), 'regime'] = 1 # Sincronia Alta
    df.loc[(df['s200'] > 0) & (df['s14'] < 0), 'regime'] = 2 # Pullback
    df.loc[(df['s200'] > 0) & (df['s50'] < 0) & (df['s14'] < 0), 'regime'] = 3 # Aviso Reversão
    df.loc[(df['s200'] < 0) & (df['s50'] < 0) & (df['s14'] < 0), 'regime'] = 4 # Queda Livre
    
    # 5. Criar Gráfico
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"Preo {symbol} - Regimes de Conquista", "IFR 200 (Anchor)", "IFR 50 & 14 (Timing)"))

    fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preco"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['ifr_200'], line=dict(color='orange', width=2), name="IFR 200"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['ifr_50'], line=dict(color='blue', width=1.5), name="IFR 50"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['ifr_14'], line=dict(color='cyan', width=1), name="IFR 14"), row=3, col=1)

    # 6. Adicionar Zonas de Regime
    colors = {1: "rgba(0, 255, 0, 0.1)", 2: "rgba(0, 0, 255, 0.1)", 3: "rgba(255, 255, 0, 0.1)", 4: "rgba(255, 0, 0, 0.1)"}
    
    # Otimizar vrects
    df['regime_change'] = (df['regime'] != df['regime'].shift(1)).astype(int).cumsum()
    regime_groups = df.groupby('regime_change').agg({'time': ['min', 'max'], 'regime': 'first'})
    
    for _, row in regime_groups.iterrows():
        reg = row[('regime', 'first')]
        if reg in colors:
            fig.add_vrect(x0=row[('time', 'min')], x1=row[('time', 'max')], fillcolor=colors[reg], opacity=1, layer="below", line_width=0, row="all", col=1)

    fig.update_layout(height=800, title_text=f"Saude IFR: {symbol}", template="plotly_dark", showlegend=False)
    fig.update_xaxes(rangeslider_visible=False)
    
    output_dir = os.path.join(project_root, "notebooks/ifr/results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"ifr_health_chart_{symbol.replace('$', '')}.html")
    fig.write_html(output_path)
    return output_path

def main():
    print_research_header("GERADOR DE RELATÓRIO VISUAL: SAÚDE IFR")
    
    assets = ["WIN$", "WDO$"]
    for asset in assets:
        print(f"Gerando gráfico para {asset}...")
        path = generate_visual_report(asset)
        if path:
            print(f"[SUCESSO] Gráfico gerado em: {path}")

if __name__ == "__main__":
    main()
