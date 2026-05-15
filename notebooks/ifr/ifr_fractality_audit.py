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

def run_fractality_audit(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path):
        print(f"[ERRO] Arquivo não encontrado: {path}")
        return None
    
    # 1. Carregar Dados
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 2. Calcular IFRs (Diferentes escalas para Fractalidade)
    df['ifr_200'] = calculate_rsi_wilder(df['close'], period=200)
    df['ifr_50'] = calculate_rsi_wilder(df['close'], period=50)
    df['ifr_9'] = calculate_rsi_wilder(df['close'], period=9)
    df['ifr_2'] = calculate_rsi_wilder(df['close'], period=2)
    
    # 3. Calcular Retornos Futuros (Curto, Médio, Longo Prazo)
    horizons = [5, 20, 60]
    for h in horizons:
        # Para DI1$, retornos são calculados em pontos (bps), para outros em %
        if "DI1" in symbol:
            df[f'fwd_ret_{h}'] = (df['close'].shift(-h) - df['close']) * 100 # bps
        else:
            df[f'fwd_ret_{h}'] = (df['close'].shift(-h) / df['close'] - 1) * 100
            
    # 4. Criar Blocos Inteiros de IFR 200
    df['ifr_block'] = df['ifr_200'].fillna(0).apply(np.floor).astype(int)
    
    # 5. Filtrar zona de interesse (40 a 60)
    df_study = df[(df['ifr_block'] >= 40) & (df['ifr_block'] <= 60)].copy()
    
    if len(df_study) == 0:
        return None

    # 6. Agregação por Bloco
    # Queremos ver o retorno médio, WR e o estado dos IFRs menores
    agg_dict = {
        'fwd_ret_20': ['mean', 'count'],
        'ifr_50': 'mean',
        'ifr_9': 'mean',
        'ifr_2': 'mean'
    }
    
    # Adicionar WR para ret_20
    df_study['win_20'] = (df_study['fwd_ret_20'] > 0).astype(int)
    agg_dict['win_20'] = 'mean'
    
    report = df_study.groupby('ifr_block').agg(agg_dict)
    
    # Flatten columns
    report.columns = ['Ret_Avg_20', 'Samples', 'IFR50_Avg', 'IFR9_Avg', 'IFR2_Avg', 'WR_20']
    report = report.reset_index()
    
    # Adicionar retorno 5 e 60 para ver fractalidade
    ret_5 = df_study.groupby('ifr_block')['fwd_ret_5'].mean()
    ret_60 = df_study.groupby('ifr_block')['fwd_ret_60'].mean()
    report = report.merge(ret_5, on='ifr_block').merge(ret_60, on='ifr_block')
    
    return report

def main():
    print_research_header("ESTUDO DE FRACTALIDADE E BLOCOS DE IFR 200 (40-60)")
    
    assets = ["WIN$", "WDO$", "DI1$"]
    all_results = {}
    
    for asset in assets:
        print(f"\n[ANALISANDO ATIVO: {asset}] ...")
        report = run_fractality_audit(asset)
        
        if report is not None:
            all_results[asset] = report
            # Mostrar os top 5 e a zona crítica
            print(report.sort_values('ifr_block').to_string(index=False))
            
            # Cálculo do Divisor de Águas (Salto entre 49 e 51)
            try:
                ret_49 = report[report['ifr_block'] == 49]['Ret_Avg_20'].values[0]
                ret_51 = report[report['ifr_block'] == 51]['Ret_Avg_20'].values[0]
                delta = ret_51 - ret_49
                print(f"\n>>> Delta de Transição (49 -> 51): {delta:+.4f}%")
                if delta > 0:
                    print(">>> VALIDADO: 50 atua como divisor de tendência positiva.")
                else:
                    print(">>> ALERTA: 50 não mostrou inversão clara de tendência neste ativo.")
            except:
                pass
            
            # Salvar CSV
            output_path = f"results/fractality_{asset.replace('$', '')}.csv"
            os.makedirs("results", exist_ok=True)
            report.to_csv(output_path, index=False)
            print(f"[INFO] Relatório salvo em: {output_path}")

    # Conclusão Fractal
    print("\n" + "="*80)
    print("RESUMO DA FRACTALIDADE".center(80))
    print("="*80)
    print("Observação sugerida: Note como IFRs menores (2, 9) se comportam quando o 200 está em 50.")
    print("Geralmente, quando o IFR 200 está entre 48-52, o IFR 2 é altamente volátil,")
    print("indicando que é o momento de 'posicionamento' (acumulação/distribuição).")

if __name__ == "__main__":
    main()
