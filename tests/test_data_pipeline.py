import unittest
import pandas as pd
from pathlib import Path
from src.data.manager import DataManager
from src.data.store import DataStore
import MetaTrader5 as mt5

class TestDataPipeline(unittest.TestCase):
    """
    Suíte de Testes Profissional para o Pipeline de Dados do AlcivinyEdger.
    Valida: Conexão, Sincronização, Integridade e Persistência.
    """
    
    @classmethod
    def setUpClass(cls):
        cls.manager = DataManager()
        cls.test_symbol = "WIN$" # Símbolo comum em MT5 brasileiro
        cls.tf = mt5.TIMEFRAME_M1

    def test_mt5_connection(self):
        """Valida se o conector consegue inicializar o terminal."""
        connected = self.manager.connector.connect()
        self.assertTrue(connected, "Falha crítica: O MetaTrader 5 não está aberto ou configurado.")
        self.manager.connector.disconnect()

    def test_incremental_flow(self):
        """Testa o ciclo completo: Download -> Salvar -> Atualizar."""
        # 1. Limpar cache de teste se existir
        store = DataStore()
        path = store._get_file_path(self.test_symbol, self.tf)
        if path.exists(): path.unlink()

        # 2. Primeiro Download (Base)
        df1 = self.manager.update_and_fetch(self.test_symbol, self.tf, lookback_if_empty=100)
        self.assertIsNotNone(df1, "Falha ao baixar dados iniciais.")
        self.assertEqual(len(df1), 100, "Quantidade de dados inicial incorreta.")
        
        # 3. Verificar se salvou no disco
        self.assertTrue(path.exists(), "O sistema não persistiu os dados em Parquet.")

        # 4. Segundo Download (Incremental)
        # Simulamos uma atualização. Como o mercado pode estar parado, 
        # esperamos que ele ao menos carregue o que já existe.
        df2 = self.manager.update_and_fetch(self.test_symbol, self.tf)
        self.assertIsNotNone(df2)
        self.assertGreaterEqual(len(df2), len(df1), "O download incremental reduziu a base de dados!")

    def test_data_integrity(self):
        """Valida se o processador removeu duplicatas e aplicou UTC."""
        df = self.manager.update_and_fetch(self.test_symbol, self.tf, lookback_if_empty=50)
        
        # Verificar duplicatas de tempo
        has_duplicates = df['time'].duplicated().any()
        self.assertFalse(has_duplicates, "O pipeline permitiu duplicatas temporais!")
        
        # Verificar Timezone
        self.assertIsNotNone(df['time'].dt.tz, "Os dados não possuem informação de Timezone (UTC).")
        self.assertEqual(str(df['time'].dt.tz), 'UTC', "O Timezone não é UTC.")

if __name__ == '__main__':
    unittest.main()
