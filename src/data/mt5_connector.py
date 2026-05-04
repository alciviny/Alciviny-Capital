import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import pytz
from typing import Optional
from src.core.logger import BaseModule

class MT5Connector(BaseModule):
    """
    Responsável pela conexão e download de dados do MetaTrader 5.
    Isola a dependência do MT5 do restante do sistema.
    """
    def __init__(self):
        super().__init__("Data.MT5Connector")
        
    def connect(self) -> bool:
        if not mt5.initialize():
            self.logger.error(f"Falha ao inicializar MT5: {mt5.last_error()}")
            return False
        self.logger.info("Conectado ao MetaTrader 5 com sucesso.")
        return True

    def _get_mt5_timeframe(self, tf: int) -> int:
        """Converte minutos (do YAML) para constantes do MT5."""
        mapping = {
            1: mt5.TIMEFRAME_M1,
            2: mt5.TIMEFRAME_M2,
            3: mt5.TIMEFRAME_M3,
            4: mt5.TIMEFRAME_M4,
            5: mt5.TIMEFRAME_M5,
            10: mt5.TIMEFRAME_M10,
            12: mt5.TIMEFRAME_M12,
            15: mt5.TIMEFRAME_M15,
            20: mt5.TIMEFRAME_M20,
            30: mt5.TIMEFRAME_M30,
            60: mt5.TIMEFRAME_H1,
            120: mt5.TIMEFRAME_H2,
            180: mt5.TIMEFRAME_H3,
            240: mt5.TIMEFRAME_H4,
            360: mt5.TIMEFRAME_H6,
            480: mt5.TIMEFRAME_H8,
            720: mt5.TIMEFRAME_H12,
            1440: mt5.TIMEFRAME_D1,
            10080: mt5.TIMEFRAME_W1,
            43200: mt5.TIMEFRAME_MN1
        }
        return mapping.get(tf, mt5.TIMEFRAME_M1)

    def get_historical_data(self, symbol: str, timeframe: int, start_pos: int, count: int) -> Optional[pd.DataFrame]:
        """Baixa dados históricos e retorna um DataFrame formatado."""
        mt5_tf = self._get_mt5_timeframe(timeframe)
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, start_pos, count)
        if rates is None:
            self.logger.warning(f"Nenhum dado encontrado para {symbol}.")
            return None
            
        df = pd.DataFrame(rates)
        
        # 1. Converter timestamp para datetime UTC
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # 2. Renomear colunas para padrão profissional (lowercase)
        rename_map = {
            'real_volume': 'volume',
            'tick_volume': 'tick_volume', # Mantendo padrão MT5 para consistência no pipeline
            'spread': 'spread'
        }
        df = df.rename(columns=rename_map)
        
        self.logger.info(f"Baixados {len(df)} registros para {symbol} (TF: {timeframe}).")
        return df

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Obtém as propriedades técnicas do ativo (margem, pontos, etc)."""
        info = mt5.symbol_info(symbol)
        if info is None:
            self.logger.error(f"Ativo {symbol} não encontrado no Market Watch.")
            return None
            
        return {
            "symbol": info.name,
            "point": info.point,
            "tick_size": info.trade_tick_size,
            "tick_value": info.trade_tick_value,
            "contract_size": info.trade_contract_size,
            "currency": info.currency_base,
            "margin_initial": info.margin_initial,
            "digits": info.digits
        }

    def get_historical_data_range(self, symbol: str, timeframe: int, date_from: datetime, date_to: datetime) -> Optional[pd.DataFrame]:
        """Baixa dados entre duas datas específicas."""
        mt5_tf = self._get_mt5_timeframe(timeframe)
        rates = mt5.copy_rates_range(symbol, mt5_tf, date_from, date_to)
        if rates is None or len(rates) == 0:
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        rename_map = {'real_volume': 'volume', 'tick_volume': 'tick_volume'}
        df = df.rename(columns=rename_map)
        
        return df

    def disconnect(self):
        mt5.shutdown()
        self.logger.info("Conexão com MT5 encerrada.")
