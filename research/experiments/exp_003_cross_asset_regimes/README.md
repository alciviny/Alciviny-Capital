# EXP-003: Cross-Asset Structural Regimes

## 🎯 Objetivo
Detectar regimes latentes do mercado brasileiro através da análise da topologia relacional entre **WIN** (Risco Equity), **WDO** (Stress Cambial) e **DI1** (Expectativa de Juros).

## 💡 Hipótese Central
As relações dinâmicas (correlação, lead-lag e dispersão) entre os três principais ativos da B3 contêm informação estrutural mais persistente do que sinais microestruturais isolados. Mudanças nessas relações precedem shifts de volatilidade e liquidez.

## 🏗️ Metodologia
A pesquisa está dividida em 6 estágios institucionais:

1.  **Feature Engine**: Cálculo de métricas de interdependência (Pearson, CDI, Granger Causality).
2.  **Regime Discovery**: Uso de HMM/GMM para clusterização de estados ocultos.
3.  **Economic Audit**: Validação da semântica dos regimes (ex: "Risk-On", "Stress Fiscal").
4.  **Persistence Audit**: Medição da meia-vida e estabilidade dos estados detectados.
5.  **Utility Audit**: Avaliação do impacto no dimensionamento de posição e controle de risco.
6.  **Shadow Validation**: Monitoramento em tempo real (60-90 dias).

## 📊 Principais Features
- **Rolling Correlations**: WIN/WDO, WIN/DI1, WDO/DI1.
- **Correlation Dispersion Index (CDI)**: Desvio padrão das correlações rolling.
- **Rolling Granger Causality**: Identificação de quem lidera o movimento em diferentes janelas.
- **Cross-Asset Entropy**: Medida de desordem sistêmica.

## 📋 Registro de Descobertas
*Acompanhe em `findings.md`.*
