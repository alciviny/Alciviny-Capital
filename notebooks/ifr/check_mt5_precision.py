import MetaTrader5 as mt5
import os
import sys

# Adicionar o diretório raiz ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.mt5_connector import MT5Connector

def check_precision():
    conn = MT5Connector()
    if not conn.connect(): return
    
    for symbol in ["WIN$", "WDO$", "DI1$"]:
        info = conn.get_symbol_info(symbol)
        if info:
            print(f"\n--- INFO: {symbol} ---")
            for k, v in info.items():
                print(f"{k}: {v}")
    
    conn.disconnect()

if __name__ == "__main__":
    check_precision()
