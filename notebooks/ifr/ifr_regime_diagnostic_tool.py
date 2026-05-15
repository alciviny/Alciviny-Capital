import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

# Adicionar raiz ao path para importar src
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.research.utils import get_data_path
from src.indicators.oscillators import calculate_rsi_wilder
from src.indicators.regime.regime_service import RegimeService

@dataclass
class DiagnosticContract:
    """Contrato de dados para o diagnóstico de regime."""
    df: pd.DataFrame
    symbol: str
    timeframe: str
    metrics: List[str]

class IFRRegimeEngine:
    """Responsabilidade: Processamento e Alinhamento de Dados."""
    
    def __init__(self):
<<<<<<< HEAD
        self.regime_service = RegimeService()

    def compute_diagnostics(self, symbol: str, timeframe: str = "15") -> DiagnosticContract:
=======
        # O RegimeService carrega as configs e inicializa os detectores
        self.regime_service = RegimeService()

    def compute_diagnostics(self, symbol: str, timeframe: str = "15") -> DiagnosticContract:
        # 1. Carregar dados
>>>>>>> 13985eb (sync: prepare local for remote pull)
        path = get_data_path(symbol, timeframe)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Dados não encontrados em {path}")
            
        df_pl = pd.read_parquet(path)
<<<<<<< HEAD
        if 'time' in df_pl.columns:
            df = df_pl.set_index('time')
        else:
            df = df_pl
            
        df.index = pd.to_datetime(df.index)

        # Processar via RegimeService
=======
        # Garantir que temos 'time' e 'close'
        if 'time' in df_pl.columns:
            df = df_pl.set_index('time')
        else:
            df = df_pl # assume index ja e time ou algo similar
            
        df.index = pd.to_datetime(df.index)

        # 2. Calcular IFR 1000
        print(f"[ENGINE] Calculando IFR 1000 para {symbol}...")
        df['ifr_1000'] = calculate_rsi_wilder(df['close'], period=1000)

        # 3. Processar Regimes via Service
        print(f"[ENGINE] Processando RegimeService (DCC, Hurst, Meta)...")
        # O RegimeService espera [win, wdo, di1] ou [ibov, dol, di1]
        # Para este diagnóstico individual, usamos o próprio ativo como proxy para os outros se necessário
        # mas idealmente carregaríamos os 3 como no script de estudo.
        # Vamos carregar os 3 para garantir que o DCC funcione corretamente.
        
>>>>>>> 13985eb (sync: prepare local for remote pull)
        assets = ["WIN$", "WDO$", "DI1$"]
        dfs = {}
        for a in assets:
            a_path = get_data_path(a, timeframe)
            a_df = pd.read_parquet(a_path)
            a_df['time'] = pd.to_datetime(a_df['time'])
            dfs[a.replace("$", "").lower()] = a_df.set_index('time')[['close']]
        
        combined = pd.concat([dfs['win'], dfs['wdo'], dfs['di1']], axis=1)
        combined.columns = ['win', 'wdo', 'di1']
        combined = combined.dropna()
        
        regime_signals = self.regime_service.get_regime_signal(combined)
        
<<<<<<< HEAD
=======
        # 4. Consolidar métricas críticas
        # Usamos o win como base principal para o IFR 1000
>>>>>>> 13985eb (sync: prepare local for remote pull)
        df_base = combined[['win']].rename(columns={'win': 'close'})
        df_base['ifr_1000'] = calculate_rsi_wilder(df_base['close'], period=1000)
        
        diagnostic_df = df_base.join(regime_signals, how='inner')
        
<<<<<<< HEAD
=======
        # Mapeamento do CSD (ar1 no MetaRegimeDetector)
>>>>>>> 13985eb (sync: prepare local for remote pull)
        if 'ar1' in diagnostic_df.columns:
            diagnostic_df['csd_score'] = diagnostic_df['ar1']
        else:
            diagnostic_df['csd_score'] = 0.0

        return DiagnosticContract(
            df=diagnostic_df,
            symbol=symbol,
            timeframe=timeframe,
            metrics=['ifr_1000', 'csd_score', 'meta_score', 'velocity_score']
        )

class IFRRegimeVisualizer:
    """Responsabilidade: Renderização e Visualização de Transições."""

    @staticmethod
    def plot_transition_zone(contract: DiagnosticContract):
<<<<<<< HEAD
        df = contract.df.tail(10000).dropna(subset=['ifr_1000', 'meta_score'])
        
        if df.empty:
=======
        # Correção: Janela expandida para capturar ciclos longos do IFR 1000
        df = contract.df.tail(10000).dropna(subset=['ifr_1000', 'meta_score'])
        
        if df.empty:
            print("[ERROR] DataFrame vazio após dropna. Verifique a disponibilidade de dados históricos.")
>>>>>>> 13985eb (sync: prepare local for remote pull)
            return

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 10), sharex=True, 
                                           gridspec_kw={'height_ratios': [2, 1, 0.4]})
        plt.subplots_adjust(hspace=0.08)

<<<<<<< HEAD
=======
        # Pane 1: IFR 1000 e Zones
>>>>>>> 13985eb (sync: prepare local for remote pull)
        ax1.plot(df.index, df['ifr_1000'], color='#2E86C1', label='IFR 1000', linewidth=1.5)
        ax1.axhline(52, color='#28B463', linestyle='--', alpha=0.6, label='Safety (52)')
        ax1.axhline(50, color='#85929E', linestyle='-', alpha=0.4)
        ax1.axhline(48, color='#CB4335', linestyle='--', alpha=0.6, label='Danger (48)')
<<<<<<< HEAD
        ax1.fill_between(df.index, 48, 52, color='#F4D03F', alpha=0.15, label='Transition Zone')
        ax1.set_ylabel("IFR 1000 Level", fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.2)

=======
        
        # Highlight Transições 48-52
        ax1.fill_between(df.index, 48, 52, color='#F4D03F', alpha=0.15, label='Transition Zone')
        ax1.set_ylabel("IFR 1000 Level", fontweight='bold')
        ax1.set_title(f"Diagnóstico de Transição de Regime: {contract.symbol} | IFR 1000", fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', frameon=True, shadow=True)
        ax1.grid(True, alpha=0.2)

        # Pane 2: Critical Slowing Down (CSD)
>>>>>>> 13985eb (sync: prepare local for remote pull)
        ax2.plot(df.index, df['csd_score'], color='#8E44AD', label='CSD Index (AR1 Trend)', linewidth=1.2)
        ax2.fill_between(df.index, 0, df['csd_score'], color='#8E44AD', alpha=0.1)
        ax2.axhline(0.6, color='#E67E22', linestyle=':', label='Warning Threshold')
        ax2.set_ylabel("CSD (Stability Loss)", fontweight='bold')
        ax2.set_ylim(-0.2, 1.1)
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.2)

<<<<<<< HEAD
        ax3.scatter(df.index, [0.5]*len(df), c=df['meta_score'], cmap='RdYlGn_r', 
                   marker='s', s=100, edgecolors='none')
=======
        # Pane 3: Meta-Regime Uncertainty (Alinhamento Temporal Corrigido)
        # Usamos scatter com markers largos como alternativa performática ao fill_between loop
        norm = plt.Normalize(df['meta_score'].min(), df['meta_score'].max())
        ax3.scatter(df.index, [0.5]*len(df), c=df['meta_score'], cmap='RdYlGn_r', 
                   marker='s', s=100, edgecolors='none')
        
>>>>>>> 13985eb (sync: prepare local for remote pull)
        ax3.set_ylabel("Regime\nStability", fontweight='bold')
        ax3.set_yticks([])
        ax3.set_ylim(0, 1)
        
<<<<<<< HEAD
        plt.tight_layout()
        output_path = f"notebooks/ifr/results/diagnostic_{contract.symbol.replace('$', '')}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150)

if __name__ == "__main__":
    engine = IFRRegimeEngine()
    visualizer = IFRRegimeVisualizer()
    contract = engine.compute_diagnostics("WIN$")
    visualizer.plot_transition_zone(contract)
=======
        # Adicionar eventos de quebra de 48
        events = []
        for i in range(1, len(df)):
            if (df['ifr_1000'].iloc[i-1] > 48 and df['ifr_1000'].iloc[i] <= 48):
                events.append(df.index[i])
                ax1.annotate('EVENT', (df.index[i], 48), 
                            xytext=(0, 15), textcoords='offset points',
                            arrowprops=dict(arrowstyle='->', color='red'),
                            color='red', fontweight='bold', fontsize=8)

        print(f"[VISUAL] Total de eventos de transição crítica identificados: {len(events)}")
        
        plt.tight_layout()
        
        output_path = f"notebooks/ifr/results/diagnostic_{contract.symbol.replace('$', '')}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=150)
        print(f"[INFO] Diagnóstico visual salvo em: {output_path}")

if __name__ == "__main__":
    try:
        engine = IFRRegimeEngine()
        visualizer = IFRRegimeVisualizer()
        
        symbol = "WIN$"
        print(f"\n[START] Diagnosticando {symbol}...")
        contract = engine.compute_diagnostics(symbol)
        
        print("[PROCESS] Gerando gráficos de alta resolução...")
        visualizer.plot_transition_zone(contract)
        
        print("\n[SUCCESS] Diagnóstico concluído com sucesso.")
    except Exception as e:
        print(f"\n[ERROR] Falha no diagnóstico: {e}")
        import traceback
        traceback.print_exc()
>>>>>>> 13985eb (sync: prepare local for remote pull)
