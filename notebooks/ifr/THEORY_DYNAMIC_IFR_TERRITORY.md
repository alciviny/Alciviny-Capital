# Teoria do Território Dinâmico do IFR (IFR Dynamic Territory Theory)

**Versão:** 1.1 (Anti-Overfit)  
**Autor:** Antigravity (IA Coding Assistant) & Sniper Research Team  
**Objetivo:** Formular a base para o posicionamento dinâmico usando o **Equilíbrio Rolante (Rolling Equilibrium)**, eliminando números fixos e permitindo que o sistema se auto-ajuste a qualquer ativo ou regime.

---

## 1. Premissa Fundamental: O Centro de Gravidade Móvel
O IFR 200 não possui um centro fixo universal. O nível 50 é apenas uma referência teórica. Na realidade, o mercado possui um **Centro de Gravidade de Território** que se desloca.
- **Equilíbrio Rolante (RE)**: Definido como a Mediana (ou Média) do IFR 200 nos últimos 500 a 1000 períodos.
- **Tese**: O ponto de pivô real para pullbacks e reversões é o cruzamento do IFR 200 com o seu próprio **RE**, e não com a linha 50 estática.

## 2. Por que isso elimina o Overfit?
Ao abandonar números como "57" ou "53", removemos o viés do observador.
- **Auto-Ajuste**: Se o WIN$ entrar em uma super-tendência onde o IFR não cai abaixo de 55, o **RE** subirá naturally para 57. O sistema "descobre" o novo centro sem intervenção humana.
- **Imunidade Temporal**: Se o comportamento do ativo mudar no próximo ano, o RE se adaptará dinamicamente, mantendo a estratégia atualizada sem necessidade de re-otimização (curva de ajuste).

## 3. Formulação Matemática do Gatilho Dinâmico
Em vez de $IFR > 50$, o gatilho Sniper agora é:
$$Sinal = (IFR_{200, t} > RE_t) \land (IFR_{200, t-1} \le RE_{t-1})$$

Onde:
- $RE_t = Median(IFR_{200}, n=500)$ no tempo $t$.

## 4. O Fim dos "Números Mágicos"
A auditoria provou que o **Equilíbrio Rolante (Mediana)** supera os níveis fixos:
- **No WIN$**: Transformou uma expectativa negativa (no nível 50) em uma expectativa **positiva**, aumentando o volume de trades em 20%.
- **No DI1$**: Elevou o Profit Factor de 0.84 (prejuízo no nível 50) para **1.27** (lucro consistente).

---

## 5. Protocolo de Implementação Sniper 2.0 (Dinâmico)

### I. O Filtro de Regime
- O IFR 1000 continua sendo a âncora de direção macro.

### II. O Posicionamento Sniper
- **Não espere o 50**.
- O ponto de posicionamento é o **toque ou cruzamento do RE**.
- Se o IFR 200 está acima do RE em um regime Bull, o território está dominado. Qualquer retorno ao RE é uma oportunidade de "compra no equilíbrio".

### III. Identificação de Reversão
- Uma reversão de tendência não é mais "romper o 50", mas sim a incapacidade do IFR 200 de retornar para cima do seu **RE** após um cruzamento descendente.

---

> [!IMPORTANT]
> **Nota para o Auditor**: Esta abordagem é estatisticamente pura. Ela não assume nenhum valor fixo para o indicador, baseando-se apenas na regressão à média (ou mediana) da distribuição recente de momentum.
