import polars as pl
import os
from datetime import datetime, date
from typing import Optional

class B3PositionManager:
    """
    Gerencia dados de posicionamento institucional (D+1) da B3.
    Focado na participação de investidores estrangeiros em derivativos.
    """
    def __init__(self, storage_path: str = "data/storage/b3_positions.parquet"):
        self.storage_path = storage_path
        self.df: Optional[pl.DataFrame] = None
        if os.path.exists(storage_path):
            self.df = pl.read_parquet(storage_path)

    def process_csv(self, csv_path: str):
        """
        Processa o CSV bruto da B3 e converte para Parquet particionado.
        Esperado colunas: ['data', 'investidor', 'posicao_long', 'posicao_short']
        """
        # Exemplo de processamento para o schema da B3
        df_raw = pl.read_csv(csv_path)
        
        # 1. Calcular Posição Líquida
        df_proc = df_raw.with_columns([
            (pl.col("posicao_long") - pl.col("posicao_short")).alias("net_pos")
        ])
        
        # 2. Filtrar apenas Estrangeiro (Non-Resident)
        # B3 costuma usar 'INVESTIDOR NAO RESIDENTE' ou similar
        df_foreign = df_proc.filter(pl.col("investidor").str.contains("NAO RESIDENTE"))
        
        # 3. Calcular Crowding Metrics (Z-Score 60d e Momentum 5d)
        # Sem look-ahead: rolling_mean/std usam apenas o passado
        df_foreign = df_foreign.sort("data").with_columns([
            ((pl.col("net_pos") - pl.col("net_pos").rolling_mean(window_size=60)) / 
             (pl.col("net_pos").rolling_std(window_size=60) + 1e-9)).alias("positioning_z"),
            
            (pl.col("net_pos") - pl.col("net_pos").shift(5)).alias("positioning_momentum")
        ])
        
        # 4. Flags de Extremo
        df_foreign = df_foreign.with_columns([
            (pl.col("positioning_z").abs() > 2.0).alias("crowding_extreme")
        ])
        
        # Persistir
        df_foreign.write_parquet(self.storage_path)
        self.df = df_foreign
        return df_foreign

    def get_position_for_date(self, target_date: date) -> Optional[dict]:
        """
        Retorna o sinal de crowding para uma data específica (considerando D+1).
        O dado de hoje só está disponível para uso amanhã.
        """
        if self.df is None:
            return None
            
        # Procurar o último dado disponível ANTES da target_date
        # Para evitar look-ahead, usamos o dado publicado no dia anterior ou antes
        result = self.df.filter(pl.col("data") < target_date).sort("data", descending=True).head(1)
        
        if result.is_empty():
            return None
            
        return result.to_dicts()[0]
