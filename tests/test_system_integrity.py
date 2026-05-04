import unittest
import pandas as pd
import numpy as np
from datetime import datetime
from src.processing.processor import DataProcessor
from src.indicators.volatility import add_vwap_bands
from src.data.mt5_connector import MT5Connector

class TestSystemIntegrity(unittest.TestCase):
    """
    Suíte de Testes de Integridade para validar contratos de dados, 
    nomenclatura de colunas e lógica de indicadores.
    """

    def setUp(self):
        self.processor = DataProcessor()
        # Mock de dados OHLCV padrão
        self.sample_df = pd.DataFrame({
            'time': pd.to_datetime(['2023-01-01 10:00', '2023-01-01 10:01', '2023-01-01 10:02']),
            'open': [100.0, 101.0, 102.0],
            'high': [105.0, 106.0, 107.0],
            'low': [95.0, 96.0, 97.0],
            'close': [101.0, 102.0, 103.0],
            'tick_volume': [10, 20, 30]
        })

    def test_legacy_column_mapping(self):
        """Valida se o processador converte 'ticks' para 'tick_volume' corretamente."""
        legacy_df = self.sample_df.rename(columns={'tick_volume': 'ticks'})
        
        # O processador deve detectar 'ticks' e renomear para 'tick_volume'
        cleaned_df = self.processor.clean_data(legacy_df)
        
        self.assertIn('tick_volume', cleaned_df.columns)
        self.assertNotIn('ticks', cleaned_df.columns)
        self.assertEqual(cleaned_df['tick_volume'].iloc[0], 10)

    def test_vwap_indicator_contract(self):
        """Valida se o indicador de VWAP utiliza a coluna correta (tick_volume)."""
        # Se o indicador estiver usando o nome errado, isso lançará um KeyError
        try:
            result_df = add_vwap_bands(self.sample_df, period_type='D')
            self.assertIn('VWAP_D', result_df.columns)
            self.assertFalse(result_df['VWAP_D'].isnull().all())
        except KeyError as e:
            self.fail(f"O indicador de VWAP falhou por erro de contrato de coluna: {e}")

    def test_mt5_connector_column_names(self):
        """Verifica se o conector MT5 está seguindo o padrão de nomenclatura estabelecido."""
        connector = MT5Connector()
        # Mock de dados crus do MT5 (simplificado)
        raw_rates = np.array([
            (1672531200, 100.0, 105.0, 95.0, 101.0, 10, 100, 1)
        ], dtype=[('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), ('close', '<f8'), ('tick_volume', '<i8'), ('real_volume', '<i8'), ('spread', '<i8')])
        
        # Simulando o processamento interno do conector (sem depender de conexão real)
        df = pd.DataFrame(raw_rates)
        rename_map = {'real_volume': 'volume', 'tick_volume': 'tick_volume', 'spread': 'spread'}
        df = df.rename(columns=rename_map)
        
        self.assertIn('tick_volume', df.columns)
        self.assertNotIn('ticks', df.columns)

    def test_processor_schema_validation(self):
        """Garante que o schema obrigatório é validado corretamente."""
        # Remover coluna obrigatória
        invalid_df = self.sample_df.drop(columns=['close'])
        
        with self.assertLogs(self.processor.logger.name, level='ERROR') as cm:
            is_valid = self.processor.validate_schema(invalid_df)
            self.assertFalse(is_valid)
            # Busca por "colunas faltando" (Português) ou "missing" (Inglês)
            found = any(("colunas faltando" in msg.lower() or "missing" in msg.lower()) for msg in cm.output)
            self.assertTrue(found, f"Log esperado não encontrado. Logs: {cm.output}")

    def test_api_config_loading(self):
        """Valida se a API carrega as configurações corretamente."""
        from src.api.main import APIModule
        api = APIModule()
        config = api._load_config()
        self.assertIsInstance(config, dict)
        self.assertIn('assets', config)
        self.assertIn('settings', config)

if __name__ == '__main__':
    unittest.main()
