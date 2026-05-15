import pandas as pd
import numpy as np
import polars as pl
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, calculate_rsi_200, print_research_header
from src.indicators.oscillators import calculate_rsi_wilder

def analyze_adaptive_thresholds(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').set_index('time')
    
    # 1. Indicadores
    df['ifr_1000'] = calculate_rsi_wilder(df['close'], period=1000)
    df['ifr_200'] = calculate_rsi_200(df['close'].values, period=200)
    
    # Retornos futuros (20 bars)
    h = 20
    df['fwd_ret'] = (df['close'].shift(-h) / df['close'] - 1) * 100
    
    # 2. Definição de Intensidade de Tendência (IFR 1000)
    def get_intensity(v):
        if v > 55: return "Very Bull (>55)"
        if v > 52: return "Strong Bull (52-55)"
        if v > 48: return "Neutral (48-52)"
        if v > 45: return "Strong Bear (45-48)"
        return "Very Bear (<45)"
    
    df['intensity'] = df['ifr_1000'].apply(get_intensity)
    
    # 3. Grid Search por Nível de IFR 200
    # Queremos saber qual o retorno médio se comprarmos quando o IFR 200 cruza ACIMA de um nível L
    # dentro de cada zona de intensidade.
    
    levels = range(45, 61) # de 45 a 60
    intensities = ["Very Bull (>55)", "Strong Bull (52-55)", "Neutral (48-52)", "Strong Bear (45-48)", "Very Bear (<45)"]
    
    heatmap_data = []
    
    for intensity in intensities:
        idf = df[df['intensity'] == intensity].dropna(subset=['ifr_200', 'fwd_ret'])
        if idf.empty: continue
        
        for L in levels:
            # Sinal: IFR 200 cruza acima de L (Pullback em Bull ou Reversal em Bear)
            signals = (idf['ifr_200'] > L) & (idf['ifr_200'].shift(1) <= L)
            rets = idf[signals]['fwd_ret']
            
            if len(rets) > 5: # Mínimo de amostras
                exp = rets.mean()
                wr = (rets > 0).mean() * 100
            else:
                exp = np.nan
                wr = np.nan
            
            heatmap_data.append({
                'Intensity': intensity,
                'Level_IFR200': L,
                'Exp%': exp,
                'Win%': wr,
                'Samples': len(rets)
            })
            
    return pd.DataFrame(heatmap_data)

def main():
    print_research_header("SIMULAÇÃO DE ADAPTATIVIDADE: SHIFT DE CENTRO DO IFR 200")
    
    symbol = "WIN$"
    print(f"\n[BATERIA DE TESTES: {symbol}]")
    results = analyze_adaptive_thresholds(symbol)
    
    if results is not None:
        # Pivotar para melhor visualização
        pivot_exp = results.pivot(index='Intensity', columns='Level_IFR200', values='Exp%')
        # Reordenar intensidades
        order = ["Very Bull (>55)", "Strong Bull (52-55)", "Neutral (48-52)", "Strong Bear (45-48)", "Very Bear (<45)"]
        pivot_exp = pivot_exp.reindex(order)
        
        print("\n[EXPECTATIVA MÉDIA % POR NÍVEL E INTENSIDADE]")
        print(pivot_exp.to_string())
        
        # Salvar Relatório
        report_path = "notebooks/ifr/results/ifr_adaptive_audit_results.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Estudo de Adaptatividade: O Deslocamento do Centro (IFR 200)\n\n")
            f.write("Este estudo valida se o ponto ideal de pullback do IFR 200 se desloca para cima (53, 54, 55...) em tendências fortes.\n\n")
            
            f.write("## Matriz de Expectativa (Exp%)\n")
            f.write("As linhas representam a tendência macro (IFR 1000) e as colunas o nível tático de entrada (IFR 200).\n\n")
            f.write(pivot_exp.to_markdown())
            
            f.write("\n\n## Análise dos Achados\n")
            f.write("1. **Shift de Bull**: Verifique se em 'Very Bull', os níveis 53-55 apresentam maior expectativa que o 50.\n")
            f.write("2. **Zona de Exaustão**: Níveis acima de 58 em tendências fortes podem indicar exaustão em vez de pullback.\n")
            f.write("3. **Simetria Bear**: O centro também deve se deslocar para baixo (45-47) em tendências de queda forte.\n")

        print(f"\n[SUCESSO] Simulação concluída. Relatório em: {report_path}")

if __name__ == "__main__":
    main()
