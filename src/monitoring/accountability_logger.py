import os
import sys
import json
from datetime import datetime
from typing import Dict, Any

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class AccountabilityLogger:
    """
    Logger de Prestao de Contas do Modelo.
    Explica por que cada deciso de sizing ou kill foi tomada.
    """
    def __init__(self, log_path: str = "research/governance/accountability_audit.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_decision(self, action: str, reason: str, context: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "reason": reason,
            "context": context
        }
        
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        print(f"DECISION LOGGED: {action} | Reason: {reason}")

if __name__ == "__main__":
    logger = AccountabilityLogger()
    # Exemplo de deciso de Sizing
    logger.log_decision(
        action="REDUCE_SIZE",
        reason="Regime Stress Detected + High Entropy",
        context={
            "regime_id": 2,
            "entropy": 0.85,
            "realized_vol": 0.002,
            "slippage_avg_1h": 1.45
        }
    )
