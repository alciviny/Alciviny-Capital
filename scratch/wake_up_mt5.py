import MetaTrader5 as mt5
import time

def wake_up_mt5():
    if not mt5.initialize():
        print(f"Erro ao inicializar: {mt5.last_error()}")
        return

    symbols = ["DI1$", "WIN$", "WDO$", "EURUSD"]
    
    for symbol in symbols:
        print(f"Tentando ativar {symbol}...")
        mt5.symbol_select(symbol, True)
        
        # Tenta baixar 1000 barras para "acordar" o cache
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1000)
        if rates is not None and len(rates) > 0:
            print(f"SUCESSO: {symbol} baixou {len(rates)} barras.")
        else:
            print(f"FALHA: {symbol} não retornou dados. Erro: {mt5.last_error()}")

    mt5.shutdown()

if __name__ == "__main__":
    wake_up_mt5()
