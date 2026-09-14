# SENTINEL STAR-X
## Autonomous, Trust-Aware, Digital-Twin-Driven Self-Healing & Self-Protecting Network for Adaptive Star Topologies

### Project Report
**Team:** Akshata, Pushkar, Manas, Aakash
**Repository:** github.com/manas765/Sentinel-Star-X

---

## 1. Project Overview

SENTINEL STAR-X is an intelligent network resilience platform built around a traditional Star topology's core weakness: dependency on a single central switch. The system continuously monitors network health, traffic, and device behavior; uses AI to detect anomalies, predict failures, and identify probable root causes; maintains dynamic trust scores for every network entity; simulates alternative recovery strategies through a Digital Twin before deploying them; protects business-critical services; and performs security-gated, autonomous self-healing — all while keeping a complete, explainable audit trail of its decisions.

**Core autonomous loop:**
```
MONITOR → DETECT → DIAGNOSE → PREDICT → TRUST EVALUATION → DIGITAL TWIN →
SIMULATE RECOVERY → COMPARE STRATEGIES → DECIDE → SECURITY VALIDATION →
TOPOLOGY ADAPTATION → SELF-HEAL → VERIFY → LEARN → MONITOR
```

**Research question:** Can a trust-aware Digital Twin autonomously select and validate the safest recovery strategy for failures and security incidents in centralized Star networks, while minimizing service disruption and unnecessary topology changes?

The project's 64 features are split across four tracks, one per team member:

| Person | Track | Focus |
|---|---|---|
| Akshata | Network + Digital Twin | Simulated topology, live monitoring, the Digital Twin itself |
| Pushkar | AI + Prediction | Anomaly detection, failure prediction, explainable AI, forecasting |
| Manas | Cybersecurity + Trust | Dynamic trust, threat escalation, security-gated recovery, audit trail |
| Aakash | Recovery + Platform | Recovery strategy simulation, decision engine, self-healing, dashboard |

---

## 2. System Architecture

```
                     REAL NETWORK (STAR TOPOLOGY)
                               │
                               ▼
                       TELEMETRY ENGINE
                               │
             ┌─────────────────┼─────────────────┐
       Network Health      Security Data      Traffic Data
             └─────────────────┼─────────────────┘
                               ▼
                         DIGITAL TWIN
              ┌────────────────┼─────────────────┐
        AI ENGINE        TRUST ENGINE          SECURITY
      (Pushkar)          (Manas)               (Manas)
              └────────────────┼─────────────────┘
                               ▼
                       DECISION ENGINE (Aakash)
                 ┌─────────────┼─────────────┐
             Backup Star     Hybrid      Partial Mesh
                 └─────────────┼─────────────┘
                               ▼
                    SECURITY GATE (Manas → Aakash)
                               ▼
                    SELF-HEALING (Aakash)
                               ▼
                    VERIFICATION (Aakash)
                               ▼
                    LEARNING / MEMORY (Aakash)
```

---

## 3. Cybersecurity + Trust Track — Manas
### 16 features implemented | 88 automated tests passing

This track implements the trust-management and cybersecurity backbone of the system. Rather than treating devices as simply "trusted" or "untrusted," it maintains a continuous, evolving trust score for every entity, backed by anomaly detection, an explainable threat-level escalation ladder, and autonomous defensive behavior — all fully auditable after the fact.

**Architecture flow:**
```
Network Activity → Security Anomaly Detector (#13) → risk score
   → Failure vs Security Classifier (#14) → probable cause
   → Threat-Level Manager (#15) → NORMAL...EMERGENCY escalation ladder
        ├─► Trust Engine (#10, #11, #12) → live trust score with decay & recovery
        ├─► Critical Service Protection (#18) → stricter rules for critical nodes
        ├─► Security-Gated Recovery (#26) → blocks/holds recovery on compromised nodes
        ├─► Network Survival Mode (#53) → network-wide defensive posture
        ├─► Attack-Path Analysis (#16) → ranks how threats could spread
        ├─► SLA Monitor (#42) → flags breached service commitments
        └─► Policy Engine (#46) → centralizes every threshold above
   → Event Correlator (#58) → fuses related events into one incident
   → Red Team vs Blue Team Simulator (#54) → validates the whole pipeline
   → Automatic Incident Reports (#55) → human-readable report generation
   → Complete Autonomous Audit Trail (#64) → full decision history
```

**Features delivered:**

| # | Feature | Summary |
|---|---|---|
| 10 | Dynamic Trust Management | Continuous 0–100 trust score per entity, with full history and level mapping (TRUSTED/NORMAL/SUSPICIOUS/UNTRUSTED) |
| 11 | Trust Decay and Recovery | Trust erodes faster under repeated bad behavior than it rebuilds under repeated good behavior |
| 12 | Central Switch Trust | Scores the central switch's CPU, memory, packet loss, latency, and failure risk against configurable thresholds |
| 13 | Security Anomaly Detection | Rules-based detection of traffic spikes, unauthorized peers, unauthorized devices, and repeated failed logins |
| 14 | Failure vs Security Incident Differentiation | Probability breakdown across hardware failure, congestion, config error, and security incident |
| 15 | Threat-Level System | Six-level escalation ladder (NORMAL→EMERGENCY); fast to escalate, gradual to de-escalate |
| 16 | Attack-Path / Risk Visualization | Ranks every reachable path from a compromised node by risk, using topology + threat data |
| 18 | Critical Service Protection | Business-critical nodes get stricter, earlier-triggering protection rules |
| 26 | Security-Gated Recovery | Blocks or holds automated recovery on nodes that may still be actively compromised |
| 42 | SLA Monitoring | Tracks uptime/response-time/packet-loss commitments and flags violations by severity |
| 46 | Policy Engine | Centralizes every configurable threshold across the track into one place |
| 53 | Network Survival Mode | Triggers a defensive posture when critical services or the network broadly are under sustained threat |
| 54 | Red Team vs Blue Team | Scripted attack scenarios run through the real detection/response pipeline, end-to-end |
| 55 | Automatic Incident Reports | Converts any simulation/incident into a structured, human-readable report |
| 58 | Event Correlation and Incident Fusion | Groups related flagged events into one incident instead of scattered noise |
| 64 | Complete Autonomous Audit Trail | Append-only log of every trust/threat/recovery decision, fully reconstructable per entity |

**Key design decisions:**
- Trust is continuous, never a binary flag.
- Escalation is fast; de-escalation is gradual — matching how real incidents should be handled.
- Recovery is security-gated, not automatic: the Recovery track cannot act on a node until this track approves it.
- Every threshold is centrally configurable via the Policy Engine.
- Every module returns a `reason` string; the Audit Trail ties the whole history together for explainability.

**Testing:** Built test-first with `pytest`. All 88 tests pass, covering normal behavior, edge cases, and boundary conditions.

**Cross-team integration:** A dedicated bridge module (`security/recovery_integration.py`) exposes `enforce_security_gate(node_id)` for the Recovery track to call before executing any autonomous healing action.

---

## 4. Recovery + Platform Track — Aakash
### Status: in progress

Based on repository history, the following features have been completed and merged:

| # | Feature | Summary |
|---|---|---|
| 21 | Recovery Strategy Simulator | Simulates candidate recovery strategies with probability scoring before any real action is taken |
| 22 | Multi-Objective Decision Engine | Scores simulated strategies against weighted objectives (reliability, cost, safety) to pick the best one |
| 23 | Context-Aware Recovery | Incorporates trust and cost optimization into recovery strategy selection |
| 30 | Network Memory | Stores network snapshots and recovery events for later recall |
| 31 | Recovery Knowledge Base | Recommends strategies based on prior recovery outcomes |
| 33 | Research Experiment Mode | Enables comparing recovery strategies under controlled experimental conditions |
| 56 | Command Center Dashboard | Live network-monitoring dashboard, since redesigned for improved styling |
| 63 | Resource-Aware Recovery Orchestration | Manages recovery execution with queue-based resource awareness |

**Remaining features on this track:** #27 Autonomous Self-Healing, #28 Recovery Verification, #29 Multi-Stage Recovery, #32 Recovery A/B Testing, #43 Recovery Cost Estimation, #45 Human-in-the-Loop, #48 Safe Rollback, #50 Service-Level Resilience.

**Security integration — complete:** `decision_engine.py` now calls `enforce_security_gate()` before scoring or simulating any recovery strategy, so no automated recovery action can run on a node that Manas's Security track flags as still under active threat. A minor NaN bug on the Command Center Dashboard was also fixed.

*[Aakash: please expand this section with implementation details, design decisions, and testing approach for your completed features, in the same style as Section 3 above.]*

---

## 5. Network + Digital Twin Track — Akshata
### Status: not yet reflected in repository history

Assigned features: #1 Intelligent Network Simulator, #2 Real-Time Network Monitoring, #3 Network Health Engine, #4 Digital Twin, #5 Digital Twin Sandbox / What-If Lab, #17 Cascading Failure Prediction, #19 Service Dependency Graph, #20 Critical Path Protection, #24 Dynamic Topology Morphing, #25 Minimum-Change Recovery, #39 Network Time Machine, #47 Configuration Versioning, #49 Network Dependency Analysis, #57 Digital Twin Drift Detection, #61 Topology Recommendation Engine, #62 Simulation Fidelity Calibration.

*[Akshata: please fill in this section once your features are underway — implementation summary, architecture notes, and testing approach, matching the style of Section 3.]*

---

## 6. AI + Prediction Track — Pushkar
### Status: not yet reflected in repository history

Assigned features: #6 AI Anomaly Detection, #7 Predictive Failure Detection, #8 Failure Classification, #9 Root Cause Analysis, #34 Benchmarking Engine, #35 Automatic Graph Generation, #36 SENTINEL Resilience Index, #37 Explainable AI, #38 Incident Replay, #40 Network Forecast / Network Weather, #41 Network Risk Map, #44 Recovery Confidence, #51 AI Network Copilot, #52 Natural-Language What-If, #59 Adaptive Threshold Management, #60 Uncertainty-Aware Autonomous Decisions.

*[Pushkar: please fill in this section once your features are underway — implementation summary, architecture notes, and testing approach, matching the style of Section 3.]*

---

## 7. Combined Testing Status

As of the last full integration check, the combined test suite across all completed work — Manas's Security + Trust track, Aakash's completed Recovery features, and the now-live Security-Recovery gate integration — totals **229 passing tests**, with zero collection errors after resolving an early cross-module import path issue (fixed via a shared `conftest.py`).

---

## 8. Next Steps

1. Akshata and Pushkar to begin/report progress on their tracks.
2. ~~Wire `security/recovery_integration.py`'s `enforce_security_gate()` into Aakash's `decision_engine.py`, so recovery actions are checked against threat level before executing.~~ **Done** — confirmed live and passing as of the latest sync.
3. Resolve outstanding cross-track issues (e.g. a known bug in `RecoveryKnowledgeBase.strategy_summary()`; a duplicate/misnumbered feature PR to redirect).
4. Once Akshata's Network module and Pushkar's AI module have working outputs, connect Manas's `AttackPathAnalyzer` to the real topology graph (currently using a standalone `networkx` graph for validation).
5. Build the end-to-end demo: Detect → Predict → Trust → Simulate → Decide → Secure → Heal → Verify → Learn.
