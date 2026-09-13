# SENTINEL STAR-X

**Autonomous, Trust-Aware, Digital-Twin-Driven Self-Healing & Self-Protecting Network for Adaptive Star Topologies**

SENTINEL STAR-X is an intelligent network resilience platform built around a traditional Star topology's core weakness: dependency on a single central switch. The system continuously monitors network health, traffic, and device behavior; uses AI to detect anomalies, predict failures, and identify probable root causes; maintains dynamic trust scores for every network entity; simulates alternative recovery strategies through a Digital Twin before deploying them; protects business-critical services; and performs security-gated, autonomous self-healing — all while keeping a complete, explainable audit trail of its decisions.

**Core autonomous loop:**
```
MONITOR → DETECT → DIAGNOSE → PREDICT → TRUST EVALUATION → DIGITAL TWIN →
SIMULATE RECOVERY → COMPARE STRATEGIES → DECIDE → SECURITY VALIDATION →
TOPOLOGY ADAPTATION → SELF-HEAL → VERIFY → LEARN → MONITOR
```

---

## Team & Feature Ownership

| Person | Track | Focus |
|---|---|---|
| Akshata | Network + Digital Twin | Simulated topology, live monitoring, the Digital Twin itself |
| Pushkar | AI + Prediction | Anomaly detection, failure prediction, explainable AI, forecasting |
| Manas | Cybersecurity + Trust | Dynamic trust, threat escalation, security-gated recovery, audit trail |
| Aakash | Recovery + Platform | Recovery strategy simulation, decision engine, self-healing, dashboard |

64 features total, split evenly (16 per person). Full feature-by-feature breakdown lives in the project report.

---

## Project Structure

```
Sentinel-Star-X/
├── backend/
│   ├── ai/              # Pushkar — anomaly detection, prediction, explainability
│   ├── api/              # Shared API layer
│   ├── benchmarking/      # Research/benchmarking tooling
│   ├── decision/          # Aakash — multi-objective decision engine
│   ├── digital_twin/      # Akshata — Digital Twin state and simulation
│   ├── experiments/       # Research experiment mode
│   ├── network/           # Akshata — network simulator, topology
│   ├── policy/            # Manas — Policy Engine
│   ├── recovery/          # Aakash — recovery strategies, self-healing, dashboard
│   ├── reporting/         # Automatic incident reports
│   ├── security/          # Manas — trust, threat detection, security gating
│   ├── telemetry/         # Live telemetry ingestion
│   ├── trust/             # Manas — Dynamic Trust Management
│   ├── verification/      # Recovery verification
│   ├── conftest.py        # Shared pytest path configuration (required — do not delete)
│   ├── pytest.ini         # pytest configuration
│   └── requirements.txt
├── data/
│   ├── configurations/
│   ├── experiments/
│   ├── incidents/
│   ├── models/
│   └── telemetry/
├── frontend/               # Command Center Dashboard
└── .gitignore
```

---

## Getting Started

### One-time setup

```powershell
git clone https://github.com/manas765/Sentinel-Star-X.git
cd Sentinel-Star-X
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

### Running the tests

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest -v
```

All modules across all four tracks share one test suite. As of the last full check, **227 tests pass** with zero collection errors.

---

## Contribution Workflow

Never push directly to `main`. Every feature goes through a branch and a Pull Request.

```powershell
# Start a new feature
git checkout main
git pull origin main
git checkout -b yourname/feature-name

# Work, then verify tests pass
cd backend
.\venv\Scripts\Activate.ps1
pytest -v

# Commit and push your branch
git add .
git commit -m "Add [feature name] with tests"
git push origin yourname/feature-name
```

Then open the Pull Request link GitHub gives you and request a review before merging.

---

## Key Design Principles

- **Modular architecture** — networking, AI, security, and recovery stay loosely coupled, communicating through explicit interfaces.
- **Configurable, not hard-coded** — thresholds and recovery policies live in the Policy Engine, not scattered constants.
- **Explainable by default** — every autonomous decision logs a reason and is captured in the Audit Trail.
- **Security-gated recovery** — the Recovery track cannot act on a node until the Security track confirms it's safe to do so.
- **Sandboxed security scenarios** — all anomaly/attack simulations use predefined, controlled data, never real intrusion techniques.
- **Test-first** — every feature ships with its own `pytest` test file covering normal behavior, edge cases, and boundaries.

---

## Documentation

A full project report — architecture, feature-by-feature breakdown per track, and testing status — is maintained separately and updated as each track progresses.