import pandas as pd
from pathlib import Path
from typing import Optional
from src.core.logger import BaseModule

class DataStore(BaseModule):
    """
    Responsável pela persistência local de dados históricos.
    Usa o formato Parquet para alta performance e compressão.
    """
    def __init__(self, storage_path: str = "data/storage"):
        super().__init__("Data.DataStore")
        self.storage_root = Path(storage_path)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, symbol: str, timeframe: int) -> Path:
        return self.storage_root / f"{symbol}_{timeframe}.parquet"

    def save(self, df: pd.DataFrame, symbol: str, timeframe: int):
        """Salva ou sobrescreve os dados de um ativo."""
        path = self._get_file_path(symbol, timeframe)
        df.to_parquet(path, index=False)
        self.logger.info(f"Dados salvos: {path} ({len(df)} registros)")

    def load(self, symbol: str, timeframe: int) -> Optional[pd.DataFrame]:
        """Carrega dados do disco usando motor PyArrow (mais rápido)."""
        path = self._get_file_path(symbol, timeframe)
        if path.exists():
            # Uso de engine='pyarrow' para carregar multithreaded
            df = pd.read_parquet(path, engine='pyarrow')
            
            if df['time'].dt.tz is None:
                df['time'] = df['time'].dt.tz_localize('UTC')
            
            self.logger.info(f"Dados carregados via PyArrow: {path}")
            return df
        return None

    def get_last_timestamp(self, symbol: str, timeframe: int) -> Optional[pd.Timestamp]:
        """Retorna a data do último candle salvo para atualização incremental."""
        df = self.load(symbol, timeframe)
        if df is not None and not df.empty:
            return df['time'].max()
        return None
