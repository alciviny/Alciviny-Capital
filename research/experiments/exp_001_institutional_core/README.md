# EXP-001: Institutional Intelligence Foundation

**Status**: 🟢 ATIVO  
**Data**: 15/05/2026  
**Autor**: Arquiteto AI & Trader

## 1. Hipótese
O mercado brasileiro é movido por drivers institucionais (Diferencial de Juros, Fluxo, Commodities). Ao utilizar modelos de **DCC-GARCH** e **Markov Regime-Switching**, podemos identificar quando as correlações padrão (ex: WIN vs WDO) estão falhando e evitar trades de baixa probabilidade.

## 2. Metodologia
- Implementação de um orquestrador (`engine.py`) que processa:
  - Volatilidade individual (GARCH 1,1).
  - Correlação dinâmica entre pares.
  - Estados ocultos (Regimes de Markov).
  - Análise de microestrutura (Lead-Lag e R²).

## 3. Estrutura do Experimento
- `models/`: Implementações matemáticas puras.
- `analysis/`: Ferramentas de análise de microestrutura.
- `engine.py`: Pipeline unificado.
- `examples/test_drive.py`: Script de validação com dados sintéticos.

## 4. Próximos Passos
- [ ] Validar com dados reais da B3 (WIN, WDO, DI1).
- [ ] Implementar visualização dos regimes em relação ao preço.
- [ ] Testar a tese de "Lead-Lag" onde o DI1 antecipa o WIN.

---
*Para ver as descobertas detalhadas, consulte [findings.md](./findings.md).*
