import pytest
import polars as pl
import numpy as np
from datetime import datetime, timedelta
from src.indicators.microstructure import OFIEngine, OFISource

def generate_mock_data(n=100, source="ohlcv"):
    base_time = datetime(2026, 5, 1, 9, 0)
    data = {
        "time": [base_time + timedelta(minutes=i) for i in range(n)],
        "open": np.linspace(100, 110, n),
        "high": np.linspace(102, 112, n),
        "low": np.linspace(98, 108, n),
        "close": np.linspace(101, 111, n),
        "volume": np.random.randint(100, 1000, n)
    }
    
    if source == "tick":
        data["bid_volume"] = np.random.randint(50, 500, n)
        data["ask_volume"] = np.random.randint(50, 500, n)
    elif source == "partial":
        data["delta_volume"] = np.random.randint(-100, 100, n)
        
    return pl.DataFrame(data)

def test_source_detection_tick():
    df = generate_mock_data(source="tick")
    engine = OFIEngine(df)
    assert engine.source == OFISource.TICK

def test_source_detection_partial():
    df = generate_mock_data(source="partial")
    engine = OFIEngine(df)
    assert engine.source == OFISource.PARTIAL

def test_source_detection_ohlcv():
    df = generate_mock_data(source="ohlcv")
    engine = OFIEngine(df)
    assert engine.source == OFISource.OHLCV

def test_ofi_calculation_range():
    df = generate_mock_data(n=50, source="ohlcv")
    engine = OFIEngine(df)
    res = engine.calculate_ofi()
    
    # OFI deve estar entre -1 e 1
    assert res["ofi"].min() >= -1.0
    assert res["ofi"].max() <= 1.0

def test_cumulative_delta_reset():
    # Criar dados de dois dias
    n = 20
    base_time_d1 = datetime(2026, 5, 1, 9, 0)
    base_time_d2 = datetime(2026, 5, 2, 9, 0)
    
    times = [base_time_d1 + timedelta(minutes=i) for i in range(n)] + \
            [base_time_d2 + timedelta(minutes=i) for i in range(n)]
    
    df = pl.DataFrame({
        "time": times,
        "open": np.random.rand(2*n),
        "high": np.random.rand(2*n) + 1,
        "low": np.random.rand(2*n) - 1,
        "close": np.random.rand(2*n),
        "volume": np.random.randint(100, 1000, 2*n)
    })
    
    engine = OFIEngine(df)
    res = engine.calculate_ofi()
    
    # O cumulative delta no início do segundo dia deve ser menor ou igual ao valor absoluto do primeiro OFI do dia
    # (Pois reseta para o valor daquele candle)
    d2_start_idx = n
    assert res["cum_delta_ofi"][d2_start_idx] == res["ofi"][d2_start_idx]

def test_vrp_calculation():
    df = generate_mock_data(n=400)
    engine = OFIEngine(df)
    vrp_series = df.select(engine.calculate_vrp(window_realized=5, window_historic=20)).to_series()
    
    assert len(vrp_series) == 400
    assert vrp_series.null_count() > 0 

def test_predictiveness_validation():
    df = generate_mock_data(n=100)
    engine = OFIEngine(df)
    results = engine.validate_ofi_predictiveness(forward_windows=[3, 5])
    
    assert "fwd_ret_3" in results
    assert "fwd_ret_5" in results
    assert isinstance(results["fwd_ret_3"], float)
