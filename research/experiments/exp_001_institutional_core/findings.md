# Findings: EXP-001 - Institutional Intelligence Foundation

## 📊 Resultados Quantitativos

| Métrica | Valor | Observação |
|:---|:---|:---|
| Convergência DCC | 🟢 Sucesso | O modelo conseguiu estimar correlações dinâmicas em dados sintéticos. |
| Detecção de Regimes | 🟢 Sucesso | Identificou 3 estados distintos (Bull, Bear, Crise) com base na volatilidade. |
| Latência de Cálculo | 🟡 Moderada | O modelo Markov é pesado (~2-5s por dataset de 1000 candles). |

## 💡 Descobertas e Insights
1. **Escalonamento é Crítico**: Retornos percentuais brutos (ex: 0.0001) causam falhas de convergência no GARCH. Multiplicar por 100 (pontos percentuais) estabiliza os modelos MLE.
2. **Correlação Dinâmica vs Rolling**: O DCC se mostrou muito mais reativo a picos de volatilidade do que a correlação de janela fixa (rolling), o que é ideal para detecção de crises.

## 🏁 Conclusão
A fundação matemática está sólida. O próximo passo lógico é a alimentação com **Dados Reais** para validar a tese de liderança do DI.
