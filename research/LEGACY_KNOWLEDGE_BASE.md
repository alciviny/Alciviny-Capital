# 🏛️ AlcivinyEdger - Legacy Knowledge Base (2021-2026)

Este documento preserva as descobertas validadas durante a fase de prototipagem em notebooks. Toda a inteligência contida aqui foi auditada e consolidada para o novo padrão profissional do projeto.

---

## 🎯 1. Estratégia Sniper IFR 200 (WIN$ 15m)
- **Ativo**: Validado exclusivamente para o Mini Índice (WIN). O WDO demonstrou inconsistência neste setup.
- **Regime**: 
    - **Bull**: IFR 200 > 52.
    - **Bear**: IFR 200 < 48.
- **Gatilho Principal**: IFR 50 cruzando 45 (Compra) ou 55 (Venda).
- **Micro-Timing (Sniper 2.0)**: O uso do IFR 2 < 15 como filtro final aumenta a precisão em 35% ao capturar a exaustão do pullback.
- **Performance Histórica**: Lucrativa em todos os anos (2021-2026). Expectativa matemática de ~+0.12% por operação.

---

## 🔬 2. Teoria do Equilíbrio Rolante (RE)
- **Tese**: O nível 50 fixo é um "número mágico" que gera overfit.
- **Descoberta**: O centro de gravidade real do momentum é a **Mediana do IFR 200** (janela de 500-1000 períodos).
- **Impacto**: O uso do RE (Rolling Equilibrium) transforma sistemas perdedores em vencedores, especialmente no ativo **DI1$**, onde o Profit Factor subiu de 0.84 para 1.27.

---

## 🛠️ 3. Metodologia Científica
Preservamos os seguintes protocolos de teste para futuros experimentos:
1.  **Testes de Permutação**: Validação de que a taxa de acerto do sinal é superior a entradas aleatórias (Timing Validation).
2.  **Welch t-test & Cohen's d**: Medição da significância estatística e do tamanho do efeito dos retornos.
3.  **Walk-Forward (60/20/20)**: Divisão rigorosa entre In-Sample, Validação e Out-of-Sample.

---

## 📂 4. Arquivos Preservados (Mapeamento)
Os seguintes scripts foram movidos para `research/shared/` por conterem lógica de auditoria reutilizável:
- `ifr_1000_event_study.py`: Motor de teste de eventos e estatísticas.
- `ifr_1000_regime_study.py`: Análise de estados de mercado.
- `data_sanitizer.py`: Limpeza e tratamento de dados MT5.
