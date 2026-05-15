import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.multitest import multipletests
import os
import sys
import logging
from datetime import datetime

# Configuração de Caminhos
sys.path.append(os.getcwd())
from src.data.store import DataStore
from src.indicators.oscillators import calculate_rsi_wilder

class IFR1000ScaleResearch:
    def __init__(self):
        self.store = DataStore()
        self.symbols = ['WIN$', 'WDO$', 'DI1$']
        self.timeframe = 15
        self.horizons = [5, 10, 20, 50, 100, 200]
        self.results = {}
        
        # Definição das Zonas
        self.zones_def = {
            1: "Exaustão Vendedora (<40)",
            2: "Fraqueza Vendedora (40-45)",
            3: "Baixa Consolidada (45-49)",
            4: "Transição Neutra (49-51)",
            5: "Alta Consolidada (51-55)",
            6: "Fraqueza Compradora (55-60)",
            7: "Exaustão Compradora (>60)"
        }

    def load_and_prepare(self, symbol):
        """Carrega dados e calcula IFR(1000) e ATR(20)."""
        df = self.store.load(symbol, self.timeframe)
        if df is None: return None
        print(f"  {symbol} - Loaded: {len(df)} rows")
        
        # IFR(1000) Wilder
        df['ifr'] = calculate_rsi_wilder(df['close'], 1000)
        
        # ATR(20) para normalização
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_20'] = tr.rolling(20).mean()
        
        # Categorização em Zonas
        df['zone'] = 4 # Default Neutro
        df.loc[df['ifr'] < 40, 'zone'] = 1
        df.loc[(df['ifr'] >= 40) & (df['ifr'] < 45), 'zone'] = 2
        df.loc[(df['ifr'] >= 45) & (df['ifr'] < 49), 'zone'] = 3
        df.loc[(df['ifr'] >= 49) & (df['ifr'] <= 51), 'zone'] = 4
        df.loc[(df['ifr'] > 51) & (df['ifr'] <= 55), 'zone'] = 5
        df.loc[(df['ifr'] > 55) & (df['ifr'] <= 60), 'zone'] = 6
        df.loc[df['ifr'] > 60, 'zone'] = 7
        
        # Métricas de Retorno Futuro
        for h in self.horizons:
            # Retorno Bruto
            df[f'ret_{h}'] = df['close'].shift(-h) / df['close'] - 1
            # Retorno Ajustado ATR
            df[f'ret_adj_{h}'] = df[f'ret_{h}'] / (df['atr_20'] / df['close'] + 1e-9)
            # Volatilidade Futura
            df[f'vol_{h}'] = df['close'].rolling(h).std().shift(-h) / df['close']
            # Direção
            df[f'dir_{h}'] = (df[f'ret_{h}'] > 0).astype(int)

        # Remover NaNs apenas das colunas críticas
        cols_to_check = ['ifr', 'atr_20'] 
        for h in self.horizons:
            cols_to_check.extend([f'ret_{h}', f'vol_{h}', f'dir_{h}'])
            
        df = df.dropna(subset=cols_to_check).reset_index(drop=True)
        
        if len(df) == 0:
            print(f"  ERRO: {symbol} ficou vazio após processamento.")
            return None
        return df

    def split_data(self, df):
        """Divisão temporal 60/20/20. OOS é fixo nos últimos 20%."""
        n = len(df)
        is_end = int(n * 0.6)
        val_end = int(n * 0.8)
        
        return df.iloc[:is_end], df.iloc[is_end:val_end], df.iloc[val_end:]

    def compute_neff(self, series):
        """Número efetivo de observações corrigindo autocorrelação."""
        n = len(series)
        if n < 10: return n
        max_lag = min(100, n // 5)
        acf = [series.autocorr(lag=i) for i in range(1, max_lag + 1)]
        acf = np.nan_to_num(acf)
        sum_acf = np.sum([a for a in acf if a > 0.05])
        neff = n / (1 + 2 * sum_acf)
        return max(1, neff)

    def cliff_delta(self, x, y):
        """Calcula Cliff's Delta para efeito não paramétrico."""
        n1, n2 = len(x), len(y)
        if n1 == 0 or n2 == 0: return 0
        
        x = np.asarray(x)
        y = np.asarray(y)
        
        diff = np.expand_dims(x, 1) - np.expand_dims(y, 0)
        delta = np.sum(np.sign(diff)) / (n1 * n2)
        return delta

    def run_permutation_test(self, df, h, n_perms=1000):
        """Teste de permutação global para Kruskal-Wallis."""
        groups = [df[df['zone'] == z][f'ret_{h}'].values for z in range(1, 8)]
        obs_stat, _ = stats.kruskal(*groups)
        
        perm_stats = []
        labels = df['zone'].values.copy()
        rets = df[f'ret_{h}'].values
        
        for _ in range(n_perms):
            np.random.shuffle(labels)
            p_groups = [rets[labels == z] for z in range(1, 8)]
            p_groups = [g for g in p_groups if len(g) > 20]
            if len(p_groups) > 1:
                s, _ = stats.kruskal(*p_groups)
                perm_stats.append(s)
        
        p_perm = np.mean(np.array(perm_stats) >= obs_stat) if perm_stats else 1.0
        return obs_stat, p_perm

    def run_is_analysis(self, df_is, symbol):
        """Executa toda a Parte 3 e 4 (IS) com rigor total."""
        print(f"\n>>> Analisando IS para {symbol}...")
        
        stats_list = []
        for z in range(1, 8):
            z_df = df_is[df_is['zone'] == z]
            freq = len(z_df) / len(df_is)
            
            row = {'symbol': symbol, 'zone': z, 'freq': freq}
            for h in self.horizons:
                row[f'mean_ret_{h}'] = z_df[f'ret_{h}'].mean()
                row[f'hit_rate_{h}'] = z_df[f'dir_{h}'].mean()
                row[f'vol_{h}'] = z_df[f'vol_{h}'].mean()
            stats_list.append(row)
        main_table = pd.DataFrame(stats_list)
        
        kw_results = []
        for h in self.horizons:
            groups = [df_is[df_is['zone'] == z][f'ret_{h}'].values for z in range(1, 8)]
            groups = [g for g in groups if len(g) > 20]
            
            if len(groups) > 1:
                stat, p = stats.kruskal(*groups)
                p_perm = np.nan
                if h in [20, 100]:
                    _, p_perm = self.run_permutation_test(df_is, h, n_perms=200)
            else:
                stat, p, p_perm = 0.0, 1.0, 1.0
            
            kw_results.append({'horizon': h, 'kw_stat': stat, 'p_val': p, 'p_perm': p_perm})
        
        kw_df = pd.DataFrame(kw_results)
        _, kw_df['p_val_fdr'], _, _ = multipletests(kw_df['p_val'], method='fdr_bh')
        
        gradient_results = []
        for h in self.horizons:
            corr, p = stats.spearmanr(df_is['ifr'], df_is[f'ret_{h}'])
            gradient_results.append({'horizon': h, 'spearman_rho': corr, 'p_val': p})
        
        grad_df = pd.DataFrame(gradient_results)
        
        z1_ret = df_is[df_is['zone'] == 1]['ret_20'].values
        z7_ret = df_is[df_is['zone'] == 7]['ret_20'].values
        delta_20 = self.cliff_delta(z7_ret, z1_ret)
        print(f"  Cliff's Delta (Z7 vs Z1) H20: {delta_20:.4f}")
        
        self.plot_point_to_point(df_is, symbol)
        
        return main_table, kw_df, grad_df

    def plot_point_to_point(self, df, symbol):
        """Gera plots de granularidade IFR vs Retorno."""
        os.makedirs("notebooks/ifr/plots_scale", exist_ok=True)
        
        df_copy = df.copy()
        df_copy['ifr_int'] = df_copy['ifr'].round()
        
        for h in [20, 100]:
            grouped = df_copy.groupby('ifr_int')[f'ret_{h}'].mean()
            plt.figure(figsize=(10, 5))
            plt.plot(grouped.index, grouped.values, marker='o', linestyle='-', color='blue')
            plt.axhline(0, color='red', linestyle='--')
            plt.axvline(50, color='gray', linestyle='--', alpha=0.5)
            plt.title(f"Gradiente IFR(1000) vs Retorno Médio H{h} - {symbol}")
            plt.xlabel("Valor IFR")
            plt.ylabel("Retorno Médio")
            plt.grid(True, alpha=0.3)
            plt.savefig(f"notebooks/ifr/plots_scale/{symbol}_gradient_H{h}.png")
            plt.close()

    def run_alternatives(self, df_is, symbol):
        """Parte 5.4 - Compara com Z-score e MA."""
        ma = df_is['close'].rolling(1000).mean()
        std = df_is['close'].rolling(1000).std()
        z_score = (df_is['close'] - ma) / std
        ma_dist = df_is['close'] / ma - 1
        
        h = 20
        valid_idx = z_score.dropna().index
        target_ret = df_is.loc[valid_idx, f'ret_{h}']
        
        corr_ifr, _ = stats.spearmanr(df_is.loc[valid_idx, 'ifr'], target_ret)
        corr_z, _ = stats.spearmanr(z_score.dropna(), target_ret)
        corr_ma, _ = stats.spearmanr(ma_dist.loc[valid_idx], target_ret)
        
        return {
            'symbol': symbol,
            'corr_ifr': corr_ifr,
            'corr_z_score': corr_z,
            'corr_ma_dist': corr_ma
        }

    def run_study(self):
        all_main = []
        all_kw = []
        all_grad = []
        all_alts = []
        
        for symbol in self.symbols:
            df = self.load_and_prepare(symbol)
            if df is None: continue
            
            is_df, val_df, oos_df = self.split_data(df)
            
            main_table, kw_df, grad_df = self.run_is_analysis(is_df, symbol)
            all_main.append(main_table)
            all_kw.append(kw_df)
            all_grad.append(grad_df)
            
            alts = self.run_alternatives(is_df, symbol)
            all_alts.append(alts)
            
            val_main, val_kw, val_grad = self.run_is_analysis(val_df, symbol)
            
            is_rho_20 = grad_df[grad_df['horizon'] == 20]['spearman_rho'].values[0]
            val_rho_20 = val_grad[val_grad['horizon'] == 20]['spearman_rho'].values[0]
            
            pass_val = (np.sign(is_rho_20) == np.sign(val_rho_20)) and (abs(val_rho_20) > 0.01)
            
            if pass_val:
                oos_main, oos_kw, oos_grad = self.run_is_analysis(oos_df, symbol)
                oos_main.to_csv(f"notebooks/ifr/ifr_1000_scale_oos_{symbol}.csv", index=False)

        if all_main:
            pd.concat(all_main).to_csv("notebooks/ifr/ifr_1000_scale_is_main.csv", index=False)
            pd.concat(all_kw).to_csv("notebooks/ifr/ifr_1000_scale_is_kw.csv", index=False)
            pd.concat(all_grad).to_csv("notebooks/ifr/ifr_1000_scale_is_grad.csv", index=False)
            pd.DataFrame(all_alts).to_csv("notebooks/ifr/ifr_1000_scale_is_alts.csv", index=False)

if __name__ == "__main__":
    research = IFR1000ScaleResearch()
    research.run_study()
