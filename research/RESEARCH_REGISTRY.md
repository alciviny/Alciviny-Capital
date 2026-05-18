# 🔬 AlcivinyEdger - Quant Research Registry

Este documento é o índice central de todas as teorias, experimentos e descobertas quantitativas do projeto. O objetivo é manter um histórico profissional, escalável e auditável de cada tese testada.

## 📋 Registro de Experimentos

| ID | Data | Teoria / Hipótese | Status | Resultado Chave | Link |
|:---|:---|:---|:---|:---|:---|
| **EXP-001** | 2026-05-15 | **Institutional Intelligence Foundation** | 🟢 Ativo | DCC-GARCH e Markov implementados | [Ver Experimento](./experiments/exp_001_institutional_core/README.md) |
| **EXP-003** | 2026-05-16 | **Cross-Asset Structural Regimes** | 🟡 Em Progresso | Phase III initialization | [Ver Experimento](./experiments/exp_003_cross_asset_regimes/README.md) |
| **LEG-001** | 2021-2026 | **Sniper IFR 200 (WIN$)** | 🏁 Finalizado | +0.12% exp. mat. validada | [Ver Base Legada](./LEGACY_KNOWLEDGE_BASE.md) |
| **LEG-002** | 2026-05 | **Rolling Equilibrium Theory** | 🏁 Finalizado | Mediana supera nível fixo 50 | [Ver Base Legada](./LEGACY_KNOWLEDGE_BASE.md) |

---

## 🛠️ Guia de Padronização de Pesquisa

Para manter o profissionalismo e a organização, cada novo experimento deve seguir esta estrutura:

1.  **Isolamento**: Criar pasta em `research/experiments/XXX_nome_curto/`.
2.  **README.md**: Descrever a hipótese, metodologia e conclusão.
3.  **Findings**: Registrar métricas (Profit Factor, Sharpe, Correlação) em `findings.md`.

---

## 💾 Política de Gestão de Dados

Para evitar a "perda de informação" e garantir a escalabilidade, seguimos estas regras:

1.  **INPUT (Dados Brutos)**: Dados históricos (Parquet/CSV) vivem em `data/storage/`. Acesso apenas para **LEITURA**.
2.  **RESULTS (Métricas)**: Tabelas resultantes e arquivos JSON ficam em `research/experiments/EXP_XXX/results/`.
3.  **PLOTS (Evidência)**: Gráficos gerados ficam em `research/experiments/EXP_XXX/plots/`.
4.  **ARTIFACTS (Objetos)**: Modelos treinados ou scalers ficam em `research/experiments/EXP_XXX/artifacts/`.

---

## 📈 Descobertas Promovidas (Research to Production)
*Abaixo, listamos o que saiu do laboratório e foi integrado ao sistema de produção (`src/`).*

- *Ainda nenhuma descoberta promovida.*
