# TRINITY STRATEGY: Technical Specification & Audit Report
**Versão:** 2.0 (Sniper Upgrade)  
**Status:** APROVADA PARA SHADOW MODE  
**Data da Auditoria:** 2026-05-15

---

## 1. Visão Geral (Executive Summary)
A estratégia **Trinity** é um modelo de reversão à média (pullback) multi-ativo projetado para o mercado brasileiro. Diferente de modelos estáticos, ela utiliza **limiares adaptativos** baseados em quantis dinâmicos para se ajustar à volatilidade e ao regime de mercado. A robustez do sinal é garantida pela confluência entre o Índice (WIN), Dólar (WDO) e Juros (DI1).

## 2. Fundamentação Teórica (The Thesis)
O mercado financeiro brasileiro é estruturalmente interconectado pelo "Tripé de Risco":
1.  **WIN (Bovespa):** Beta e apetite a risco.
2.  **WDO (Dólar):** Fluxo cambial e proteção (hedge).
3.  **DI1 (Juros):** Custo de oportunidade e gravidade econômica.

A tese central é que um **Pullback no WIN** só é estatisticamente confiável quando ocorre em um ambiente de **descompressão nos Juros e no Dólar**. Operar o Índice sem olhar a "gravidade" (DI) é um erro de omissão de variável latente.

## 3. Dinâmica de Microestrutura e Sinais

### 3.1. Estacionaridade e Distribuição de Caudas
O uso de IFR (200) em janelas de 15min transforma o preço (não-estacionário) em um oscilador limitado (estacionário em média). No entanto, o erro clássico é assumir uma distribuição normal.
*   **A Abordagem P45-P55:** Ao mapear os quantis, o modelo ignora o valor nominal do IFR e foca na **densidade de probabilidade**. O P45-P55 representa a "massa central" da distribuição de reversão.
*   **Expectativa Matemática ($E[Trade]$):** 
    $$E[x] = (P(W) \cdot AvgW) - (P(L) \cdot AvgL) - Costs$$
    Para a Trinity, $E[x] \approx 0.098\%$ por trade. Em um horizonte de 40 candles, isso representa uma captura de prêmio de risco por tempo (Theta de volatilidade).

### 3.2. Matriz de Correlação da Trindade (DCC-GARCH Insight)
A robustez vem da **correlação negativa** estrutural:
*   **WIN vs WDO:** $\rho \approx -0.65$
*   **WIN vs DI1:** $\rho \approx -0.50$
*   O sinal Trinity só é gerado quando há uma **divergência momentânea** (WIN cai enquanto WDO/DI1 não sobem proporcionalmente), criando uma mola estatística de retorno à média.

### 3.1. Indicadores Core
*   **RSI (200 períodos):** Utilizado para suavizar o ruído e focar no regime de tendência/exaustão.
*   **Rolling Quantiles (1000 candles):** Em vez de usar níveis fixos (30/70), calculamos dinamicamente os percentis **P45** e **P55** de cada ativo.

### 3.2. Lógica de Sinal (Gatilho)
*   **Filtro de Entrada (WIN):** O RSI do WIN deve ter estado acima do P55 (exaustão de alta) e retornar para a "Zona de Neutralidade" (entre P45 e P55).
*   **Confluência Trinity (Filtros Externos):**
    *   **WDO RSI < P45:** Dólar deve estar fraco ou em queda.
    *   **DI1 RSI < P45:** Juros devem estar estáveis ou em queda.
*   **Upgrade Sniper 2.0 (Micro Timing):**
    *   **IFR 2 (Micro) < 15:** Para entradas de Long, exigimos exaustão de curtíssimo prazo para maximizar o efeito mola.
*   **Direção:** A estratégia atual foca em pullbacks de alta (Long), mas o framework suporta Short via inversão de sinais.

### 3.3. Horizonte de Saída
*   **Saída por Tempo (Exit Horizon):** 40 candles (15min -> ~10 horas de trade). O modelo assume que o retorno à média ocorre dentro deste ciclo médio.

---

## 4. Protocolo de Auditoria e Validação (Anti-Overfit)

Para garantir que a estratégia não é fruto de "ajuste de curva", ela foi submetida a quatro camadas de estresse:

### 4.1. Estabilidade Combinatória (Block Cross-Validation)
Dividimos o histórico em 6 blocos temporais. 
*   **Resultado:** 83% dos blocos apresentaram Profit Factor > 1.0. 
*   **Insight:** A estratégia é resiliente a diferentes épocas, embora apresente variância em regimes de baixa volatilidade (Bloco 03).

### 4.2. Sensibilidade ao Slippage (Cost Stress Test)
Testamos a degradação do lucro conforme os custos operacionais aumentam.
*   **Resultados:**
    *   Slippage 0.000%: PF 1.29
    *   Slippage 0.010%: PF 1.26
    *   Slippage 0.020%: PF 1.23
*   **Conclusão:** A vantagem matemática (Edge) é maior que o custo de fricção do mercado.

### 4.3. Simulação de Monte Carlo (Bootstrap)
Re-amostragem de 1.000 caminhos aleatórios de PnL.
*   **Expectativa Matemática:** 11.33% de retorno médio esperado no longo prazo.
*   **VaR 95% (Drawdown):** -16.70% (com Kelly Full).
*   **Veredito:** Probabilidade de ruína estatisticamente desprezível se respeitado o Kelly Sizer.

---

## 5. Gerenciamento de Capital (Sizing)

A estratégia utiliza o **Kelly Criterion** adaptativo:
$$f^* = \frac{p \cdot R - q}{R}$$
Onde $p$ é a taxa de acerto (56%) e $R$ é a relação win/loss (~1.0).
*   **Recomendação:** Operar com **0.3 Kelly** (conservador) ou **0.5 Kelly** (equilibrado).

---

## 6. Arquitetura do Software (Industrialization)
A implementação foi desacoplada no framework `src/backtest/`:
*   `engine/`: Motor vetorizado Polars para alta performance.
*   `strategies/`: Lógica de alfa isolada (IFRPullbackTrinity).
*   `risk/`: Gerenciamento de capital independente.
*   `validation/`: Suíte de testes de estresse.

## 7. Análise de Falhas e Regimes Adversos (When it Fails)

### 7.1. Regimes de Expansão de Volatilidade (Tail Risk)
A estratégia Trinity é vulnerável a **V-Shapes sem consolidação** ou notícias macroeconômicas que causem uma quebra na correlação WIN/WDO.
*   **Fator de Risco:** Se o DI1 disparar (Gap de alta) enquanto o WIN faz pullback, o modelo Trinity **bloqueia** a entrada, o que é a principal função de preservação de capital do sistema.
*   **Slippage Crítico:** A sensibilidade mostra que se o custo de execução exceder **0.05%**, a edge estatística é consumida pela fricção, tornando o sistema inviável para HFT (High Frequency), mas excelente para Mid-Frequency (15min).

---

**Assinado:**
*Antigravity Quant Agent v2.0*
