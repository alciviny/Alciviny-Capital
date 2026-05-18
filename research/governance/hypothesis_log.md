# Research Governance & Hypothesis Log: AlcivinyEdger

## Project Status: RESEARCH FREEZE (Phase 1 Complete)
**Date:** 2026-05-16
**Objective:** Institutionalize Microstructure Execution & Macro Risk Engine.

---

## 1. Validated Hypotheses (Approved for Production Shadow)

### H1: Trapped Buyers/Sellers (Micro-Timing)
- **Status:** APPROVED (Filtered)
- **Evidence:** 5m Signal Quality +22 bps.
- **Caveat:** TOXIC without aggressive execution. Must use Market Orders.
- **Kill Criteria:** Adverse Selection > Signal Alpha.

### H2: Volume-based Probability of Informed Trading (VPIN)
- **Status:** APPROVED (Operational)
- **Evidence:** High correlation with execution toxicity and realized slippage.
- **Use Case:** Real-time toxicity filter for order sizing.

### H3: Macro Regime Persistence (HMM)
- **Status:** APPROVED (Risk Engine)
- **Evidence:** Stress regimes persist for ~13h. 
- **Use Case:** Adaptive position sizing (Reduce risk in high-entropy/stress states).
- **Recalibration:** Bi-weekly (15 days).

---

## 2. Rejected Hypotheses (Technical Debt / Narrative Kill)

### R1: Absorption as Standalone Alpha
- **Status:** REJECTED
- **Reason:** Alpha is consumed by spread and fees. 
- **Learning:** Non-monetizable at 5m resolution.

### R2: Static HMM (1-Year Window)
- **Status:** REJECTED
- **Reason:** Transition Matrix Drift (0.36) too high.
- **Learning:** Structural regimes are non-stationary; require adaptive calibration.

### R3: Alpha Prediction via Macro Regimes
- **Status:** REJECTED (Narrative)
- **Reason:** R2 is negative for linear prediction.
- **Learning:** Regimes optimize risk (DD reduction 35%), but do not predict direction.

---

## 3. Operational Governance

| Gate | Threshold | Action |
| :--- | :--- | :--- |
| **Integrity Drift** | > 500ms | Stop Trading (Feed Inconsistency) |
| **Regime Entropy** | > 0.8 | Reduce Exposure (Uncertainty) |
| **Feature PSI** | > 0.25 | Retrain Mandatory (Structural Drift) |
| **Slippage P95** | Historical Max | Disable Signal (Adverse Selection) |

---

## 4. Lifecycle Governance & Retirement Criteria

| Component | Expected Horizon | Retirement Trigger |
| :--- | :--- | :--- |
| **Trapped Buyers (5m)** | 6-12 Months | Net Alpha < 5 bps (30d rolling) |
| **VPIN Engine** | 12-18 Months | Correlation with Toxicity < 0.3 |
| **Macro HMM** | 18-24 Months | Transition Matrix Stability Error > 0.5 |
| **OFI Feature** | 24+ Months | Hurst Exponent < 0.45 (Mean Reversion) |

---

## 5. Final Veredict
The system is now a **Risk-First Adaptive Framework**. Future work must focus exclusively on **Latency Topology**, **State Synchronization**, and **Accountability Audit**.
