import numpy as np
from typing import Dict, List, Optional
from datetime import date
from src.engine.gate import MacroRegimeGate

class FractionalKellySizer:
    """
    Sizer Institucional com teto de risco dinâmico.
    Aplica a lógica: size = min(Prob * Kelly_Base, max_exposure / vol_multiplier)
    """
    
    def __init__(self, 
                 kelly_base: float = 0.5, 
                 max_exposure: float = 1.0,
                 vol_multipliers: Optional[Dict[str, float]] = None):
        self.kelly_base = kelly_base
        self.max_exposure = max_exposure
        # Multiplicadores de volatilidade por regime (default agressivo)
        self.vol_multipliers = vol_multipliers or {
            "BULL": 1.0,
            "BEAR": 1.5,
            "CRISIS": 3.0,
            "UNKNOWN": 2.0
        }

    def calculate_size(self, 
                       prob_regime: float, 
                       regime_name: str) -> float:
        """
        Calcula o tamanho da posição ponderado pela probabilidade e regime de vol.
        """
        vol_multiplier = self.vol_multipliers.get(regime_name, 2.0)
        
        # 1. Tamanho base via Kelly Fracionado
        target_size = prob_regime * self.kelly_base
        
        # 2. Teto de risco baseado na volatilidade do regime
        risk_cap = self.max_exposure / vol_multiplier
        
        return float(np.clip(target_size, 0, risk_cap))

class StrategyRouter:
    """
    Orquestrador de ativação de subsistemas baseado em probabilidades de regime.
    """
    
    def __init__(self, 
                 thresholds: Optional[Dict[str, float]] = None,
                 sizer: Optional[FractionalKellySizer] = None,
                 gate: Optional[MacroRegimeGate] = None):
        # Thresholds mínimos de probabilidade para ativar uma estratégia
        self.thresholds = thresholds or {
            "BULL": 0.4,
            "BEAR": 0.4,
            "CRISIS": 0.3 # Regime de crise ativa proteção/vol trading com menor prob
        }
        self.sizer = sizer or FractionalKellySizer()
        self.gate = gate or MacroRegimeGate()

    def route(self, 
              prob_vector: np.ndarray, 
              regime_labels: List[str],
              target_date: Optional[date] = None,
              current_vrp: float = 0.0) -> Dict[str, float]:
        """
        Retorna as estratégias ativas e seus tamanhos de posição finais.
        """
        activations = {}
        
        # 1. Ajustar Kelly Base via Macro Gate se houver data disponível
        active_kelly_base = self.sizer.kelly_base
        if target_date and self.gate:
            active_kelly_base = self.gate.apply(active_kelly_base, target_date, current_vrp)
            
        # Armazenar base original para restaurar se necessário
        original_base = self.sizer.kelly_base
        self.sizer.kelly_base = active_kelly_base
        
        try:
            for i, label in enumerate(regime_labels):
                prob = prob_vector[i]
                if prob >= self.thresholds.get(label, 0.5):
                    # 2. Calcular tamanho da posição final via Sizer
                    size = self.sizer.calculate_size(prob, label)
                    activations[label] = size
        finally:
            # Restaurar kelly base original
            self.sizer.kelly_base = original_base
                
        return activations
