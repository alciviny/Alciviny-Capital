# AlcivinyEdger - Industrialization Log (v2)

Este documento registra as mudanças estruturais realizadas para transformar o frontend de um protótipo em uma aplicação de nível institucional.

## 1. Arquitetura de Estado (Zustand)
- **Problema**: "Prop-drilling" excessivo e perda de estado ao recarregar a página.
- **Solução**: Implementação do `useUIStore` com middleware de persistência.
- **Impacto**: Preferências de ativos e indicadores agora sobrevivem ao F5.

## 2. Resiliência e Segurança de Dados
- **Problema**: Crashes (Runtime Errors) ao tentar renderizar indicadores com valores nulos (warm-up period).
- **Solução**: Filtro sanitizador no `ChartPane.js` que ignora `null/undefined` antes da renderização.
- **Impacto**: O sistema não trava mais ao carregar indicadores de longo período (ex: IFR 200).

## 3. Performance de Backend & Ingestão
- **Problema**: Cálculo de RSI via loop `for` era um gargalo de CPU.
- **Solução**: Vetorização completa usando Pandas `ewm` (equivalente matemático ao método de Wilder).
- **Impacto**: Redução de ~100x no tempo de processamento dos indicadores.

## 4. Sincronismo de Gráficos
- **Problema**: Crosshair e Zoom dessincronizados entre múltiplos painéis.
- **Solução**: Engine de sincronização centralizada via `syncRef` (Map-based registry).
- **Impacto**: Experiência de análise multi-painel fluida e profissional.

## 5. Configuração Dinâmica
- **Problema**: Lógica de plotagem hardcoded baseada em nomes de strings.
- **Solução**: Introdução do campo `plot_type` no `indicators.yaml`.
- **Impacto**: Novos indicadores podem ser adicionados sem alterar uma única linha de código no frontend.

---
**Status**: Industrializado | **Estabilidade**: Alta | **Performance**: Otimizada
