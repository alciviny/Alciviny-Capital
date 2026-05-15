class CostModel:
    """
    Calcula custos de transao e slippage.
    """
    def __init__(self, commission_per_trade: float = 0.0, slippage_pct: float = 0.0):
        self.commission = commission_per_trade
        self.slippage = slippage_pct

    def apply_costs(self, price: float, size: float, side: int) -> float:
        """
        Ajusta o preo de execuo baseado nos custos.
        side: 1 para compra, -1 para venda.
        """
        slippage_impact = price * self.slippage * side
        return price + slippage_impact
