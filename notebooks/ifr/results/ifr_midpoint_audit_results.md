# Auditoria de Midpoint: Onde o Regime de Fato Muda?

Este estudo analisa o comportamento do IFR 200 ao entrar na 'Zona Neutra' e sua capacidade de prever Pullbacks vs Reversões.

## Ativo: WIN$
| Método      |   Prob Pullback% |   Exp Pullback% |   Exp Reversal% |   Duração Média |   Total Eventos |
|:------------|-----------------:|----------------:|----------------:|----------------:|----------------:|
| Fixed 50    |          85.0183 |     -0.00611114 |       0.0540692 |         20.5542 |             821 |
| Rolling SMA |          82.0078 |     -0.0636935  |       0.0896129 |         22.3377 |             767 |
| Z-Score 0.5 |          73.3246 |     -0.0190289  |       0.0255557 |         12.5099 |             761 |

## Ativo: WDO$
| Método      |   Prob Pullback% |   Exp Pullback% |   Exp Reversal% |   Duração Média |   Total Eventos |
|:------------|-----------------:|----------------:|----------------:|----------------:|----------------:|
| Fixed 50    |          82.4408 |      -0.0178024 |     -0.0703787  |         21.7472 |             803 |
| Rolling SMA |          81.6794 |      -0.0168632 |     -0.00310078 |         23.8537 |             786 |
| Z-Score 0.5 |          75.6927 |      -0.0108409 |      0.032426   |         13.2393 |             794 |

## Ativo: DI1$
| Método      |   Prob Pullback% |   Exp Pullback% |   Exp Reversal% |   Duração Média |   Total Eventos |
|:------------|-----------------:|----------------:|----------------:|----------------:|----------------:|
| Fixed 50    |          82.695  |      0.0066288  |       0.063502  |         22.6837 |             705 |
| Rolling SMA |          80.5797 |      0.05197    |       0.185487  |         27.4681 |             690 |
| Z-Score 0.5 |          75.6391 |     -0.00154383 |       0.0358684 |         14.3128 |             665 |

## Conclusões sobre a Assertividade
1. **Fixed 50 (48/52)**: É a zona clássica. Se a Prob Pullback for alta, confirma a tese de zona de valor.
2. **Rolling/Z-Score**: Se apresentarem maior Exp Pullback, indicam que o 'centro' é dinâmico e depende da volatilidade recente.
3. **Ponto de Inflexão**: O método com menor 'Duração Média' e maior 'Exp Reversal' identifica o momento exato da troca de mãos.
