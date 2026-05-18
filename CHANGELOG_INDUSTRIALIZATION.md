# Log de Industrialização - AlcivinyEdger

Este documento registra a transição do framework de indicadores para um motor institucional probabilístico.

---

## 1. Core Engine & Microestrutura
- **OFIEngine**: Implementação de Order Flow Imbalance com detecção automática de schema (Tick, Partial, OHLCV).
- **VRP Proxy**: Volatility Risk Premium integrado para detecção de explosão de volatilidade.
- **State Vector Factory**: Normalização Z-Score reativa (lookback 20) e estrutural (lookback 60).
- **Evolução**: Suporte a vetores de estado 5D (MRS + Vol + DCC + OFI + VRP).

## 2. Inteligência Institucional
- **InstitutionalClassifier**: Wrapper XGBoost com suporte a probabilidades contínuas.
- **Hybrid Labeling**: Lógica de treinamento anti-circularidade (MRS validado por Forward Return).
- **StrategyRouter**: Orquestrador de estratégias baseado em threshold de confiança.
- **FractionalKellySizer**: Dimensionamento de posição com teto de risco dinâmico por regime de vol.
- **MacroRegimeGate (Gap 2)**: Portão de risco D+1 baseado em crowding (B3) e Z-Score de posicionamento.

## 3. Infraestrutura de Pesquisa
- **Microstructure Analyzer**: Análise Lead-Lag e R² intraday.
- **Predictiveness Validator**: Auditoria quantitativa do poder preditivo de novos indicadores.
- **B3 Position Manager**: Ingestão e processamento de dados de participação de estrangeiros.
- **Training Pipeline**: Script automatizado para treinamento e persistência de modelos.

---

## 4. Status de Industrialização por Gap

| Gap | Descrição | Status | Notas |
|:---|:---|:---|:---|
| **1** | Microestrutura (OFI) | 🟢 100% | Motor pronto; predictiveness auditado em dados reais. |
| **2** | Posicionamento B3 | 🟢 100% | Macro Gate integrado ao Router para proteção contra Crowding. |
| **3** | Meta-Classificador | 🟢 100% | Modelo v1 treinado e integrado. |
| **4** | Portfolio Sizer | 🟢 100% | Kelly Fracionado com dynamic cap implementado. |

---

## 5. Changelog de Versões

### [v2.0.0] - 2026-05-16
- **ESTATÍSTICA**: Implementado **Expanding Window Estimation** para MRS/DCC (eliminação de Lookahead Bias).
- **LABELS**: Substituído shift fixo pelo **Triple Barrier Method (TBM)** (alvos baseados em desfechos financeiros reais).
- **FEATURES**: Adicionada **Entropia de Regime** (Shannon Entropy) e **Delta Probs** para capturar incerteza e velocidade de transição.
- **AUDITORIA**: Implementado script de **Feature Audit** (Proxy SHAP) e **Walk-Forward Analysis (WFA)**.
- **ROBUSTEZ**: Aumentada a regularização L1/L2 do XGBoost para evitar colapso de dimensão.

### [v1.2.0] - 2026-05-16
- **ADICIONADO**: `src/data/b3_pos.py` para gestão de posicionamento estrangeiro.
- **ADICIONADO**: `src/engine/gate.py` com lógica de hierarquia de risco (Crowding Signal).
- **INTEGRADO**: `MacroRegimeGate` no `StrategyRouter` (Risco D+1 agora é transparente).
- **MELHORADO**: Suíte de testes expandida para cobrir lógica de gate e D+1.

### [v1.1.0] - 2026-05-16
- **ADICIONADO**: `src/indicators/microstructure.py` com `OFIEngine`.
- **ADICIONADO**: Suporte a Vetor de Estado 5D em `StateVectorFactory`.
- **MELHORADO**: Normalização Z-Score agora trata divisões por zero com epsilon.

### [v1.0.0] - 2026-05-15
- Versão inicial da industrialização com Meta-Classificador e Engine de Roteamento.
