import polars as pl
import numpy as np
from datetime import datetime

class BacktestEngine:
    """
    Motor de execução profissional focado em performance e fidelidade estatística.
    """
    def __init__(self, transaction_cost: float = 0.02):
        self.cost = transaction_cost

    def run(self, df: pl.DataFrame, risk_config: dict):
        """
        Executa a simulação baseada em sinais e configurações de risco.
        """
        # Preparação
        trades = []
        in_trade = False
        side = None # "BUY" or "SELL"
        entry_price = 0
        sl_price = 0
        tp_price = 0
        entry_time = None
        
        # Convertemos para lista de dicts para o loop de trade (mais preciso que vetorização para SL/TP dinâmico)
        # Nota: Usamos loop aqui apenas para a lógica de trade path, os sinais já vêm vetorizados.
        data = df.to_dicts()
        
        for i, row in enumerate(data):
            if not in_trade:
                # Verificar entradas
                if row.get("entry_buy"):
                    in_trade = True
                    side = "BUY"
                    entry_price = row["close"]
                    entry_time = row["time"]
                    sl_price = entry_price - risk_config.get("stop_pts", 500)
                    tp_price = entry_price + risk_config.get("target_pts", 1000)
                    time_limit = i + risk_config.get("time_exit", 40)
                    
                elif row.get("entry_sell"):
                    in_trade = True
                    side = "SELL"
                    entry_price = row["close"]
                    entry_time = row["time"]
                    sl_price = entry_price + risk_config.get("stop_pts", 500)
                    tp_price = entry_price - risk_config.get("target_pts", 1000)
                    time_limit = i + risk_config.get("time_exit", 40)
            
            else:
                # Verificar saídas (SL, TP ou Tempo)
                exit_trigger = None
                exit_price = row["close"]
                
                if side == "BUY":
                    if row["low"] <= sl_price:
                        exit_trigger = "STOP"
                        exit_price = sl_price
                    elif row["high"] >= tp_price:
                        exit_trigger = "TARGET"
                        exit_price = tp_price
                    elif i >= time_limit:
                        exit_trigger = "TIME"
                        
                elif side == "SELL":
                    if row["high"] >= sl_price:
                        exit_trigger = "STOP"
                        exit_price = sl_price
                    elif row["low"] <= tp_price:
                        exit_trigger = "TARGET"
                        exit_price = tp_price
                    elif i >= time_limit:
                        exit_trigger = "TIME"
                
                if exit_trigger:
                    ret = ((exit_price / entry_price - 1) * 100 if side == "BUY" else (entry_price / exit_price - 1) * 100)
                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": row["time"],
                        "side": side,
                        "entry": entry_price,
                        "exit": exit_price,
                        "reason": exit_trigger,
                        "return_pct": ret - self.cost
                    })
                    in_trade = False
                    
        return pl.DataFrame(trades)
