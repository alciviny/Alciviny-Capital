# Auditoria Comparativa: IFR 1000 vs IFR 200 (WIN$)

## 1. Divisor de Tendência (Retorno Médio %)
O IFR 1000 é um divisor de águas mais robusto que o IFR 200?

### IFR 200
|         |   BULL (>50) |   BEAR (<50) |
|:--------|-------------:|-------------:|
| ret_20  |   0.00817196 |  -0.00705106 |
| ret_100 |   0.00496003 |  -0.00100327 |
| ret_500 |  -0.0085003  |   0.0846947  |

### IFR 1000
|         |   BULL (>50) |   BEAR (<50) |
|:--------|-------------:|-------------:|
| ret_20  |  -0.00679101 |   0.00153809 |
| ret_100 |  -0.0347254  |   0.00708429 |
| ret_500 |  -0.128581   |   0.091139   |

## 2. Sniper Strategy (Performance Backtest)
| Âncora | Trades | Win Rate | Avg Ret | Profit Factor |
| :--- | :--- | :--- | :--- | :--- |
| IFR 200 | 202 | 51.0% | 0.058% | 1.28 |
| IFR 1000 | 397 | 47.9% | -0.031% | 0.89 |

## 3. Dinâmica de Conquista (Prob. de Avanço por Nível)
|   level |   IFR 200 |   IFR 1000 |
|--------:|----------:|-----------:|
|      40 |   71.4286 |   nan      |
|      41 |   66.1017 |   nan      |
|      42 |   64.486  |   nan      |
|      43 |   71.8615 |   nan      |
|      44 |   61.1511 |   nan      |
|      45 |   59.1195 |   nan      |
|      46 |   60.4013 |   100      |
|      47 |   52.3372 |    66.9421 |
|      48 |   45.9114 |    62.5    |
|      49 |   48.6486 |    47.9769 |
|      50 |   49.4461 |    47.817  |
|      51 |   47.3517 |    36.5385 |
|      52 |   43.2964 |    33.9901 |
|      53 |   47.2059 |    24.7312 |
|      54 |   44.0823 |    31.4286 |
|      55 |   37.2922 |    21.4286 |
|      56 |   35.102  |     0      |
|      57 |   42.2819 |   nan      |
|      58 |   52.0325 |   nan      |
|      59 |   34.0206 |   nan      |
|      60 |   34      |   nan      |

## Conclusão Preliminar
- **IFR 200 resiliente**: O período 200 ainda captura melhor as inflexões de médio prazo necessárias para o timing do Mini Índice.
