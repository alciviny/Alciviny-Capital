import unittest
import pandas as pd
import numpy as np
from src.indicators.volatility import KeltnerChannel, KeltnerConfig, add_keltner_channels
from src.processing.processor import DataProcessor

class TestKeltnerChannel(unittest.TestCase):
    def setUp(self):
        # Gerar dados sintéticos para teste
        np.random.seed(42)
        n = 100
        self.df = pd.DataFrame({
            'time': pd.date_range("2024-01-01", periods=n, freq="1h"),
            'open': np.random.randn(n).cumsum() + 100,
            'high': np.random.randn(n).cumsum() + 102,
            'low': np.random.randn(n).cumsum() + 98,
            'close': np.random.randn(n).cumsum() + 100,
            'tick_volume': np.random.randint(100, 1000, n)
        })

    def test_keltner_calculation(self):
        """Verifica se as colunas básicas do Keltner são calculadas."""
        config = KeltnerConfig(ema_period=20, atr_period=10, multiplier=2.0)
        kc = KeltnerChannel(config)
        result = kc.compute(self.df)
        
        self.assertEqual(len(result.middle), len(self.df))
        self.assertTrue(result.upper.iloc[-1] > result.middle.iloc[-1])
        self.assertTrue(result.lower.iloc[-1] < result.middle.iloc[-1])
        
        df_res = result.to_dataframe()
        self.assertIn("keltner_middle", df_res.columns)
        self.assertIn("keltner_upper", df_res.columns)
        self.assertIn("keltner_signal", df_res.columns)

    def test_processor_integration(self):
        """Verifica se o DataProcessor aplica o Keltner corretamente via config."""
        processor = DataProcessor()
        # Forçar uma config que inclua keltner se não estiver carregada (embora já devamos ter atualizado o yaml)
        df_processed = processor.compute_indicators(self.df)
        
        self.assertIn("keltner_middle", df_processed.columns)
        self.assertIn("keltner_upper", df_processed.columns)
        self.assertIn("keltner_signal", df_processed.columns)
        
    def test_squeeze_detection(self):
        """Verifica se a detecção de squeeze funciona (ao menos retorna booleanos)."""
        config = KeltnerConfig(use_squeeze=True)
        kc = KeltnerChannel(config)
        result = kc.compute(self.df)
        self.assertEqual(result.squeeze.dtype, bool)

if __name__ == '__main__':
    unittest.main()
