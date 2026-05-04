import yaml
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.logger import setup_logging, BaseModule

# Inicializar logging centralizado
setup_logging()

class OHLCBar(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float

class AssetCatalog(BaseModel):
    assets: Dict[str, List[str]]

class APIModule(BaseModule):
    def __init__(self):
        super().__init__("API")
        self.config = self._load_config()
        self.storage_path = Path(self.config.get('settings', {}).get('storage_path', 'data/storage'))
        
    def _load_config(self) -> dict:
        try:
            with open("configs/universe.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")
            return {}

# Instanciar orquestrador da API
api_core = APIModule()
app = FastAPI(title="AlcivinyEdger API - Industrial Grade")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Restrito ao frontend Next.js padrão
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/catalog", response_model=AssetCatalog)
def get_catalog():
    """Retorna o catálogo de ativos com base nos arquivos físicos disponíveis."""
    if not api_core.storage_path.exists():
        api_core.logger.warning(f"Diretório de storage não encontrado: {api_core.storage_path}")
        return {"assets": {}}
    
    files = list(api_core.storage_path.glob("*.parquet"))
    catalog = {}
    
    for f in files:
        parts = f.stem.split("_")
        if len(parts) >= 2:
            symbol = "_".join(parts[:-1])
            timeframe = parts[-1]
            if symbol not in catalog:
                catalog[symbol] = []
            catalog[symbol].append(timeframe)
            
    return {"assets": catalog}

@app.get("/data/{symbol}/{timeframe}", response_model=List[Dict])
def get_data(symbol: str, timeframe: str):
    """Lê dados Parquet e retorna todas as colunas (OHLC + Indicadores)."""
    file_path = api_core.storage_path / f"{symbol}_{timeframe}.parquet"
    
    if not file_path.exists():
        api_core.logger.error(f"Arquivo não encontrado: {file_path}")
        raise HTTPException(status_code=404, detail=f"Ativo {symbol} no timeframe {timeframe} não possui dados locais.")
        
    try:
        df = pd.read_parquet(file_path)
        
        # Mapeamento Flexível para colunas base
        column_map = {col.lower(): col for col in df.columns}
        base_required = ['time', 'open', 'high', 'low', 'close']
        
        # Garantir que o OHLC base existe
        mapping = {}
        for req in base_required:
            if req in column_map:
                mapping[column_map[req]] = req
            else:
                api_core.logger.error(f"Coluna base '{req}' ausente em {file_path.name}")
                raise ValueError(f"Coluna base '{req}' ausente")

        # Renomear colunas base e manter as outras (indicadores)
        df = df.rename(columns=mapping)
        
        # Conversão de Tempo
        if pd.api.types.is_datetime64_any_dtype(df['time']):
            df['time'] = df['time'].astype('int64') // 10**9
        
        # Retornar tudo
        return df.to_dict(orient='records')

    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        api_core.logger.critical(f"Falha catastrófica ao ler {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar dados do ativo.")

@app.get("/api/config/indicators")
async def get_indicator_config():
    """Retorna a configuração atual dos indicadores para o frontend."""
    config_path = Path("configs/indicators.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {"indicators": {}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
