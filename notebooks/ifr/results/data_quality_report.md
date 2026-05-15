# Relatório de Integridade de Dados

Esta auditoria verifica a continuidade e qualidade da base de dados histórica.

| Ativo   |   Total Barras |   Duplicatas |   Gaps Intraday (>15min) |   Tempo Total em Gaps (min) |   Barras Estagnadas (Total) |   Máx Estagnação (Barras) |   Estagnação Média (Barras) |   Estagnação % |
|:--------|---------------:|-------------:|-------------------------:|----------------------------:|----------------------------:|--------------------------:|----------------------------:|---------------:|
| WIN$    |          46387 |            0 |                        6 |                       34485 |                         544 |                         2 |                     1.01304 |        1.17274 |
| WDO$    |          46390 |            0 |                        7 |                       34500 |                        1932 |                         4 |                     1.06681 |        4.16469 |
| DI1$    |          43603 |            0 |                      413 |                       58830 |                        9846 |                        14 |                     1.46365 |       22.581   |

## Conclusões
1. **Gaps Intraday**: Se houver muitos gaps > 15min, os indicadores (IFR, Médias) podem estar 'pulando' informações críticas.
2. **Estagnação**: Preço constante por muito tempo indica perda de conexão com o provedor de dados durante a gravação.
3. **Duplicatas**: Podem distorcer cálculos de momentum e volume.
