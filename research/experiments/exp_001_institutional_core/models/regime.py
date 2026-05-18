import numpy as np
import pandas as pd
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from typing import Optional, Dict

class MarkovRegimeDetector:
    """
    Detector Industrial de Regimes Ocultos.
    Utiliza Log-Returns padronizados e mapeamento semântico de estados.
    """
    def __init__(self, k_regimes: int = 3):
        self.k_regimes = k_regimes
        self.model = None
        self.results = None
        self.regime_map = {} 
        self.expected_durations = None
        self.confidence_metrics = {}

    def detect(self, prices: pd.Series) -> pd.DataFrame:
        """
        Executa a regressão de Markov com normalização e rotulagem automática.
        """
        # 1. Transformação para Log-Returns (Elimina viés de escala de preço)
        returns = np.log(prices / prices.shift(1)).dropna()
        
        # 2. Padronização Z-Score (Estabilidade Numérica MLE)
        mu, sigma = returns.mean(), returns.std()
        scaled = (returns - mu) / sigma
        
        # 3. Definição do Modelo com Switching Mean e Switching Variance
        self.model = MarkovRegression(
            scaled, 
            k_regimes=self.k_regimes, 
            trend='c', 
            switching_trend=True, 
            switching_variance=True
        )
        
        # 4. Fit Robusto com Múltiplas Partidas (Evita ótimos locais)
        self.results = self.model.fit(search_reps=30, em_iter=20)
        
        if not self.results.mle_retvals['converged']:
            raise RuntimeError("Markov Model did not converge. Verifique a qualidade dos dados.")

        # 5. Extração de Probabilidades Suavizadas
        probs = self.results.smoothed_marginal_probabilities.copy()
        probs.columns = [f"regime_{i}_prob" for i in range(self.k_regimes)]
        
        # Hard Classification temporária para mapeamento
        dominant = np.argmax(probs.values, axis=1)
        
        # 6. MAPEAMENTO SEMÂNTICO DINÂMICO
        # O label 0 do statsmodels não é necessariamente o mesmo em cada rodada.
        # Precisamos classificar por características estatísticas.
        regime_stats = []
        for i in range(self.k_regimes):
            mask = dominant == i
            if not mask.any(): continue # Regime não detectado no período
            
            regime_stats.append({
                'id': i,
                'mean': returns[mask].mean(),
                'vol': returns[mask].std()
            })
            
        # Classificação baseada em Volatilidade e Média
        # Ordem de Volatilidade: Crise é a maior vol.
        # Ordem de Média: Bull é a maior média, Bear a menor.
        regime_stats.sort(key=lambda x: x['vol'], reverse=True)
        crisis_id = regime_stats[0]['id'] # Maior volatilidade = CRISE
        
        others = regime_stats[1:]
        others.sort(key=lambda x: x['mean'], reverse=True)
        bull_id = others[0]['id']
        bear_id = others[1]['id'] if len(others) > 1 else -1
        
        self.regime_map = {bull_id: "BULL", bear_id: "BEAR", crisis_id: "CRISIS"}
        
        # 7. Finalização do DataFrame de Saída
        probs['dominant_regime_id'] = dominant
        probs['regime_name'] = [self.regime_map.get(d, "UNKNOWN") for d in dominant]
        
        # 8. Persistência de Regime
        self.expected_durations = self.results.expected_durations
        
        # 9. Autodiagnóstico de Confiança
        self._calculate_confidence(probs)
        
        return probs

    def _calculate_confidence(self, probs: pd.DataFrame):
        """Calcula métricas de qualidade do ajuste (RCM e Persistência)."""
        # 1. RCM (Regime Classification Measure) - Adaptado para K regimes
        # Mede o quão 'decidido' o modelo está. 0 = Perfeito, 100 = Ruído total.
        p = probs[[f"regime_{i}_prob" for i in range(self.k_regimes)]].values
        n = len(p)
        
        # Para K=3, usamos a métrica de pureza de classificação
        # RCM = 100 * (1 - (K/(K-1)) * sum( (p - 1/K)^2 ) / N ) - Versão simplificada
        # Aqui usamos uma abordagem direta: quão longe estamos da incerteza (1/K)
        uncertainty = np.mean([np.prod(row) for row in p]) * (self.k_regimes**self.k_regimes)
        rcm_score = np.clip(uncertainty * 100, 0, 100)
        
        # 2. Persistência Média (Diag da Matriz de Transição)
        trans_mat = self.results.regime_transition
        # O statsmodels retorna (K, K, 1) ou (K, K), pegamos a diagonal
        if trans_mat.ndim == 3: trans_mat = trans_mat[:, :, 0]
        avg_persistence = np.mean(np.diag(trans_mat))
        
        self.confidence_metrics = {
            "rcm_score": rcm_score, # < 30 é excelente
            "avg_persistence": avg_persistence, # > 0.90 é excelente
            "aic": self.results.aic,
            "bic": self.results.bic,
            "converged": self.results.mle_retvals['converged']
        }

    def get_confidence_report(self) -> str:
        """Gera um relatório textual sobre a confiabilidade dos sinais."""
        m = self.confidence_metrics
        if not m: return "Modelo ainda não executado."
        
        status = "🟢 ALTA" if m['rcm_score'] < 35 and m['avg_persistence'] > 0.85 else "🟡 MÉDIA"
        if m['rcm_score'] > 60: status = "🔴 BAIXA (RUÍDO)"
        
        report = f"""
--- RELATÓRIO DE AUDITORIA DE REGIMES ---
Confiança do Modelo: {status}
-----------------------------------------
RCM Score: {m['rcm_score']:.2f} (0=Perfeito, 100=Inútil)
Persistência Média: {m['avg_persistence']*100:.1f}%
Convergência MLE: {'Sim' if m['converged'] else 'Não'}
AIC / BIC: {m['aic']:.1f} / {m['bic']:.1f}
-----------------------------------------
"""
        return report

    def get_regime_summary(self) -> Dict:
        """Retorna as estatísticas e durações esperadas dos regimes."""
        if self.results is None: return {}
        
        durations = self.results.expected_durations
        summary = {}
        for i, name in self.regime_map.items():
            if i == -1: continue
            summary[name] = {
                "id": i,
                "expected_duration": durations[i],
                "params": self.results.params.filter(like=f"[{i}]").to_dict()
            }
        return summary
