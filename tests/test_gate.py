import pytest
import numpy as np
import polars as pl
from datetime import date, timedelta
from src.data.b3_pos import B3PositionManager
from src.engine.gate import MacroRegimeGate
from src.engine.router import StrategyRouter, FractionalKellySizer

def test_b3_position_manager_logic(tmp_path):
    storage = tmp_path / "test_pos.parquet"
    # Criar dados mock (100 dias)
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(100)]
    df = pl.DataFrame({
        "data": dates,
        "investidor": ["INVESTIDOR NAO RESIDENTE"] * 100,
        "net_pos": np.linspace(1000, 5000, 100) # Tendência de alta
    })
    
    # Adicionar as colunas calculadas manualmente para simular o processamento
    df = df.with_columns([
        ((pl.col("net_pos") - pl.col("net_pos").rolling_mean(60)) / (pl.col("net_pos").rolling_std(60) + 1e-9)).alias("positioning_z")
    ])
    df.write_parquet(storage)
    
    manager = B3PositionManager(storage_path=str(storage))
    # Para o dia 100, deve pegar o dado do dia 99 (D+1)
    pos = manager.get_position_for_date(date(2026, 1, 1) + timedelta(days=99))
    assert pos is not None
    assert pos["data"] < date(2026, 1, 1) + timedelta(days=99)

def test_macro_gate_hierarchy():
    class MockManager:
        def __init__(self, z): self.z = z
        def get_position_for_date(self, dt): return {"positioning_z": self.z}
    
    # Teste Neutro |z| < 1.5
    gate = MacroRegimeGate(pos_manager=MockManager(1.0))
    assert gate.apply(0.5, date.today()) == 0.5
    
    # Teste Alerta |z| = 1.7
    gate = MacroRegimeGate(pos_manager=MockManager(1.7))
    assert gate.apply(0.5, date.today()) == 0.5 * 0.7
    
    # Teste Extremo |z| = 2.5
    gate = MacroRegimeGate(pos_manager=MockManager(2.5))
    assert gate.apply(0.5, date.today()) == 0.5 * 0.4
    
    # Teste Extremo com VRP Negativo
    assert gate.apply(0.5, date.today(), current_vrp=-0.1) == 0.5 * 0.2

def test_router_integration_with_gate():
    class MockManager:
        def get_position_for_date(self, dt): return {"positioning_z": 2.5} # Extremo
        
    sizer = FractionalKellySizer(kelly_base=0.5, max_exposure=1.0)
    gate = MacroRegimeGate(pos_manager=MockManager())
    router = StrategyRouter(thresholds={"BULL": 0.5}, sizer=sizer, gate=gate)
    
    # BULL prob = 0.8
    # Sem gate: size = 0.8 * 0.5 = 0.4
    # Com gate (|z|>2.5): kelly_base = 0.5 * 0.4 = 0.2. Size = 0.8 * 0.2 = 0.16
    activations = router.route(np.array([0.8]), ["BULL"], target_date=date.today())
    
    assert activations["BULL"] == pytest.approx(0.16)
