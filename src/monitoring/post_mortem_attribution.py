import os
import sys
import polars as pl
import pandas as pd
import numpy as np

# Root path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class PostMortemAuditor:
    """
    Auditor de Atribuição Pós-Morte.
    Decompõe o PnL negativo em Signal vs Execution vs Latency.
    """
    def __init__(self, shadow_logs_path: str = None):
        # Como o shadow_engine rodou na memória, vamos simular o carregamento 
        # ou passar os dados diretamente. Para este script, vamos processar 
        # os logs gerados na simulação anterior.
        pass

    def run_attribution(self, log_df: pd.DataFrame):
        print("\n--- POST-MORTEM ALPHA ATTRIBUTION ---")
        
        # 1. Signal Quality (Gross Alpha)
        gross_alpha = log_df['gross_alpha'].mean()
        
        # 2. Execution Leakage (Slippage + Fees)
        slippage = log_df['slippage'].mean()
        fees = 0.3 # Fixed bps
        execution_cost = slippage + fees
        
        # 3. Adverse Selection (Toxic Flow)
        # Na simulação anterior, o PnL líquido foi -2.44.
        # Net = Gross - Execution - AdverseSelection (e outros)
        # Vamos estimar o resíduo como Adverse Selection
        net_pnl = log_df['net_pnl'].mean()
        adverse_selection = gross_alpha - net_pnl - execution_cost
        
        # 4. Decomposição de 100% do Alpha
        total_drag = execution_cost + adverse_selection
        
        print(f"1. Signal Quality (Theoretical):  +{gross_alpha:6.2f} bps")
        print(f"2. Execution Costs (Slippage/Fees): -{execution_cost:6.2f} bps")
        print(f"3. Adverse Selection (Toxic Flow):  -{adverse_selection:6.2f} bps")
        print("-" * 40)
        print(f"FINAL NET REALIZED ALPHA:         {net_pnl:6.2f} bps")
        
        # 5. Veredito Institucional
        print("\nDIAGNÓSTICO FINAL:")
        if adverse_selection > gross_alpha:
            print("STATUS: TOXIC ALPHA. O fluxo informado te atropela antes da captura.")
        elif execution_cost > (gross_alpha * 0.5):
            print("STATUS: ILLIQUID ALPHA. O custo de captura devora a margem de segurança.")
        else:
            print("STATUS: LATENCY ALPHA. O sinal é real mas exige infraestrutura HFT.")

if __name__ == "__main__":
    # Simular dados baseados nos resultados do Shadow Engine anterior
    # Gross Alpha (~22 bps), Net PnL (-2.44 bps), Slippage (1.35 bps)
    data = {
        'gross_alpha': [22.0] * 405,
        'slippage': [1.35] * 405,
        'net_pnl': [-2.44] * 405,
        'status': ['EXECUTED'] * 405
    }
    log_df = pd.DataFrame(data)
    
    auditor = PostMortemAuditor()
    auditor.run_attribution(log_df)
