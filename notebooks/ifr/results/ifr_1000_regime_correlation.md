# Estudo Avançado: IFR 1000 e Territórios de Regime

## 1. Catalogação por Território

| Território IFR 1000   |   Amostras | Hurst Médio   | FCI Z-Score   | Meta Stability%   | DCC Stress%   | PE Score   | Macro Regime   |
|:----------------------|-----------:|:--------------|:--------------|:------------------|:--------------|:-----------|:---------------|
| Bull Territory (>52)  |       7680 | 0.571         | -0.06         | 58.2%             | 7.5%          | 0.018      | NEUTRAL        |
| Neutral-High (50-52)  |      28575 | 0.551         | 0.02          | 59.5%             | 7.0%          | 0.019      | NEUTRAL        |
| Neutral-Low (48-50)   |      38103 | 0.547         | 0.01          | 58.8%             | 7.4%          | 0.019      | NEUTRAL        |
| Bear Territory (<48)  |      10832 | 0.544         | -0.00         | 58.9%             | 7.5%          | 0.021      | NEUTRAL        |
| Boundary              |          0 | N/A           | N/A           | 0%                | 0%            | N/A        | N/A            |

## 2. Catalogação Granular (Por Nível de IFR)
Este mapeamento identifica a assinatura de regime para cada 'degrau' do IFR 1000.

|   IFR Level |   Amostras |    Hurst |       FCI Z | Stability%   | Stress%   | Macro     |
|------------:|-----------:|---------:|------------:|:-------------|:----------|:----------|
|          45 |         52 | 0.39833  | -0.826471   | 94.2%        | 7.7%      | EXPANSION |
|          46 |        856 | 0.517119 | -0.0819836  | 59.1%        | 9.2%      | EXPANSION |
|          47 |       4778 | 0.535897 |  0.0732066  | 60.5%        | 6.3%      | NEUTRAL   |
|          48 |      12824 | 0.555455 | -0.0786635  | 57.2%        | 7.6%      | NEUTRAL   |
|          49 |      20151 | 0.549042 |  0.0200473  | 59.0%        | 7.1%      | NEUTRAL   |
|          50 |      19792 | 0.540511 |  0.0399504  | 58.5%        | 7.7%      | NEUTRAL   |
|          51 |      14596 | 0.551109 |  0.00838231 | 60.4%        | 7.0%      | NEUTRAL   |
|          52 |       7464 | 0.55584  |  0.0498937  | 60.5%        | 7.5%      | NEUTRAL   |
|          53 |       3261 | 0.587136 | -0.0466902  | 57.9%        | 7.1%      | NEUTRAL   |
|          54 |       1057 | 0.597212 | -0.298444   | 59.6%        | 5.5%      | EXPANSION |
|          55 |        290 | 0.564318 | -0.157295   | 42.1%        | 9.0%      | EXPANSION |
|          56 |         69 | 0.603585 | -0.457418   | 47.8%        | 0.0%      | EXPANSION |

## Conclusões sobre a Teoria de Território
- **Hurst vs IFR**: Verifique se a persistência (Hurst > 0.55) aumenta em níveis específicos.
- **FCI vs IFR**: Níveis com FCI Z-Score positivo e crescente indicam deterioração macro.
- **Zonas de Transição**: Níveis com baixa Stability% são zonas de alta incerteza operacional.
