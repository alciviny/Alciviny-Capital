from typing import Any, List, Dict
import polars as pl
from src.backtest.validation.walk_forward import WalkForwardValidator
from src.backtest.validation.sensitivity import SensitivityValidator
from src.backtest.validation.monte_carlo import MonteCarloSimulator
from src.backtest.reports.generator import ReportGenerator

class IndustrialGatekeeper:
    """
    O "Porteiro Industrial" da Alciviny.
    Submete a estratégia a uma bateria de testes de estresse.
    Somente estratégias que passam em TODOS os critérios são aprovadas para capital real.
    """
    def __init__(self, engine: Any):
        self.engine = engine
        self.validators = [
            WalkForwardValidator(engine),
            SensitivityValidator(engine)
        ]

    def validate(self, data: pl.DataFrame, strategy: Any, risk_manager: Any = None) -> Dict[str, Any]:
        print("\n" + "="*70)
        print(" INICIANDO CERTIFICAÇÃO INDUSTRIAL DE ALFA ".center(70, "="))
        print("="*70 + "\n")

        results = {}
        all_passed = True

        # 1. Backtest Base (Realismo de Stops)
        print("[GATE 1] Backtest Base (Realismo Industrial)...")
        base_metrics = self.engine.run(data, strategy, risk_manager=risk_manager)
        results["base_metrics"] = base_metrics
        
        print(f"  > Trades: {base_metrics['trades_count']} | PF: {base_metrics['profit_factor']:.2f}")
        
        if base_metrics["profit_factor"] < 1.0:
            all_passed = False

        # 2. Executar Validadores Modulares
        for validator in self.validators:
            val_name = validator.__class__.__name__
            print(f"[GATE] Executando {val_name}...")
            val_results = validator.run(data, strategy) # Nota: Alguns validadores rodam sem RM para isolar o edge do setup
            passed = validator.get_verdict(val_results)
            
            results[val_name] = {
                "results": val_results,
                "passed": passed
            }
            
            # Print metrics específicas para transparência
            if "wfe" in val_results:
                print(f"  > WFE: {val_results['wfe']:.2f} | OOS PF: {val_results['avg_oos_pf']:.2f}")
            if "stability_score" in val_results:
                print(f"  > Stability: {val_results['stability_score']*100:.1f}% | Variance: {val_results['pf_variance']*100:.1f}%")
            
            status = "PASS" if passed else "FAIL"
            print(f"  Result: {status}")
            if not passed: all_passed = False

        # 3. Monte Carlo (Risco de Ruína)
        print("[GATE] Monte Carlo Stress Test...")
        trades = self.engine.get_trades()
        mc = MonteCarloSimulator(trades["pnl_pct"])
        mc_results = mc.run_simulation(n_simulations=1000)
        results["MonteCarlo"] = mc_results
        
        if mc_results["95th_percentile_dd"] < -20.0:
            print("  FAIL: Risco de Drawdown excessivo no Monte Carlo.")
            all_passed = False
        else:
            print("  Result: PASS")

        results["final_verdict"] = "APPROVED" if all_passed else "REJECTED"

        print("\n" + "="*70)
        print(f"VEREDITO FINAL: {results['final_verdict']}".center(70))
        print("="*70 + "\n")

        # 4. Relatório Final
        rep = ReportGenerator()
        rep.generate(f"Certified_{strategy.__class__.__name__}", base_metrics, trades)

        return results
