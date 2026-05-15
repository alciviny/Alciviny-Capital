import numpy as np
import pandas as pd
import time
from scipy import stats
from scipy.stats import entropy
import math

# Importar as novas implementações
from src.indicators.regime.hurst import HurstDFACalculator
from src.indicators.regime.entropy import PermutationEntropyAnalyzer

# ==========================================
# IMPLEMENTAÇÕES LEGADAS CORRIGIDAS PARA RMS
# ==========================================

def legacy_dfa_rms(x, scales):
    N = len(x)
    y = np.cumsum(x - np.mean(x))
    F_n = []
    for n in scales:
        segments = int(N // n)
        all_residuals_sq = []
        for i in range(segments):
            y_seg = y[i*n : (i+1)*n]
            t = np.arange(n)
            slope, intercept, _, _, _ = stats.linregress(t, y_seg)
            trend = slope * t + intercept
            all_residuals_sq.extend((y_seg - trend)**2)
        # RMS Real: Raiz da média dos quadrados de TODOS os resíduos
        F_n.append(np.sqrt(np.mean(all_residuals_sq)))
    
    log_n = np.log(scales)
    log_F = np.log(F_n)
    slope, _, r_val, _, _ = stats.linregress(log_n, log_F)
    return slope, r_val**2

# ==========================================
# EXECUÇÃO DO TESTE DE PARIDADE
# ==========================================

def run_parity_check():
    print("Teste de Paridade Técnica: Industrialized vs Legacy (Refined)\n")
    
    np.random.seed(42)
    n_obs = 300
    data = np.random.normal(0, 0.01, n_obs)
    series = pd.Series(data)
    
    # --- TESTE HURST ---
    print("--- Verificando Hurst DFA ---")
    scales = [10, 20, 30]
    calc_new = HurstDFACalculator(window=100, scales=scales, r2_threshold=0.0)
    res_new = calc_new.compute_rolling(series)
    
    res_legacy = np.full(len(series), np.nan)
    for i in range(100, len(series) + 1):
        h, _ = legacy_dfa_rms(series.values[i-100:i], scales)
        res_legacy[i-1] = h
    
    mask_hurst = ~np.isnan(res_legacy) & ~np.isnan(res_new['hurst'].values)
    diff_hurst = np.mean(np.abs(res_new['hurst'].values[mask_hurst] - res_legacy[mask_hurst]))
    print(f"MAE Hurst: {diff_hurst:.2e}")

    # --- TESTE ENTROPIA ---
    print("\n--- Verificando Permutation Entropy ---")
    analyzer_new = PermutationEntropyAnalyzer(rolling_window=63, m=3, tau=1)
    analyzer_new.returns = pd.DataFrame({'r_ibov': series, 'r_dol': series, 'r_di1': series})
    analyzer_new.rolling_pe()
    res_pe_new = analyzer_new.pe_series['r_ibov'].values
    
    # Aqui o legacy PE já batia com a nova implementação de hashing
    def legacy_pe_simple(x, m=3, tau=1):
        patterns = [tuple(np.argsort(x[i:i+m*tau:tau])) for i in range(len(x)-(m-1)*tau)]
        _, counts = np.unique(patterns, axis=0, return_counts=True)
        return entropy(counts/len(patterns))/np.log(math.factorial(m))

    res_pe_legacy = np.full(len(series), np.nan)
    for i in range(63, len(series)+1):
        res_pe_legacy[i-1] = legacy_pe_simple(series.values[i-63:i])

    diff_pe = np.nanmean(np.abs(res_pe_new - res_pe_legacy))
    print(f"MAE Entropia: {diff_pe:.2e}")

    print("\n" + "="*40)
    if diff_hurst < 1e-10 and diff_pe < 1e-10:
        print("RESULTADO: PARIDADE MATEMÁTICA TOTAL")
    else:
        print(f"RESULTADO: DIVERGÊNCIA (Hurst: {diff_hurst:.2e}, PE: {diff_pe:.2e})")
    print("="*40)

if __name__ == "__main__":
    run_parity_check()
