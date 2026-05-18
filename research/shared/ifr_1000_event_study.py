import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.utils import resample
from datetime import datetime
import yaml
from tqdm import tqdm

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.indicators.oscillators import calculate_rsi_wilder
from src.data.store import DataStore
from src.core.logger import setup_logging

setup_logging()

class IFR1000EventResearch:
    def __init__(self, assets=['WIN$', 'WDO$', 'DI1$'], timeframe=15):
        self.assets = assets
        self.timeframe = timeframe
        self.store = DataStore()
        self.horizons = [5, 10, 20, 50, 100, 200]
        self.lookback = 50
        self.cooldown = 20
        self.slope_period = 5
        self.results = {}
        
    def load_and_prepare(self, symbol):
        """Carrega dados e calcula indicadores base."""
        df = self.store.load(symbol, self.timeframe)
        if df is None or df.empty:
            print(f"Erro ao carregar {symbol}")
            return None
            
        df = df.sort_values('time').reset_index(drop=True)
        
        # IFR(1000)
        df['ifr'] = calculate_rsi_wilder(df['close'], period=1000)
        
        # ATR(20) para normalização
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_20'] = tr.rolling(20).mean()
        
        # Remover warmup (1000 candles)
        df = df.iloc[1000:].reset_index(drop=True)
        return df

    def detect_events(self, df, variation='A'):
        """Detecta eventos de compra e venda baseados nas regras do Estudo 2."""
        df = df.copy()
        df['signal'] = 0 # 1 para compra, -1 para venda
        
        ifr = df['ifr'].values
        close = df['close'].values
        
        # Obter posição da coluna signal
        sig_col_pos = df.columns.get_loc('signal')
        
        for i in range(self.lookback, len(df)):
            # Evitar sinais dentro do cooldown
            if i > 0 and df['signal'].iloc[max(0, i-self.cooldown):i].abs().sum() > 0:
                continue
                
            # --- COMPRA (Pullback de Alta) ---
            # Condição 1: Excursão (< 49 nos últimos 50 candles)
            excursion_buy = (ifr[i-self.lookback:i] < 49.0).any()
            # Condição 2: Retorno (cruzou >= 49.0 agora)
            return_buy = ifr[i] >= 49.0 and ifr[i-1] < 49.0
            
            if excursion_buy and return_buy:
                # Condição 3: Slope
                slope_ok = False
                if variation == 'A':
                    slope_ok = ifr[i] > ifr[i-self.slope_period]
                elif variation == 'B':
                    slope_ok = close[i] > close[i-self.slope_period]
                elif variation == 'C':
                    slope_ok = (ifr[i] > ifr[i-self.slope_period]) and (close[i] > close[i-self.slope_period])
                
                if slope_ok:
                    df.iloc[i, sig_col_pos] = 1
                    continue

            # --- VENDA (Pullback de Baixa) ---
            excursion_sell = (ifr[i-self.lookback:i] > 51.0).any()
            return_sell = ifr[i] <= 51.0 and ifr[i-1] > 51.0
            
            if excursion_sell and return_sell:
                slope_ok = False
                if variation == 'A':
                    slope_ok = ifr[i] < ifr[i-self.slope_period]
                elif variation == 'B':
                    slope_ok = close[i] < close[i-self.slope_period]
                elif variation == 'C':
                    slope_ok = (ifr[i] < ifr[i-self.slope_period]) and (close[i] < close[i-self.slope_period])
                
                if slope_ok:
                    df.iloc[i, sig_col_pos] = -1
                    
        return df

    def calculate_metrics(self, df):
        """Calcula retornos, MAE e MFE para os horizontes definidos."""
        df = df.copy()
        
        # 1. Calcular retornos para TODOS os candles (Baseline)
        for h in self.horizons:
            # Retorno simples futuro
            df[f'ret_{h}_base'] = df['close'].shift(-h) / df['close'] - 1
            
            # Inicializar colunas de eventos
            df[f'ret_{h}'] = np.nan
            df[f'ret_adj_{h}'] = np.nan
            df[f'mae_{h}'] = np.nan
            df[f'mfe_{h}'] = np.nan
            
        events_idx = df[df['signal'] != 0].index
        
        for idx in events_idx:
            sig = df.loc[idx, 'signal']
            entry_price = df.loc[idx, 'close']
            atr = df.loc[idx, 'atr_20']
            
            for h in self.horizons:
                if idx + h >= len(df): continue
                
                future_window = df.loc[idx+1:idx+h, ['high', 'low', 'close']]
                
                if sig == 1: # Compra
                    raw_ret = (df.loc[idx+h, 'close'] - entry_price) / entry_price
                    mae = (future_window['low'].min() - entry_price) / entry_price
                    mfe = (future_window['high'].max() - entry_price) / entry_price
                else: # Venda
                    raw_ret = (entry_price - df.loc[idx+h, 'close']) / entry_price
                    mae = (entry_price - future_window['high'].max()) / entry_price
                    mfe = (entry_price - future_window['low'].min()) / entry_price
                
                df.loc[idx, f'ret_{h}'] = raw_ret
                df.loc[idx, f'ret_adj_{h}'] = raw_ret / (atr / entry_price + 1e-9)
                df.loc[idx, f'mae_{h}'] = abs(mae) if mae < 0 else 0
                df.loc[idx, f'mfe_{h}'] = mfe if mfe > 0 else 0
                
        return df

    def split_data(self, df):
        """Divisão temporal 60/20/20."""
        n = len(df)
        is_end = int(n * 0.6)
        val_end = int(n * 0.8)
        
        return df.iloc[:is_end].reset_index(drop=True), \
               df.iloc[is_end:val_end].reset_index(drop=True), \
               df.iloc[val_end:].reset_index(drop=True)


    def run_permutation_test(self, df, h, n_perms=1000):
        """Teste de permutação para validar o timing do sinal."""
        events = df[df['signal'] != 0]
        if len(events) == 0: return 1.0
        
        real_hit_rate = (events[f'ret_{h}'] > 0).mean()
        
        # Baseline: retornos de h candles em datas aleatórias
        # Para ser justo, pegamos o mesmo número de eventos
        all_rets = df[f'ret_{h}_base'].dropna().values
        
        count_better = 0
        for _ in range(n_perms):
            perm_rets = np.random.choice(all_rets, size=len(events), replace=True)
            perm_hit_rate = (perm_rets > 0).mean()
            if perm_hit_rate >= real_hit_rate:
                count_better += 1
                
        return count_better / n_perms

    def run_stats(self, df, symbol, phase='IS'):
        """Calcula estatísticas principais."""
        events = df[df['signal'] != 0]
        if len(events) < 5: return pd.DataFrame()
        
        stats_list = []
        for h in self.horizons:
            ret_col = f'ret_{h}'
            event_rets = events[ret_col].dropna()
            baseline_rets = df[f'ret_{h}_base'].dropna()
            
            if len(event_rets) < 5: continue
            
            # Welch t-test vs 0 (hipótese: retorno > 0)
            t_stat, p_val = stats.ttest_1samp(event_rets, 0)
            
            # Taxa de acerto
            hit_rate = (event_rets > 0).mean()
            
            # Cohen's d (vs baseline)
            # Normalizamos o retorno do evento subtraindo a média da baseline
            d = (event_rets.mean() - baseline_rets.mean()) / (baseline_rets.std() + 1e-9)
            
            # MAE / MFE
            mae_avg = events[f'mae_{h}'].mean()
            mfe_avg = events[f'mfe_{h}'].mean()
            ratio = mfe_avg / (mae_avg + 1e-9)
            
            stats_list.append({
                'symbol': symbol,
                'phase': phase,
                'horizon': h,
                'n_events': len(event_rets),
                'hit_rate': hit_rate,
                'mean_ret': event_rets.mean(),
                'p_val': p_val,
                'cohen_d': d,
                'mae_avg': mae_avg,
                'mfe_avg': mfe_avg,
                'ratio_mfe_mae': ratio
            })
            
        return pd.DataFrame(stats_list)

    def run_full_study(self):
        """Executa todo o estudo conforme as partes do prompt."""
        all_is_stats = []
        
        for symbol in self.assets:
            print(f"\n>>> Iniciando Estudo 2 para {symbol}...")
            df_base = self.load_and_prepare(symbol)
            if df_base is None: continue
            
            is_df, val_df, oos_df = self.split_data(df_base)
            
            # Testar as 3 variações no IS
            best_var = 'A'
            best_score = -1
            
            variation_stats = []
            for var in ['A', 'B', 'C']:
                print(f"  Testando Variação {var} no IS...")
                df_is = self.detect_events(is_df, variation=var)
                df_is = self.calculate_metrics(df_is)
                
                st = self.run_stats(df_is, symbol, 'IS')
                if st.empty: continue
                st['variation'] = var
                variation_stats.append(st)
                
                # Critério de escolha: Cohen's d médio nos horizontes 20, 50, 100
                score = st[st['horizon'].isin([20, 50, 100])]['cohen_d'].mean()
                if score > best_score:
                    best_score = score
                    best_var = var
            
            print(f"  Variação vencedora no IS para {symbol}: {best_var} (Score: {best_score:.4f})")
            
            if not variation_stats: continue
            all_is_stats.extend(variation_stats)
            
            # Salvar resultados do IS
            self.results[symbol] = {
                'is_df': is_df,
                'val_df': val_df,
                'oos_df': oos_df,
                'best_var': best_var,
                'is_full_stats': pd.concat(variation_stats)
            }
            
            # --- VALIDAÇÃO (VAL) ---
            print(f"  Validando {best_var} no VAL...")
            df_val = self.detect_events(val_df, variation=best_var)
            df_val = self.calculate_metrics(df_val)
            val_stats = self.run_stats(df_val, symbol, 'VAL')
            if not val_stats.empty:
                val_stats['variation'] = best_var
                self.results[symbol]['val_stats'] = val_stats
                
                # Verificação de Critério (Parte 5.1)
                is_best_stats = self.results[symbol]['is_full_stats']
                is_best_stats = is_best_stats[is_best_stats['variation'] == best_var]
                
                h20_val = val_stats[val_stats['horizon'] == 20]
                h20_is = is_best_stats[is_best_stats['horizon'] == 20]
                
                if not h20_val.empty and not h20_is.empty:
                    hr_is = h20_is['hit_rate'].values[0]
                    hr_val = h20_val['hit_rate'].values[0]
                    ret_is = h20_is['mean_ret'].values[0]
                    ret_val = h20_val['mean_ret'].values[0]
                    
                    print(f"    Hit Rate H20 - IS: {hr_is:.2%} | VAL: {hr_val:.2%}")
                    print(f"    Mean Ret H20 - IS: {ret_is:.6f} | VAL: {ret_val:.6f}")
                    
                    pass_val = (hr_val >= hr_is - 0.08) and (np.sign(ret_val) == np.sign(ret_is))
                    print(f"    Resultado Validação: {'PASSOU' if pass_val else 'FALHOU'}")
                    self.results[symbol]['passed_val'] = pass_val
                else:
                    print("    Aviso: Dados insuficientes para validação H20.")
                    self.results[symbol]['passed_val'] = False
            else:
                print("    Aviso: Nenhum evento detectado no VAL.")
                self.results[symbol]['passed_val'] = False

            # --- ANÁLISE VISUAL (Parte 3.2) ---
            self.plot_event_samples(df_is, symbol)

        return pd.concat(all_is_stats) if all_is_stats else pd.DataFrame()

    def plot_event_samples(self, df, symbol):
        """Plota 10 eventos aleatórios para inspeção visual."""
        events = df[df['signal'] != 0]
        if len(events) == 0: return
        
        sample_idx = events.sample(min(10, len(events))).index
        
        for i, idx in enumerate(sample_idx):
            plt.figure(figsize=(12, 6))
            
            # Janela de 200 candles centrada no evento
            window = df.iloc[max(0, idx-100):min(len(df), idx+100)]
            
            plt.subplot(2, 1, 1)
            plt.plot(window.index, window['close'], color='black', alpha=0.7)
            plt.axvline(idx, color='blue', linestyle='--', label='Evento')
            # Marcação horizontes
            for h in [20, 50, 100]:
                if idx + h < len(df):
                    plt.axvline(idx + h, color='gray', linestyle=':', alpha=0.5)
            
            plt.title(f"Evento {i+1} - {symbol} (Index {idx})")
            plt.legend()
            
            plt.subplot(2, 1, 2)
            plt.plot(window.index, window['ifr'], color='blue')
            plt.axhline(51, color='red', linestyle='-', alpha=0.3)
            plt.axhline(49, color='green', linestyle='-', alpha=0.3)
            plt.axvline(idx, color='blue', linestyle='--')
            plt.ylim(30, 70)
            
            plt.tight_layout()
            os.makedirs(f"notebooks/ifr/plots/{symbol}", exist_ok=True)
            plt.savefig(f"notebooks/ifr/plots/{symbol}/event_{idx}.png")
            plt.close()

    def run_robustness_tests(self):
        """Testa sensibilidade aos parâmetros (Parte 5.2)."""
        symbol = 'WDO$' # Ativo que teve melhor score no IS
        print(f"\n>>> Rodando Testes de Robustez para {symbol} (no IS)...")
        
        df_base = self.load_and_prepare(symbol)
        is_df, _, _ = self.split_data(df_base)
        
        robust_results = []
        
        # Testar Cooldown
        for cd in [10, 20, 30, 50]:
            self.cooldown = cd
            df = self.detect_events(is_df, variation='A')
            df = self.calculate_metrics(df)
            st = self.run_stats(df, symbol, 'Robustness_CD')
            if not st.empty:
                h20 = st[st['horizon'] == 20].iloc[0]
                robust_results.append({'param': 'cooldown', 'value': cd, 'hit_rate': h20['hit_rate'], 'mean_ret': h20['mean_ret']})
        self.cooldown = 20 # Reset
        
        # Testar Lookback Excursão
        for lb in [20, 30, 50, 75, 100]:
            self.lookback = lb
            df = self.detect_events(is_df, variation='A')
            df = self.calculate_metrics(df)
            st = self.run_stats(df, symbol, 'Robustness_LB')
            if not st.empty:
                h20 = st[st['horizon'] == 20].iloc[0]
                robust_results.append({'param': 'lookback', 'value': lb, 'hit_rate': h20['hit_rate'], 'mean_ret': h20['mean_ret']})
        self.lookback = 50 # Reset
        
        return pd.DataFrame(robust_results)

    def run_oos(self):
        """Abre o OOS para ativos que passaram na validação."""
        oos_results = []
        for symbol, data in self.results.items():
            if not data.get('passed_val', False):
                print(f"\n>>> Pulando OOS para {symbol} (Falha na Validação)")
                continue
                
            print(f"\n>>> ABRINDO OOS PARA {symbol} (Variação: {data['best_var']})...")
            df_oos = self.detect_events(data['oos_df'], variation=data['best_var'])
            df_oos = self.calculate_metrics(df_oos)
            stats_oos = self.run_stats(df_oos, symbol, 'OOS')
            stats_oos['variation'] = data['best_var']
            
            # Permutation Test on OOS for H50
            p_perm = self.run_permutation_test(df_oos, 50)
            stats_oos.loc[stats_oos['horizon'] == 50, 'p_perm'] = p_perm
            
            oos_results.append(stats_oos)
            data['oos_stats'] = stats_oos
            
        return pd.concat(oos_results) if oos_results else pd.DataFrame()

if __name__ == "__main__":
    research = IFR1000EventResearch(assets=['WIN$', 'WDO$', 'DI1$'], timeframe=15)
    
    # Executar IS e VAL
    is_stats_df = research.run_full_study()
    
    # Salvar resultados parciais
    is_stats_df.to_csv("notebooks/ifr/ifr_1000_event_is_stats.csv", index=False)
    
    # Executar Robustez
    robust_df = research.run_robustness_tests()
    robust_df.to_csv("notebooks/ifr/ifr_1000_event_robustness.csv", index=False)
    
    # Executar OOS
    oos_stats_df = research.run_oos()
    if not oos_stats_df.empty:
        oos_stats_df.to_csv("notebooks/ifr/ifr_1000_event_oos_stats.csv", index=False)
        
    print("\n\n" + "="*50)
    print("ESTUDO CONCLUÍDO. VERIFIQUE OS ARQUIVOS CSV E PLOTS.")
    print("="*50)
