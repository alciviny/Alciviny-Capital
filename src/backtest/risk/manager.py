from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class RiskParameters:
    stop_loss_pct: float
    take_profit_pct: float
    trailing_stop: bool = False

class RiskManager:
    """
    Controla a execução de stops e regras de saída de risco.
    """
    def __init__(self, params: RiskParameters, sizer: Any = None):
        self.params = params
        self.sizer = sizer

    def check_exit(self, entry_price: float, current_price: float, position_side: int) -> Optional[str]:
        """
        Verifica se alguma regra de risco foi atingida.
        """
        pnl_pct = (current_price / entry_price - 1) * position_side
        
        if pnl_pct <= -self.params.stop_loss_pct:
            return "STOP_LOSS"
        if pnl_pct >= self.params.take_profit_pct:
            return "TAKE_PROFIT"
            
        return None
