import pandas as pd
import numpy as np
import os
import sys

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from notebooks.ifr.ifr_regime_diagnostic_tool import IFRRegimeEngine

class RegimeHypothesisTester:
    """Motor de teste de estresse para hipóteses de transição."""
    
    def __init__(self, data: pd.DataFrame):
        self.df = data.copy()
        # Calcular retornos futuros para validação (ex: 20 períodos a frente)
        self.df['fwd_ret_20'] = self.df['close'].pct_change(20).shift(-20)
        self.df['fwd_max_drawdown'] = self.df['close'].rolling(window=20).min().shift(-20) / self.df['close'] - 1
        
        # Garantir que temos hurst_value (usando win do RegimeService se disponível)
        if 'hurst_value' not in self.df.columns and 'hurst_regime' in self.df.columns:
            # Proxy se não tivermos o valor bruto disponível no df direto
            self.df['hurst_value'] = np.where(self.df['hurst_regime'] == 'TRENDING', 0.6, 0.5)

    def run_stress_tests(self):
        print(f"\n{'='*60}")
        print(f"{'TESTE DE HIPÓTESES: ZONA DE TRANSIÇÃO 48-52':^60}")
        print(f"{'='*60}")

        # H1: Regime Crash (48 + High CSD)
        # O CSD alto indica que a estrutura está quebrando
        h1_cond = (self.df['ifr_1000'] < 48) & (self.df['csd_score'] > 0.6)
        h1_results = self.df[h1_cond].dropna(subset=['fwd_ret_20'])
        
        # H2: Transition Trap (48 + Low CSD)
        # CSD baixo indica que a transição não tem "momentum" de instabilidade
        h2_cond = (self.df['ifr_1000'] < 48) & (self.df['csd_score'] < 0.4)
        h2_results = self.df[h2_cond].dropna(subset=['fwd_ret_20'])
        
        # H3: Conquest Confirmation (52 + High Hurst)
        h3_cond = (self.df['ifr_1000'] > 52) & (self.df['hurst_value'] > 0.55)
        h3_results = self.df[h3_cond].dropna(subset=['fwd_ret_20'])

        self._print_report("H1: REGIME CRASH (IFR < 48 + CSD > 0.6)", h1_results, target_dir="down")
        self._print_report("H2: TRANSITION TRAP (IFR < 48 + CSD < 0.4)", h2_results, target_dir="up")
        self._print_report("H3: CONQUEST CONFIRM (IFR > 52 + HURST > 0.55)", h3_results, target_dir="up")

    def _print_report(self, name: str, results: pd.DataFrame, target_dir: str):
        print(f"\n>>> {name}")
        if results.empty:
            print("    [AVISO] Amostras insuficientes para esta hipótese.")
            return
            
        count = len(results)
        avg_ret = results['fwd_ret_20'].mean() * 100
        
        if target_dir == "up":
            hit_rate = (results['fwd_ret_20'] > 0).mean() * 100
        else:
            hit_rate = (results['fwd_ret_20'] < 0).mean() * 100
            
        avg_dd = results['fwd_max_drawdown'].mean() * 100
        std_ret = results['fwd_ret_20'].std() * 100
        
        print(f"    Amostras: {count}")
        print(f"    Retorno Médio (20p): {avg_ret:+.3f}%")
        print(f"    Assertividade Direcional: {hit_rate:.1f}%")
        print(f"    Volatilidade Retorno (Std): {std_ret:.3f}%")
        print(f"    Drawdown Médio Esperado: {avg_dd:.3f}%")
        
        # Lógica de validação qualitativa
        if "CRASH" in name:
            if avg_ret < -0.05 and hit_rate > 55:
                print("    [RESULTADO] Hipótese Altamente Provável. Risco de cauda validado.")
            else:
                print("    [RESULTADO] Hipótese Inconclusiva. O CSD sozinho não garante aceleração.")
        
        if "TRAP" in name:
            if avg_ret > 0:
                print("    [RESULTADO] Hipótese Validada: Zonas de baixa CSD tendem a falhar no rompimento.")
            else:
                print("    [RESULTADO] Hipótese Rejeitada: O mercado continua caindo mesmo com CSD baixo.")

if __name__ == "__main__":
    try:
        engine = IFRRegimeEngine()
        print("[INIT] Carregando dados e alinhando regimes...")
        contract = engine.compute_diagnostics("WIN$", timeframe="15")
        
        tester = RegimeHypothesisTester(contract.df)
        tester.run_stress_tests()
    except Exception as e:
        print(f"[ERROR] {e}")
