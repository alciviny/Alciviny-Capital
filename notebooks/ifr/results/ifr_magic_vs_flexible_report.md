# Relatório de Auditoria: IFR 200 (Magic vs Flexible)

## Ativo: WIN$
| Método                |         Exp% |    Win% |   Estabilidade |       PF |
|:----------------------|-------------:|--------:|---------------:|---------:|
| Magic Numbers (48/52) |  0.00129645  | 50.2242 |        371.096 | 1.00426  |
| Adaptive Z-Score      | -0.000137226 | 50.1451 |        219.844 | 0.999551 |
| Perceptis (PE Filter) |  0           |  0      |          0     | 0        |

## Ativo: WDO$
| Método                |       Exp% |    Win% |   Estabilidade |       PF |
|:----------------------|-----------:|--------:|---------------:|---------:|
| Magic Numbers (48/52) | -0.0160281 | 47.9208 |        322.153 | 0.931127 |
| Adaptive Z-Score      | -0.0149659 | 47.9992 |        220.905 | 0.93549  |
| Perceptis (PE Filter) |  0         |  0      |          0     | 0        |

## Ativo: DI1$
| Método                |      Exp% |    Win% |   Estabilidade |      PF |
|:----------------------|----------:|--------:|---------------:|--------:|
| Magic Numbers (48/52) | 0.0462728 | 49.4243 |        327.842 | 1.19442 |
| Adaptive Z-Score      | 0.0444045 | 49.3784 |        238.268 | 1.18683 |
| Perceptis (PE Filter) | 0.340684  | 58.8933 |        990.977 | 3.80161 |

## Conclusão da Auditoria
A hipótese de que os **Números Mágicos (48/52)** são mais assertivos baseia-se na sua estabilidade temporal e na redução do 'chicote' (whipsaw) em zonas de ruído.
Métodos flexíveis como Z-Score e Perceptis tendem a ser mais reativos, mas podem sofrer com a quebra de regime em timeframes menores.
