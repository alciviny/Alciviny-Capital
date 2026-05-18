import polars as pl
from typing import Optional
from datetime import date
from src.data.b3_pos import B3PositionManager

class MacroRegimeGate:
    """
    Portão Macro que ajusta a exposição do Kelly baseado no Crowding de mercado.
    Implementa a lógica de redução de risco institucional D+1.
    """
    def __init__(self, pos_manager: Optional[B3PositionManager] = None):
        self.pos_manager = pos_manager or B3PositionManager()

    def apply(self, kelly_base: float, target_date: date, current_vrp: float = 0.0) -> float:
        """
        Aplica a hierarquia de redução de Kelly.
        |z| < 1.5              -> 1.0x
        |z| [1.5, 2.0]        -> 0.7x
        |z| > 2.0              -> 0.4x
        |z| > 2.0 + VRP < 0    -> 0.2x (Risco Máximo)
        """
        pos_signal = self.pos_manager.get_position_for_date(target_date)
        
        if not pos_signal:
            return kelly_base # Sem dado B3, mantém base por conservadorismo ou padrão
            
        z_raw = pos_signal.get("positioning_z")
        z = abs(z_raw) if z_raw is not None else 0.0
        multiplier = 1.0
        
        if z > 2.0:
            # Caso Extremo
            multiplier = 0.4
            # Agravante: Volatilidade em expansão (VRP < 0)
            if current_vrp < 0:
                multiplier = 0.2
        elif z > 1.5:
            # Alerta
            multiplier = 0.7
            
        return kelly_base * multiplier
