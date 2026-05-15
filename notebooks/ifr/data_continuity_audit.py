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

from src.research.utils import get_data_path, print_research_header

def audit_data_quality(symbol, timeframe="15"):
    path = get_data_path(symbol, timeframe)
    if not os.path.exists(path): return None
    
    df = pl.read_parquet(path).to_pandas()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time')
    
    # 1. Verificar Duplicatas
    duplicates = df['time'].duplicated().sum()
    
    # 2. Verificar Gaps de Tempo (Intraday)
    df['diff'] = df['time'].diff().dt.total_seconds() / 60
    
    # Gaps suspeitos: > 15 min durante o dia
    df['hour'] = df['time'].dt.hour
    intraday_gaps = df[(df['hour'] >= 10) & (df['hour'] <= 17) & (df['diff'] > 15)]
    
    # 4. Verificar Estagnação (Clusters de Preço Fixo)
    df['is_stale'] = df['close'].diff() == 0
    df['stale_group'] = (df['is_stale'] != df['is_stale'].shift()).cumsum()
    stale_distribution = df[df['is_stale']].groupby('stale_group')['is_stale'].count()
    
    stats = {
        'Ativo': symbol,
        'Total Barras': len(df),
        'Duplicatas': duplicates,
        'Gaps Intraday (>15min)': len(intraday_gaps),
        'Tempo Total em Gaps (min)': intraday_gaps['diff'].sum(),
        'Barras Estagnadas (Total)': df['is_stale'].sum(),
        'Máx Estagnação (Barras)': stale_distribution.max() if not stale_distribution.empty else 0,
        'Estagnação Média (Barras)': stale_distribution.mean() if not stale_distribution.empty else 0,
        'Estagnação %': (df['is_stale'].sum() / len(df)) * 100
    }
    
    return stats, intraday_gaps.head(10)

def main():
    print_research_header("AUDITORIA DE QUALIDADE DE DADOS (DATA CONTINUITY)")
    
    summary = []
    for asset in ["WIN$", "WDO$", "DI1$"]:
        print(f"\n[AUDITANDO: {asset}]")
        stats, sample_gaps = audit_data_quality(asset)
        if stats:
            summary.append(stats)
            for k, v in stats.items():
                print(f"{k}: {v}")
            
            if not sample_gaps.empty:
                print("\nExemplos de Gaps Detectados (Top 10):")
                print(sample_gaps[['time', 'diff']].to_string(index=False))
                
    # Relatório
    report_path = "notebooks/ifr/results/data_quality_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    df_sum = pd.DataFrame(summary)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Integridade de Dados\n\n")
        f.write("Esta auditoria verifica a continuidade e qualidade da base de dados histórica.\n\n")
        f.write(df_sum.to_markdown(index=False))
        f.write("\n\n## Conclusões\n")
        f.write("1. **Gaps Intraday**: Se houver muitos gaps > 15min, os indicadores (IFR, Médias) podem estar 'pulando' informações críticas.\n")
        f.write("2. **Estagnação**: Preço constante por muito tempo indica perda de conexão com o provedor de dados durante a gravação.\n")
        f.write("3. **Duplicatas**: Podem distorcer cálculos de momentum e volume.\n")

    print(f"\n[SUCESSO] Auditoria concluída. Relatório em: {report_path}")

if __name__ == "__main__":
    main()
