import pandas as pd
import numpy as np
import polars as pl
import os
import sys
import logging
from typing import Dict, List

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IFR1000Study")

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path, print_research_header
from src.indicators.oscillators import calculate_rsi_wilder
from src.indicators.regime.regime_service import RegimeService
from src.indicators.regime.fci import FinancialConditionsIndex

def load_and_align_data(timeframe="15"):
    """Carrega WIN, WDO e DI1 e alinha os dados."""
    assets = ["WIN$", "WDO$", "DI1$"]
    dfs = {}
    
    for asset in assets:
        path = get_data_path(asset, timeframe)
        if not os.path.exists(path):
            logger.error(f"Arquivo não encontrado: {path}")
            continue
        
        # Carregar via Polars e converter para Pandas
        df_pl = pl.read_parquet(path)
        df_pd = df_pl.to_pandas()
        df_pd['time'] = pd.to_datetime(df_pd['time'])
        df_pd = df_pd.sort_values('time').set_index('time')
        
        # Manter apenas o close para alinhamento
        name = asset.replace("$", "").lower()
        dfs[name] = df_pd[['close']]
    
    # Concatenar e remover NaNs (alinhamento temporal)
    combined = pd.concat([dfs['win'], dfs['wdo'], dfs['di1']], axis=1)
    combined.columns = ['win', 'wdo', 'di1']
    combined = combined.dropna()
    
    return combined

def run_ifr_1000_study(timeframe="15"):
    print_research_header("ESTUDO DE CORRELAÇÃO: IFR 1000 PERIODOS vs REGIMES DE MERCADO")
    
    # 1. Carregar Dados
    logger.info(f"Carregando e alinhando dados ({timeframe})...")
    df = load_and_align_data(timeframe)
    if df.empty:
        logger.error("Dados insuficientes para o estudo.")
        return

    # 2. Calcular IFR 1000 para WIN e WDO
    logger.info("Calculando IFR 1000 para WIN e WDO...")
    df['ifr_win'] = calculate_rsi_wilder(df['win'], period=1000)
    df['ifr_wdo'] = calculate_rsi_wilder(df['wdo'], period=1000)
    
    # 3. Calcular Regimes via RegimeService
    logger.info("Calculando indicadores de regime (DCC, Hurst, Entropia, Meta)...")
    regime_service = RegimeService()
    regime_output = regime_service.get_regime_signal(df[['win', 'wdo', 'di1']])
    
    # 4. Calcular FCI (Financial Conditions Index)
    logger.info("Calculando Financial Conditions Index (PCA)...")
    fci_engine = FinancialConditionsIndex(rolling_window=252)
    fci_engine.preprocess(df[['win', 'wdo', 'di1']])
    fci_engine.rolling_pca()
    fci_output = fci_engine.classify_regimes()
    
    # 5. Calcular Hurst Bruto para WIN (para ter o valor numérico)
    logger.info("Calculando Hurst DFA bruto para WIN...")
    from src.indicators.regime.hurst import HurstDFACalculator
    
    hurst_calc = HurstDFACalculator(window=126)
    win_rets_pd = df['win'].pct_change().dropna()
    win_hurst_df = hurst_calc.compute_rolling(win_rets_pd)
    
    # Unir resultados
    logger.info(f"Normalizando índices para join... Price index name: {df.index.name}")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    regime_output.index = pd.to_datetime(regime_output.index).tz_localize(None)
    fci_output.index = pd.to_datetime(fci_output.index).tz_localize(None)
    win_hurst_df.index = pd.to_datetime(win_hurst_df.index).tz_localize(None)
    
    df.index.name = 'date'
    combined_base = df.join(regime_output, how='inner')
    combined_base = combined_base.join(fci_output[['z_fci', 'macro_regime']], how='inner', rsuffix='_fci')
    combined_base = combined_base.join(win_hurst_df[['hurst']].rename(columns={'hurst': 'hurst_value'}), how='inner')
    
    # Criar dataset expandido (Melt de IFR)
    df_win = combined_base.copy()
    df_win['ifr_1000'] = df_win['ifr_win']
    df_win['source'] = 'WIN'
    
    df_wdo = combined_base.copy()
    df_wdo['ifr_1000'] = df_wdo['ifr_wdo']
    df_wdo['source'] = 'WDO'
    
    study_df = pd.concat([df_win, df_wdo])
    
    logger.info(f"Registros após joins e expansão: {len(study_df)}")
    
    study_df = study_df.dropna(subset=['ifr_1000', 'meta_regime_state'])
    logger.info(f"Registros após dropna: {len(study_df)}")

    # 6. Definir Territórios do IFR 1000
    def categorize_territory(v):
        if v > 52: return "Bull Territory (>52)"
        if v < 48: return "Bear Territory (<48)"
        if 50 <= v <= 52: return "Neutral-High (50-52)"
        if 48 <= v < 50: return "Neutral-Low (48-50)"
        return "Boundary"

    study_df['territory'] = study_df['ifr_1000'].apply(categorize_territory)
    
<<<<<<< HEAD
    # Debug: Ver distribution
=======
    # Debug: Ver distribuição
>>>>>>> 13985eb (sync: prepare local for remote pull)
    logger.info(f"IFR 1000 Stats: Min={study_df['ifr_1000'].min():.2f}, Max={study_df['ifr_1000'].max():.2f}")
    logger.info(f"Contagem por Território:\n{study_df['territory'].value_counts()}")
    
    # 7. Analisar Regimes por Território
    territories = ["Bull Territory (>52)", "Neutral-High (50-52)", "Neutral-Low (48-50)", "Bear Territory (<48)", "Boundary"]
    results = []
    
    for terr in territories:
        z_df = study_df[study_df['territory'] == terr]
        if z_df.empty:
            results.append({
                'Território IFR 1000': terr,
                'Amostras': 0,
                'Hurst Médio': "N/A",
                'FCI Z-Score': "N/A",
                'Meta Stability%': "0%",
                'DCC Stress%': "0%",
                'PE Score': "N/A",
                'Macro Regime': "N/A"
            })
            continue
        
        # Hurst & FCI
        hurst_mean = z_df['hurst_value'].mean()
        fci_z_mean = z_df['z_fci'].mean()
        
        # Frequência de Meta-Regime Estável (CRYSTALLIZED + STABLE)
        meta_counts = z_df['meta_regime_state'].value_counts(normalize=True) * 100
        stability_freq = meta_counts.get('CRYSTALLIZED', 0) + meta_counts.get('STABLE', 0)
        
        # Frequência de DCC Stress
        dcc_counts = z_df['dcc_regime'].value_counts(normalize=True) * 100
        stress_freq = dcc_counts.get('STRESS', 0)
        
        # Macro Regime Predominante
        macro_top = z_df['macro_regime'].mode()[0] if not z_df['macro_regime'].empty else "N/A"
        
        # Scores
        pe_mean = z_df['pe_score'].mean()
        
        results.append({
            'Território IFR 1000': terr,
            'Amostras': len(z_df),
            'Hurst Médio': f"{hurst_mean:.3f}",
            'FCI Z-Score': f"{fci_z_mean:.2f}",
            'Meta Stability%': f"{stability_freq:.1f}%",
            'DCC Stress%': f"{stress_freq:.1f}%",
            'PE Score': f"{pe_mean:.3f}",
            'Macro Regime': macro_top
        })

    summary_df = pd.DataFrame(results)
    
    # 7. Catalogação Granular (40 a 60)
    logger.info("Gerando catalogação granular por nível de IFR (40-60)...")
    study_df['ifr_level'] = study_df['ifr_1000'].round().astype(int)
    granular_levels = sorted([l for l in study_df['ifr_level'].unique() if 40 <= l <= 60])
    
    granular_stats = []
    for level in granular_levels:
        ldf = study_df[study_df['ifr_level'] == level]
        if len(ldf) < 10: continue
        
        # Recalcular métricas para garantir precisão
        stab_count = ldf['meta_regime_state'].isin(['STABLE', 'CRYSTALLIZED']).sum()
        meta_stability = (stab_count / len(ldf)) * 100
        dcc_stress = (ldf['dcc_regime'] == 'STRESS').mean() * 100
        macro_regime = ldf['macro_regime'].mode()[0] if not ldf['macro_regime'].mode().empty else "N/A"
        
        granular_stats.append({
            "IFR Level": level,
            "Amostras": len(ldf),
            "Hurst": ldf['hurst_value'].mean(),
            "FCI Z": ldf['z_fci'].mean(),
            "Stability%": f"{meta_stability:.1f}%",
            "Stress%": f"{dcc_stress:.1f}%",
            "Macro": macro_regime
        })
    
    granular_df = pd.DataFrame(granular_stats)

    # 8. Gerar Relatório Markdown
    report_path = os.path.join(os.path.dirname(__file__), "results/ifr_1000_regime_correlation.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Estudo Avançado: IFR 1000 e Territórios de Regime\n\n")
        f.write("## 1. Catalogação por Território\n\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n## 2. Catalogação Granular (Por Nível de IFR)\n")
        f.write("Este mapeamento identifica a assinatura de regime para cada 'degrau' do IFR 1000.\n\n")
        if not granular_df.empty:
            f.write(granular_df.to_markdown(index=False))
        else:
            f.write("Dados insuficientes para catalogação granular no range 40-60.")
        
        f.write("\n\n## Conclusões sobre a Teoria de Território\n")
        f.write("- **Hurst vs IFR**: Verifique se a persistência (Hurst > 0.55) aumenta em níveis específicos.\n")
        f.write("- **FCI vs IFR**: Níveis com FCI Z-Score positivo e crescente indicam deterioração macro.\n")
        f.write("- **Zonas de Transição**: Níveis com baixa Stability% são zonas de alta incerteza operacional.\n")

    logger.info(f"Estudo concluído. Resultados salvos em: {report_path}")

if __name__ == "__main__":
<<<<<<< HEAD
=======
    # Verificar se hurst_score existe no MetaRegimeDetector.detect
    # Vou rodar uma pequena inspeção antes se necessário, mas o script acima já loga as colunas.
>>>>>>> 13985eb (sync: prepare local for remote pull)
    run_ifr_1000_study(timeframe="15")
