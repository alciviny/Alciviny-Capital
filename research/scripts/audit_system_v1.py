import os
import sys
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime, date
import matplotlib.pyplot as plt
from typing import Dict, List, Any

# Root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.experiments.exp_001_institutional_core.engine import InstitutionalCore
from src.data.factory import StateVectorFactory
from src.models.meta import InstitutionalClassifier
from src.engine.router import StrategyRouter, FractionalKellySizer
from src.engine.gate import MacroRegimeGate

class SystemAuditor:
    def __init__(self, model_path: str):
        self.core = InstitutionalCore()
        self.factory = StateVectorFactory()
        self.clf = InstitutionalClassifier(model_path=model_path)
        self.sizer = FractionalKellySizer(kelly_base=0.5, max_exposure=1.0)
        self.gate = MacroRegimeGate()
        self.router = StrategyRouter(sizer=self.sizer, gate=self.gate)

    def run_audit(self, data: pl.DataFrame, target: str, confluences: List[str]):
        print(f"[{datetime.now()}] Iniciando Auditoria Crítica do Sistema v1.2.0...")
        
        # 1. Análise Institucional (MRS, DCC, Micro)
        results = self.core.run_full_analysis(data, target=target, confluences=confluences)
        
        # 2. State Vector e Predição Meta
        # Assumindo que o mapeamento BULL já foi validado no treino
        bull_id = next(k for k, v in self.core.markov.regime_map.items() if v == "BULL")
        bull_prob_col = f"regime_{bull_id}_prob"
        
        # State Vector 3D (para compatibilidade com modelo v1 se necessário, ou 5D se treinado)
        # Vamos usar o que o modelo espera
        use_micro = "ofi_z20" in self.clf.model.get_booster().feature_names if hasattr(self.clf.model, 'get_booster') else False
        
        sv_df = self.factory.generate(
            results, 
            target_col=target, 
            mrs_prob_cols=[bull_prob_col], 
            dcc_corr_col=f"corr_{target}_{confluences[0]}",
            use_microstructure=use_micro
        )
        
        # Adicionar Preço e Tempo de volta para o backtest
        sv_df = sv_df.join(results.select(["time", target, "regime_name"]), on="time")
        
        # 3. Predições
        features = self.factory.get_feature_names(mrs_prob_cols=[bull_prob_col], use_microstructure=use_micro)
        X = sv_df.select(features).to_pandas()
        meta_probs = self.clf.predict_proba(X)
        
        # 4. Simulação de Backtest (Vetorizada + Gate Loop)
        sv_df = sv_df.with_columns([
            ((pl.col(target).shift(-30) / pl.col(target) - 1)).alias("fwd_ret_30")
        ]).drop_nulls()
        
        pdf = sv_df.to_pandas()
        pdf['meta_bull_prob'] = meta_probs[:len(pdf), 1] # Assumindo 1 como BULL
        
        # Rodar Roteamento com e sem Gate
        results_list = []
        for i, row in pdf.iterrows():
            target_date = row['time'].date()
            # Prob vector mock para o router: [Bear, Bull, Crisis]
            # Como o modelo meta pode ter labels diferentes, vamos simplificar para Bull vs Outros
            probs = np.array([0.0, row['meta_bull_prob'], 0.0]) 
            labels = ["BEAR", "BULL", "CRISIS"]
            
            # 1. Apenas MRS (Baseline)
            mrs_prob = row['p_bull_mrs']
            mrs_size = self.sizer.calculate_size(mrs_prob, row['regime_name'])
            
            # 2. Meta Classifier SEM Gate
            meta_size_no_gate = self.sizer.calculate_size(row['meta_bull_prob'], "BULL")
            
            # 3. Meta Classifier COM Gate
            # Precisamos do VRP para o gate (se disponível no sv_df)
            vrp = row['vrp_z20'] if 'vrp_z20' in row else 0.0
            activations = self.router.route(probs, labels, target_date=target_date, current_vrp=vrp)
            meta_size_gate = activations.get("BULL", 0.0)
            
            results_list.append({
                "time": row['time'],
                "year": row['time'].year,
                "fwd_ret": row['fwd_ret_30'],
                "mrs_size": mrs_size,
                "meta_size_no_gate": meta_size_no_gate,
                "meta_size_gate": meta_size_gate,
                "regime": row['regime_name']
            })
            
        audit_df = pd.DataFrame(results_list)
        
        # 5. Análise de Performance
        print("\n--- Auditoria de Estabilidade Temporal (Sharpe Estimado) ---")
        for year in sorted(audit_df['year'].unique()):
            year_data = audit_df[audit_df['year'] == year]
            if len(year_data) < 10: continue
            
            sharpe_mrs = self._calc_sharpe(year_data['mrs_size'] * year_data['fwd_ret'])
            sharpe_meta = self._calc_sharpe(year_data['meta_size_gate'] * year_data['fwd_ret'])
            print(f"Ano {year}: n={len(year_data)} | MRS Sharpe: {sharpe_mrs:.4f} | Meta+Gate Sharpe: {sharpe_meta:.4f}")
            
        print("\n--- Auditoria do Macro Gate ---")
        gate_hits = audit_df[audit_df['meta_size_gate'] < audit_df['meta_size_no_gate']]
        print(f"Ativações do Gate: {len(gate_hits)} ({len(gate_hits)/len(audit_df)*100:.1f}%)")
        
        if len(gate_hits) > 0:
            avoided_loss_series = (gate_hits['meta_size_no_gate'] - gate_hits['meta_size_gate']) * gate_hits['fwd_ret']
            avoided_loss_series = avoided_loss_series.replace([np.inf, -np.inf], np.nan).dropna()
            
            saved = avoided_loss_series[avoided_loss_series < 0].sum()
            cut = avoided_loss_series[avoided_loss_series > 0].sum()
            
            print(f"PnL 'Salvo' pelo Gate (Loss Avoided): {saved:.6f}")
            print(f"PnL 'Sacrificado' pelo Gate (Profit Cut): {cut:.6f}")
            print(f"Net Gate Impact: {saved + cut:.6f}")

    def _calc_sharpe(self, returns):
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        if len(returns) < 5 or returns.std() < 1e-12: return 0.0
        # Sharpe = Mean / Std * sqrt(Annualization)
        # 15min data -> ~28 bars/day * 252 days
        return (returns.mean() / returns.std()) * np.sqrt(28 * 252)

def load_data():
    base_path = "data/storage/"
    # Usando dados de 15min para cobrir mais tempo histórico
    win = pl.read_parquet(base_path + "WIN$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "WIN"})
    wdo = pl.read_parquet(base_path + "WDO$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "WDO"})
    di1 = pl.read_parquet(base_path + "DI1$_15_CLEAN.parquet").select(["time", "close"]).rename({"close": "DI1"})
    return win.join(wdo, on="time").join(di1, on="time").sort("time")

if __name__ == "__main__":
    model_path = "src/models/weights/institutional_meta_v1.joblib"
    if not os.path.exists(model_path):
        print("Erro: Modelo não encontrado. Treine o modelo primeiro.")
    else:
        data = load_data()
        auditor = SystemAuditor(model_path=model_path)
        auditor.run_audit(data, "WIN", ["WDO", "DI1"])
