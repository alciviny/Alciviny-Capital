import numpy as np
from abc import ABC, abstractmethod

class PositionSizer(ABC):
    """
    Interface para algoritmos de dimensionamento de posição.
    """
    @abstractmethod
    def calculate_size(self, signal: float, capital: float, risk_per_trade: float) -> float:
        pass

class FixedFractionalSizer(PositionSizer):
    """
    Dimensionamento baseado em uma fração fixa do capital.
    """
    def calculate_size(self, signal: float, capital: float, risk_per_trade: float) -> float:
        return (capital * risk_per_trade) / abs(signal) if signal != 0 else 0.0

class KellySizer(PositionSizer):
    """
    Dimensionamento baseado no Critério de Kelly.
    """
    def __init__(self, win_rate: float, win_loss_ratio: float, fraction: float = 0.5):
        self.win_rate = win_rate
        self.win_loss_ratio = win_loss_ratio
        self.fraction = fraction # Half-Kelly por padrão para segurança

    def calculate_size(self, signal: float, capital: float, risk_per_trade: float = None) -> float:
        # F = W - (1-W)/R
        # Se R <= 0, Kelly não faz sentido
        if self.win_loss_ratio <= 0: return 0.0
        
        kelly_f = self.win_rate - ((1 - self.win_rate) / self.win_loss_ratio)
        # Aplicamos a fração (ex: Half-Kelly) e garantimos que não seja negativo
        allocation = max(0.0, kelly_f * self.fraction)
        return capital * min(allocation, 1.0) # Cap em 100% do capital
