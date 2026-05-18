import pytest
import numpy as np
import pandas as pd
from datetime import datetime
import polars as pl
from src.engine.router import FractionalKellySizer, StrategyRouter
from src.data.factory import StateVectorFactory

def test_kelly_sizer_caps():
    sizer = FractionalKellySizer(kelly_base=0.5, max_exposure=1.0)
    
    # Em regime BULL (vol_mult = 1.0), prob=0.8 -> size=0.4 (0.8 * 0.5)
    size_bull = sizer.calculate_size(0.8, "BULL")
    assert size_bull == 0.4
    
    # Em regime CRISIS (vol_mult = 3.0), teto = 1/3 = 0.33
    # Mesmo com prob=0.8, o size deve ser capado em 0.33
    size_crisis = sizer.calculate_size(0.8, "CRISIS")
    assert size_crisis == pytest.approx(0.3333, abs=0.01)

def test_strategy_router_activation():
    router = StrategyRouter(thresholds={"BULL": 0.6})
    probs = np.array([0.7, 0.2, 0.1]) # Bull, Bear, Crisis
    labels = ["BULL", "BEAR", "CRISIS"]
    
    activations = router.route(probs, labels)
    assert "BULL" in activations
    assert "BEAR" not in activations
    # O router usa FractionalKellySizer(kelly_base=0.5) por padrão.
    # 0.7 (prob) * 0.5 (kelly) = 0.35
    assert activations["BULL"] == 0.35

def test_state_vector_factory_normalization():
    factory = StateVectorFactory(vol_lookback=5, corr_lookback=5)
    df = pl.DataFrame({
        "WIN": [100, 101, 102, 101, 103, 104, 105, 104, 106, 107],
        "mrs": [0.5] * 10,
        "dcc": [0.8] * 10
    })
    
    # MRS probs devem ser passadas como lista
    mrs_probs = ["mrs"]
    sv = factory.generate(df, "WIN", mrs_probs, "dcc")
    
    assert "vol_z20" in sv.columns
    assert "dcc_z60" in sv.columns
    assert "mrs" in sv.columns
    # MRS prob deve ser mantida original
    assert sv["mrs"][0] == 0.5

def test_state_vector_4d_generation():
    factory = StateVectorFactory(vol_lookback=5, corr_lookback=5)
    # Mock data com OHLCV completo para OFI
    df = pl.DataFrame({
        "time": [datetime(2026, 5, 1, 9, i) for i in range(10)],
        "open": [100] * 10,
        "high": [105] * 10,
        "low": [95] * 10,
        "close": [102] * 10,
        "volume": [1000] * 10,
        "mrs": [0.5] * 10,
        "dcc": [0.8] * 10
    })
    
    mrs_probs = ["mrs"]
    sv = factory.generate(df, "close", mrs_probs, "dcc", use_microstructure=True)
    
    assert "ofi_z20" in sv.columns
    assert "vrp_z20" in sv.columns
    assert len(factory.get_feature_names(mrs_prob_cols=mrs_probs, use_microstructure=True)) == 18
