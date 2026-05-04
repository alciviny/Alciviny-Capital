import pandas as pd
from datetime import datetime, timezone
import yaml
from typing import Optional, List, Dict
from src.core.logger import BaseModule
from src.data.mt5_connector import MT5Connector
from src.processing.processor import DataProcessor
from src.data.store import DataStore

class DataManager(BaseModule):
    """
    Orquestrador de Dados Avançado.
    Gerencia: Cache Local (Store) -> Atualização Incremental -> Processamento.
    """
    def __init__(self, connector: Optional[MT5Connector] = None, 
                 processor: Optional[DataProcessor] = None,
                 store: Optional[DataStore] = None):
        super().__init__("Data.DataManager")
        self.connector = connector or MT5Connector()
        self.processor = processor or DataProcessor()
        self.store = store or DataStore()

    def update_and_fetch(self, symbol: str, timeframe: int, lookback_if_empty: int = 5000) -> Optional[pd.DataFrame]:
        """
        Garante que os dados em disco estejam atualizados e retorna o histórico completo.
        """
        try:
            if not self.connector.connect():
                return self.store.load(symbol, timeframe) # Tenta carregar offline

            last_ts = self.store.get_last_timestamp(symbol, timeframe)
            
            if last_ts is None:
                # 1. Caso base: Baixar histórico inicial
                self.logger.info(f"Iniciando download inicial para {symbol}...")
                new_data = self.connector.get_historical_data(symbol, timeframe, 0, lookback_if_empty)
            else:
                # 2. Atualização Incremental
                self.logger.info(f"Atualizando {symbol} desde {last_ts}...")
                
                # Garantir que ambas as datas sejam naive para evitar erro de comparação
                date_from = last_ts.to_pydatetime()
                if date_from.tzinfo is not None:
                    date_from = date_from.replace(tzinfo=None)
                
                date_to = datetime.now(timezone.utc).replace(tzinfo=None)
                
                new_data = self.connector.get_historical_data_range(symbol, timeframe, date_from, date_to)

            # 3. Processar e Unificar
            existing_data = self.store.load(symbol, timeframe)
            
            if new_data is not None:
                combined = pd.concat([existing_data, new_data]) if existing_data is not None else new_data
                processed = self.processor.clean_data(combined)
                processed = self.processor.compute_indicators(processed)
                
                # 4. Salvar progresso
                self.store.save(processed, symbol, timeframe)
                return processed
            
            return existing_data

        except Exception as e:
            self.logger.error(f"Erro no pipeline incremental: {str(e)}")
            return self.store.load(symbol, timeframe)
        finally:
            self.connector.disconnect()

    def sync_from_config(self, config_path: str = "configs/universe.yaml"):
        """Sincroniza todo o universo de ativos baseado em um arquivo YAML."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            for asset in config['assets']:
                symbol = asset['symbol']
                timeframes = asset['timeframes']
                lookback = config['settings'].get('initial_lookback', 5000)
                
                self.logger.info(f"Sincronizando Ativo: {symbol}")
                for tf in timeframes:
                    self.update_and_fetch(symbol, tf, lookback_if_empty=lookback)
                    
            self.logger.info("Sincronização do universo concluída.")
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar via config: {str(e)}")
