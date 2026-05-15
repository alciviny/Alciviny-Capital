import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.multitest import multipletests
from sklearn.utils import resample
from datetime import datetime
import yaml

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.indicators.oscillators import calculate_rsi_wilder
from src.data.store import DataStore
from src.core.logger import setup_logging

setup_logging()

class IFR1000Research:
    """
    Motor de Pesquisa Quantitativa para a Teoria IFR(1000) Linha 50.
    """
    def __init__(self, assets=['WIN$', 'WDO$', 'DI1$'], timeframe=15):
        self.assets = assets
        self.timeframe = timeframe
        self.store = DataStore()
        self.horizons = [5, 10, 20, 50, 100, 200, 500]
        self.results = {}

    def load_and_prepare(self, symbol):
        """Carrega e prepara os dados para o estudo."""
        df = self.store.load(symbol, self.timeframe)
        if df is None or df.empty:
            print(f"Erro ao carregar {symbol}_{self.timeframe}")
            return None
        
        df = df.sort_values('time').reset_index(drop=True)
        
        # 1. Calcular IFR(1000)
        df['ifr_1000'] = calculate_rsi_wilder(df['close'], period=1000)
        
        # 2. Rotular Regimes
<<<<<<< HEAD
=======
        # Regime Alta: IFR > 51.0
        # Regime Baixa: IFR < 49.0
        # Neutra: 49.0 <= IFR <= 51.0
>>>>>>> 13985eb (sync: prepare local for remote pull)
        df['regime'] = 'Neutra'
        df.loc[df['ifr_1000'] > 51.0, 'regime'] = 'Alta'
        df.loc[df['ifr_1000'] < 49.0, 'regime'] = 'Baixa'
        
<<<<<<< HEAD
        # 3. Calcular Retornos Futuros
=======
        # 3. Calcular Retornos Futuros (Definição A: Raw, Definição B: Risk-Adjusted)
        # ATR(20) para normalização
>>>>>>> 13985eb (sync: prepare local for remote pull)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_20'] = tr.rolling(20).mean()
        
        for h in self.horizons:
<<<<<<< HEAD
            df[f'ret_{h}'] = df['close'].shift(-h) / df['close'] - 1
            df[f'ret_adj_{h}'] = df[f'ret_{h}'] / (df['atr_20'] / df['close'] + 1e-9)
            
=======
            # Retorno simples
            df[f'ret_{h}'] = df['close'].shift(-h) / df['close'] - 1
            # Retorno ajustado ao risco
            df[f'ret_adj_{h}'] = df[f'ret_{h}'] / (df['atr_20'] / df['close'] + 1e-9)
            
        # Remover warmup e NaNs de retorno futuro
>>>>>>> 13985eb (sync: prepare local for remote pull)
        df = df.dropna().reset_index(drop=True)
        return df

    def split_data(self, df):
        """Divisão temporal estrita 60/20/20."""
        n = len(df)
        is_end = int(n * 0.6)
        val_end = int(n * 0.8)
        
        is_df = df.iloc[:is_end].copy()
        val_df = df.iloc[is_end:val_end].copy()
        oos_df = df.iloc[val_end:].copy()
        
        return is_df, val_df, oos_df

    def compute_neff(self, series):
        """Calcula o número efetivo de observações (Neff) corrigindo autocorrelação."""
        n = len(series)
        if n < 2: return n
        
<<<<<<< HEAD
=======
        # Calcular autocorrelação até lag 100 ou n/10
>>>>>>> 13985eb (sync: prepare local for remote pull)
        max_lag = min(100, n // 10)
        acf = [series.autocorr(lag=i) for i in range(1, max_lag + 1)]
        acf = np.nan_to_num(acf)
        
<<<<<<< HEAD
=======
        # Neff = N / (1 + 2 * sum(acf))
        # Usamos apenas acf significativo ou positivo para ser conservador
>>>>>>> 13985eb (sync: prepare local for remote pull)
        sum_acf = np.sum([a for a in acf if a > 0.05])
        neff = n / (1 + 2 * sum_acf)
        return max(1, neff)

    def run_statistical_tests(self, df, symbol, phase='IS'):
        """Executa a bateria de testes estatísticos."""
        stats_list = []
        
        for h in self.horizons:
            for ret_col in [f'ret_{h}', f'ret_adj_{h}']:
                alta = df[df['regime'] == 'Alta'][ret_col]
                baixa = df[df['regime'] == 'Baixa'][ret_col]
                
                if len(alta) < 30 or len(baixa) < 30:
                    continue
                
<<<<<<< HEAD
                t_stat, p_welch = stats.ttest_ind(alta, baixa, equal_var=False)
                u_stat, p_mw = stats.mannwhitneyu(alta, baixa, alternative='two-sided')
                d = (alta.mean() - baixa.mean()) / np.sqrt((alta.std()**2 + baixa.std()**2) / 2)
                
                neff_alta = self.compute_neff(alta)
                neff_baixa = self.compute_neff(baixa)
                
                t_adj = d * np.sqrt((neff_alta * neff_baixa) / (neff_alta + neff_baixa))
                p_adj = 2 * (1 - stats.t.cdf(np.abs(t_adj), df=min(neff_alta, neff_baixa)-1))
                
                diff_means = []
                for _ in range(1000):
=======
                # 1. Welch t-test
                t_stat, p_welch = stats.ttest_ind(alta, baixa, equal_var=False)
                
                # 2. Mann-Whitney U
                u_stat, p_mw = stats.mannwhitneyu(alta, baixa, alternative='two-sided')
                
                # 3. Cohen's d
                d = (alta.mean() - baixa.mean()) / np.sqrt((alta.std()**2 + baixa.std()**2) / 2)
                
                # 4. Neff Correction (conservador)
                # Aplicamos Neff na média para ajustar o p-valor do t-test
                neff_alta = self.compute_neff(alta)
                neff_baixa = self.compute_neff(baixa)
                
                # Recalcular p-valor com Neff
                t_adj = d * np.sqrt((neff_alta * neff_baixa) / (neff_alta + neff_baixa))
                p_adj = 2 * (1 - stats.t.cdf(np.abs(t_adj), df=min(neff_alta, neff_baixa)-1))
                
                # 5. Bootstrap IC 95%
                diff_means = []
                for _ in range(1000): # 1000 para velocidade no teste, 10000 no final
>>>>>>> 13985eb (sync: prepare local for remote pull)
                    s_alta = resample(alta)
                    s_baixa = resample(baixa)
                    diff_means.append(s_alta.mean() - s_baixa.mean())
                
                ci_low, ci_high = np.percentile(diff_means, [2.5, 97.5])
                
                stats_list.append({
                    'symbol': symbol,
                    'phase': phase,
                    'horizon': h,
                    'ret_type': 'Adjusted' if 'adj' in ret_col else 'Raw',
                    'mean_alta': alta.mean(),
                    'mean_baixa': baixa.mean(),
                    'p_welch': p_welch,
                    'p_mw': p_mw,
                    'p_adj_neff': p_adj,
                    'cohen_d': d,
                    'ci_low': ci_low,
                    'ci_high': ci_high,
                    'n_alta': len(alta),
                    'n_baixa': len(baixa),
                    'neff_total': neff_alta + neff_baixa
                })
                
        return pd.DataFrame(stats_list)

    def run_full_study(self):
        """Executa todo o fluxo de pesquisa."""
        all_stats = []
        
        for symbol in self.assets:
<<<<<<< HEAD
=======
            print(f"\n>>> Estudando Ativo: {symbol}")
>>>>>>> 13985eb (sync: prepare local for remote pull)
            df = self.load_and_prepare(symbol)
            if df is None: continue
            
            is_df, val_df, oos_df = self.split_data(df)
<<<<<<< HEAD
            is_stats = self.run_statistical_tests(is_df, symbol, 'IS')
            all_stats.append(is_stats)
            
            val_stats = self.run_statistical_tests(val_df, symbol, 'VAL')
            all_stats.append(val_stats)
            
            self.plot_regimes(is_df, symbol)
            self.plot_distribution(is_df, symbol)
            
            self.results[symbol] = {
                'is': is_df, 'val': val_df, 'oos': oos_df,
                'is_stats': is_stats, 'val_stats': val_stats
            }

        full_df = pd.concat(all_stats)
=======
            print(f"Amostras - IS: {len(is_df)}, VAL: {len(val_df)}, OOS: {len(oos_df)}")
            
            # Análise IS
            is_stats = self.run_statistical_tests(is_df, symbol, 'IS')
            all_stats.append(is_stats)
            
            # Análise VAL
            val_stats = self.run_statistical_tests(val_df, symbol, 'VAL')
            all_stats.append(val_stats)
            
            # 2. Visualização IS
            self.plot_regimes(is_df, symbol)
            self.plot_distribution(is_df, symbol)
            
            # OOS será aberto no final (opcional ou controlado)
            self.results[symbol] = {
                'is': is_df,
                'val': val_df,
                'oos': oos_df,
                'is_stats': is_stats,
                'val_stats': val_stats
            }

        full_df = pd.concat(all_stats)
        
        # Correção Benjamini-Hochberg
>>>>>>> 13985eb (sync: prepare local for remote pull)
        _, p_corrigido, _, _ = multipletests(full_df['p_adj_neff'], method='fdr_bh')
        full_df['p_fdr'] = p_corrigido
        
        return full_df

    def run_oos_final(self):
        """Abre o cofre (OOS) e valida os resultados."""
<<<<<<< HEAD
=======
        print("\n" + "="*40)
        print("!!! ABRINDO O OUT-OF-SAMPLE (OOS) !!!")
        print("="*40)
        
>>>>>>> 13985eb (sync: prepare local for remote pull)
        oos_results = []
        for symbol, data in self.results.items():
            oos_df = data['oos']
            stats_oos = self.run_statistical_tests(oos_df, symbol, 'OOS')
            oos_results.append(stats_oos)
            
        full_oos = pd.concat(oos_results)
        return full_oos

    def run_robustness_period(self, symbol, periods=[500, 750, 900, 1000, 1100, 1250, 1500]):
        """Testa sensibilidade ao período do IFR."""
        df = self.store.load(symbol, self.timeframe)
        if df is None: return None
        
        robust_list = []
        for p in periods:
            temp_df = df.copy()
            temp_df['ifr'] = calculate_rsi_wilder(temp_df['close'], period=p)
            temp_df = temp_df.dropna()
<<<<<<< HEAD
            temp_df['regime'] = 0
            temp_df.loc[temp_df['ifr'] > 50, 'regime'] = 1
            temp_df.loc[temp_df['ifr'] < 50, 'regime'] = -1
            temp_df['ret_100'] = temp_df['close'].shift(-100) / temp_df['close'] - 1
            temp_df = temp_df.dropna()
            hit_rate = (np.sign(temp_df['regime']) == np.sign(temp_df['ret_100'])).mean()
=======
            
            # Regime simplificado
            temp_df['regime'] = 0
            temp_df.loc[temp_df['ifr'] > 50, 'regime'] = 1
            temp_df.loc[temp_df['ifr'] < 50, 'regime'] = -1
            
            # Retorno futuro (ex: 100 períodos)
            temp_df['ret_100'] = temp_df['close'].shift(-100) / temp_df['close'] - 1
            temp_df = temp_df.dropna()
            
            # Métrica de acerto: regime * sinal(retorno) > 0
            hit_rate = (np.sign(temp_df['regime']) == np.sign(temp_df['ret_100'])).mean()
            
>>>>>>> 13985eb (sync: prepare local for remote pull)
            robust_list.append({'period': p, 'hit_rate': hit_rate})
            
        return pd.DataFrame(robust_list)

    def plot_regimes(self, df, symbol):
        """Plota o preço com os regimes coloridos."""
        plt.figure(figsize=(15, 7))
<<<<<<< HEAD
        plt.subplot(2, 1, 1)
        plt.plot(df['time'], df['close'], color='black', alpha=0.5, label='Close')
        for regime, color in zip(['Alta', 'Baixa', 'Neutra'], ['green', 'red', 'gray']):
            mask = df['regime'] == regime
            plt.scatter(df.loc[mask, 'time'], df.loc[mask, 'close'], color=color, s=1, label=regime)
        plt.title(f"Regimes IFR(1000) - {symbol}")
        plt.legend()
=======
        
        # Plotar Preço
        plt.subplot(2, 1, 1)
        plt.plot(df['time'], df['close'], color='black', alpha=0.5, label='Close')
        
        # Colorir regimes
        for regime, color in zip(['Alta', 'Baixa', 'Neutra'], ['green', 'red', 'gray']):
            mask = df['regime'] == regime
            plt.scatter(df.loc[mask, 'time'], df.loc[mask, 'close'], color=color, s=1, label=regime)
        
        plt.title(f"Regimes IFR(1000) - {symbol}")
        plt.legend()
        
        # Plotar IFR(1000)
>>>>>>> 13985eb (sync: prepare local for remote pull)
        plt.subplot(2, 1, 2)
        plt.plot(df['time'], df['ifr_1000'], color='blue', label='IFR(1000)')
        plt.axhline(51, color='green', linestyle='--')
        plt.axhline(49, color='red', linestyle='--')
        plt.axhline(50, color='black', alpha=0.2)
        plt.ylim(30, 70)
        plt.legend()
<<<<<<< HEAD
        plt.tight_layout()
        os.makedirs("notebooks/ifr/plots", exist_ok=True)
        plt.savefig(f"notebooks/ifr/ifr_1000_regimes_{symbol}.png")
        plt.close()
=======
        
        plt.tight_layout()
        plot_path = f"notebooks/ifr/ifr_1000_regimes_{symbol}.png"
        plt.savefig(plot_path)
        plt.close()
        print(f"Gráfico de regimes salvo: {plot_path}")
>>>>>>> 13985eb (sync: prepare local for remote pull)

    def plot_distribution(self, df, symbol):
        """Histograma e estatísticas descritivas."""
        plt.figure(figsize=(10, 6))
        sns.histplot(df['ifr_1000'], bins=50, kde=True)
        plt.axvline(49, color='red', linestyle='--')
        plt.axvline(51, color='green', linestyle='--')
        plt.title(f"Distribuição IFR(1000) - {symbol}")
<<<<<<< HEAD
        os.makedirs("notebooks/ifr/plots", exist_ok=True)
        plt.savefig(f"notebooks/ifr/ifr_1000_dist_{symbol}.png")
        plt.close()
=======
        
        plot_path = f"notebooks/ifr/ifr_1000_dist_{symbol}.png"
        plt.savefig(plot_path)
        plt.close()
        print(f"Gráfico de distribuição salvo: {plot_path}")
>>>>>>> 13985eb (sync: prepare local for remote pull)

if __name__ == "__main__":
    research = IFR1000Research(assets=['WIN$', 'WDO$', 'DI1$'], timeframe=15)
    stats_df = research.run_full_study()
<<<<<<< HEAD
    output_path = "notebooks/ifr/ifr_1000_results.csv"
    stats_df.to_csv(output_path, index=False)
    robust_df = research.run_robustness_period('DI1$')
    if robust_df is not None:
        robust_df.to_csv("notebooks/ifr/ifr_1000_robustness_period.csv", index=False)
    oos_df = research.run_oos_final()
=======
    
    # Salvar resultados
    output_path = "notebooks/ifr/ifr_1000_results.csv"
    stats_df.to_csv(output_path, index=False)
    print(f"\nResultados salvos em: {output_path}")
    
    # 2. Robustez de Período para DI1$ (que mostrou sinal)
    print("\n>>> Analisando Robustez de Período para DI1$...")
    robust_df = research.run_robustness_period('DI1$')
    if robust_df is not None:
        print(robust_df.to_string(index=False))
        robust_df.to_csv("notebooks/ifr/ifr_1000_robustness_period.csv", index=False)
    
    # 3. VALIDAÇÃO FINAL OOS
    oos_df = research.run_oos_final()
    
    # Comparação DI1$ IS vs OOS
    print("\n>>> VALIDAÇÃO OOS - DI1$ (Horizonte 500)")
    di_is = stats_df[(stats_df['symbol'] == 'DI1$') & (stats_df['phase'] == 'IS') & (stats_df['horizon'] == 500) & (stats_df['ret_type'] == 'Raw')]
    di_oos = oos_df[(oos_df['symbol'] == 'DI1$') & (oos_df['phase'] == 'OOS') & (oos_df['horizon'] == 500) & (oos_df['ret_type'] == 'Raw')]
    
    if not di_oos.empty:
        print(f"IS Mean Return: {di_is['mean_alta'].values[0]:.4f} (Alta) vs {di_is['mean_baixa'].values[0]:.4f} (Baixa)")
        print(f"OOS Mean Return: {di_oos['mean_alta'].values[0]:.4f} (Alta) vs {di_oos['mean_baixa'].values[0]:.4f} (Baixa)")
        print(f"OOS p-adj (Neff): {di_oos['p_adj_neff'].values[0]:.4f}")
        
        if di_oos['p_adj_neff'].values[0] < 0.10 and np.sign(di_oos['mean_alta'].values[0] - di_oos['mean_baixa'].values[0]) == np.sign(di_is['mean_alta'].values[0] - di_is['mean_baixa'].values[0]):
            print("\n✅ VEREDICTO FINAL: HIPÓTESE CONFIRMADA NO OOS PARA DI1$")
        else:
            print("\n❌ VEREDICTO FINAL: HIPÓTESE REPROVADA NO OOS (Falha de Robustez)")

    # Sumário Final
    sig = stats_df[stats_df['p_fdr'] < 0.05]
    if not sig.empty:
        print(f"\n[!] HIPÓTESE SUPORTADA em {len(sig)} configurações (FDR < 0.05):")
        print(sig[['symbol', 'phase', 'horizon', 'ret_type', 'cohen_d', 'p_fdr']].to_string())
    else:
        print("\n[?] NENHUMA CONFIGURAÇÃO significativa após correção de FDR e Neff.")
        print("A teoria pode ser um artefato ou exigir horizontes mais longos/ativos específicos.")
>>>>>>> 13985eb (sync: prepare local for remote pull)
