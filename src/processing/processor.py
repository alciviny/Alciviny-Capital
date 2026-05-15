import pandas as pd
import numpy as np
from typing import List, Optional
import yaml
from src.core.logger import BaseModule
from src.indicators.oscillators import add_ifr_grid
from src.indicators.volatility import add_vwap_bands, add_keltner_channels

class DataProcessor(BaseModule):
    """
    Motor de processamento de dados quantitativos.
    Responsável por limpeza, tratamento de NaNs, normalização e engenharia base de features.
    """
    def __init__(self):
        super().__init__("Processing.DataProcessor")
        self.indicator_config = self._load_indicator_config()

    def _load_indicator_config(self):
        try:
            with open("configs/indicators.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return self._validate_config(config)
        except Exception as e:
            self.logger.error(f"Erro crítico ao carregar config: {e}")
            return {}

    def _validate_config(self, config):
        """Validação defensiva de parâmetros para evitar crashes em runtime."""
        if not config: return {}
        
        valid_config = {}
        for name, params in config.items():
            if not isinstance(params, dict): continue
            
            # Garantir 'enabled' por padrão
            if 'enabled' not in params: params['enabled'] = True
            
            # Validação específica por tipo
            if params.get('type') == 'vwap_atr':
                # Validar multiplicadores
                if not isinstance(params.get('multipliers'), list):
                    self.logger.warning(f"Config '{name}' com multiplicadores inválidos. Usando padrão [1.5, 3.0, 6.0, 9.0]")
                    params['multipliers'] = [1.5, 3.0, 6.0, 9.0]
                
                # Validar período ATR
                if not isinstance(params.get('atr_period'), int) or params['atr_period'] <= 0:
                    params['atr_period'] = 300
                    
            elif name.startswith('ifr'):
                if not isinstance(params.get('period'), int) or params['period'] <= 0:
                    params['period'] = 14
            
            elif params.get('type') == 'keltner':
                # Validar parâmetros do Keltner
                if not isinstance(params.get('ema_period'), int): params['ema_period'] = 20
                if not isinstance(params.get('atr_period'), int): params['atr_period'] = 10
                if not isinstance(params.get('multiplier'), (int, float)): params['multiplier'] = 2.0

            valid_config[name] = params
            
        return valid_config

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """Garante que as colunas obrigatórias existem e têm tipos corretos."""
        required_cols = {'time', 'open', 'high', 'low', 'close', 'tick_volume'}
        # Aceita 'volume' ou 'tick_volume'
        if not required_cols.issubset(set(df.columns)) and 'volume' not in df.columns:
            missing = required_cols - set(df.columns)
            self.logger.error(f"Schema inválido. Colunas faltando: {missing}")
            return False
        return True

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicatas, trata valores ausentes e garante UTC."""
        if df.empty:
            return df

        # 0. Mapeamento Defensivo (Retrocompatibilidade)
        if 'ticks' in df.columns and 'tick_volume' not in df.columns:
            df = df.rename(columns={'ticks': 'tick_volume'})
            self.logger.info("Mapeamento legado 'ticks' -> 'tick_volume' aplicado.")
            
        initial_len = len(df)
        
        # 1. Validar Schema
        if not self.validate_schema(df):
            raise ValueError("DataFrame não contém as colunas necessárias para o pipeline quantitativo.")

        # 2. Garantir que 'time' é datetime e está em UTC (Naive)
        if not pd.api.types.is_datetime64_any_dtype(df['time']):
            unit = 's' if df['time'].max() < 2e10 else 'ms'
            df['time'] = pd.to_datetime(df['time'], unit=unit, utc=True)
        
        # Converter para naive (remove o +00:00) para evitar conflitos de comparação
        if df['time'].dt.tz is not None:
            df['time'] = df['time'].dt.tz_convert('UTC').dt.tz_localize(None)

        # 3. Limpeza de Duplicatas e Ordenação
        df = df.drop_duplicates(subset=['time']).sort_values('time')
        
        # 4. Tratamento de NaNs (Forward Fill -> Drop remanescentes no início)
        df = df.ffill().dropna()
        
        final_len = len(df)
        if initial_len > final_len:
            self.logger.info(f"Limpeza concluída: {initial_len - final_len} registros removidos/corrigidos.")
        
        return df

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica indicadores técnicos baseados na configuração."""
        if df.empty: return df
        
        for ind_name, params in self.indicator_config.items():
            if ind_name.startswith('ifr') and params.get('enabled', True):
                period = params.get('period', 200)
                lines = params.get('grid_lines', [])
                df = add_ifr_grid(df, period=period, lines=lines, col_name=ind_name)
                self.logger.info(f"Indicador {ind_name} ({period}) aplicado.")
            
            elif params.get('type') == 'vwap_atr' and params.get('enabled', True):
                p_type = params.get('period_type', 'D')
                atr_p = params.get('atr_period', 300)
                mults = params.get('multipliers', [1.5, 3.0, 6.0, 9.0])
                df = add_vwap_bands(df, period_type=p_type, atr_period=atr_p, multipliers=mults)
                self.logger.info(f"Indicador {ind_name} ({p_type}) aplicado.")
            
            elif params.get('type') == 'keltner' and params.get('enabled', True):
                df = add_keltner_channels(
                    df, 
                    ema_period=params.get('ema_period', 20),
                    atr_period=params.get('atr_period', 10),
                    multiplier=params.get('multiplier', 2.0),
                    use_squeeze=params.get('use_squeeze', True)
                )
                self.logger.info(f"Indicador {ind_name} aplicado.")
            
        return df

    def normalize(self, df: pd.DataFrame, columns: List[str], method: str = 'zscore', window: Optional[int] = 200) -> pd.DataFrame:
        """
        Normaliza colunas usando janelas móveis (Rolling) otimizadas.
        """
        if df.empty: return df
        
        df_norm = df.copy()
        # Se o dataset for gigante (>20k), limitamos o processamento para performance se window for pequeno
        # Mas mantemos a integridade dos últimos dados.
        
        for col in columns:
            if col not in df.columns: continue
                
            if window:
                roll = df[col].rolling(window=window, min_periods=1)
                if method == 'zscore':
                    # Vetorização pura do Pandas/NumPy
                    df_norm[col] = (df[col] - roll.mean()) / (roll.std() + 1e-9)
                elif method == 'minmax':
                    df_norm[col] = (df[col] - roll.min()) / (roll.max() - roll.min() + 1e-9)
            else:
                if method == 'zscore':
                    df_norm[col] = (df[col] - df[col].mean()) / (df[col].std() + 1e-9)
                elif method == 'minmax':
                    df_norm[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min() + 1e-9)
        
        return df_norm

    def add_basic_returns(self, df: pd.DataFrame, col: str = 'close') -> pd.DataFrame:
        """Calcula retornos logarítmicos (essencial para modelos estatísticos)."""
        df['returns'] = np.log(df[col] / df[col].shift(1))
        return df.dropna()

    def validate_integrity(self, df: pd.DataFrame) -> bool:
        """
        Verifica a saúde dos dados:
        1. Gaps temporais anômalos.
        2. Presença de preços negativos ou zerados.
        3. Detecção de Outliers (Spikes de preço irreais).
        """
        if df.empty: return False

        # 1. Verificar Preços Inválidos
        cols_to_check = ['open', 'high', 'low', 'close']
        if (df[cols_to_check] <= 0).any().any():
            self.logger.error("Detectados preços negativos ou zerados nos dados!")
            return False

        # 2. Verificar Gaps Temporais
        time_diffs = df['time'].diff().dt.total_seconds().dropna()
        median_diff = time_diffs.median()
        gaps = time_diffs[time_diffs > median_diff * 3] # Mais de 3 períodos de gap
        if not gaps.empty:
            self.logger.warning(f"Detectados {len(gaps)} gaps temporais significativos.")

        # 3. Detecção de Outliers (Z-Score > 10 - Spikes absurdos)
        for col in ['close']:
            returns = df[col].pct_change().dropna()
            z_scores = (returns - returns.mean()) / (returns.std() + 1e-9)
            outliers = z_scores[z_scores.abs() > 10]
            if not outliers.empty:
                self.logger.critical(f"ALERTA: {len(outliers)} spikes de preço suspeitos detectados em {col}!")
                return False

        return True
