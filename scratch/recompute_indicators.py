from src.data.manager import DataManager
from src.data.mt5_connector import MT5Connector
from src.processing.processor import DataProcessor
from src.data.store import DataStore

def update_all_data():
    manager = DataManager()
    store = DataStore()
    processor = DataProcessor()
    
    # Listar arquivos no storage
    storage_path = store.storage_root
    files = list(storage_path.glob("*.parquet"))
    
    for f in files:
        print(f"Processando {f.name}...")
        parts = f.stem.split("_")
        symbol = "_".join(parts[:-1])
        timeframe = int(parts[-1])
        
        df = store.load(symbol, timeframe)
        if df is not None:
            # Recalcular indicadores
            df_with_indicators = processor.compute_indicators(df)
            # Salvar de volta
            store.save(df_with_indicators, symbol, timeframe)
            print(f"OK: {f.name} atualizado com IFR e Grid.")

if __name__ == "__main__":
    update_all_data()
