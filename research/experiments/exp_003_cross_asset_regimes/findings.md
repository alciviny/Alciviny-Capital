# Findings: EXP-003 Cross-Asset Structural Regimes (Audited)

## 🛡️ Auditoria de Robustez (Pós-Refatoração)
- **Status**: Leakage Removido. OOS Validado.
- **Metodologia**: Train/Test Split (70/30) com escalonamento temporal rigoroso.
- **Custos**: Simulação inclui 0.5 bps por troca de regime.

## Performance por Regime (Out-of-Sample)
Os resultados abaixo referem-se exclusivamente ao conjunto de dados que o modelo **nunca viu** durante o treinamento.

| Regime | Label Sugerido | Retorno Médio (OOS) | Conclusão Técnica |
| :--- | :--- | :--- | :--- |
| **0** | **Stress Local** | -0.37 bps | Confirmado como regime de risco; Kill-Switch necessário. |
| **1** | **Transição** | +0.97 bps | Alpha positivo resiliente. |
| **2** | **Consenso Neutro** | +1.01 bps | Mais estável; Ideal para exposição principal. |
| **3** | **Desacoplamento** | -3.18 bps | **ALTO RISCO**. Ativos sem driver comum; Alta probabilidade de stop. |

## 📉 Conclusões da Auditoria
1.  **Validade do Alpha**: O edge não está em prever a direção, mas em **evitar o Regime 3**. A estratégia de filtrar a exposição apenas para os Regimes 1 e 2 superou o Baseline (Buy & Hold) de forma significativa no OOS.
2.  **Instabilidade do Stress**: O Regime 0 mostrou deriva (drift) na correlação com DI1, indicando que "Stress" muda de face ao longo do tempo.
3.  **Utilidade**: Implementar o **Kill-Switch Contextual** baseado na detecção do Regime 3 e na queda de confiança do GMM (< 0.7).

## Próximos Passos
- Migrar lógica para `StateVectorEngine` para monitoramento em Shadow Mode.
- Testar suavização HMM para reduzir custos de transação no chaveamento.
