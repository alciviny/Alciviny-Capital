# Relatório: Equilíbrio Rolante vs Níveis Fixos

Este estudo prova que podemos abandonar números fixos (como 57) usando o **Equilíbrio Rolante** do próprio IFR.

## O que é o Equilíbrio Rolante?
É a média (SMA) ou mediana dos últimos 500 períodos do IFR 200. Ele 'descobre' automaticamente onde é o centro do mercado.

## Por que evita Overfit?
- Não depende de uma constante mágica.
- Se o mercado mudar o comportamento daqui a 1 ano, a média móvel do IFR se ajustará sozinha.
- Funciona em qualquer ativo (WIN, WDO, S&P500) sem precisar re-otimizar.
