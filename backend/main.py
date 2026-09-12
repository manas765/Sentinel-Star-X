from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import random

app = FastAPI(title="Sentinel Star X")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/network/status")
def network_status():
    return {
        "total_nodes": 12,
        "healthy_nodes": 9,
        "failed_nodes": 2,
        "recovering_nodes": 1,
        "overall_health": 75.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/trust/levels")
def trust_levels():
    data = [
        {"node_id": "node-1",  "trust_level": "NORMAL",     "gate": "PROCEED",  "color": "#22c55e"},
        {"node_id": "node-2",  "trust_level": "QUARANTINE",  "gate": "BLOCKED",  "color": "#7c3aed"},
        {"node_id": "node-3",  "trust_level": "SUSPICIOUS",  "gate": "HOLD",     "color": "#f59e0b"},
        {"node_id": "node-4",  "trust_level": "RESTRICT",    "gate": "MANUAL",   "color": "#ef4444"},
        {"node_id": "node-5",  "trust_level": "NORMAL",      "gate": "PROCEED",  "color": "#22c55e"},
        {"node_id": "node-6",  "trust_level": "MONITOR",     "gate": "PROCEED",  "color": "#3b82f6"},
    ]
    return data

@app.get("/api/recovery/active")
def active_recovery():
    return {
        "node_id": "node-11",
        "strategy": "reroute",
        "elapsed_seconds": 3.2,
        "confidence": 87,
        "cost_score": 24,
        "stages": [
            {"name": "isolate", "status": "done"},
            {"name": "reroute", "status": "active"},
            {"name": "verify",  "status": "pending"},
        ]
    }

@app.get("/api/recovery/recent")
def recent_recoveries():
    return [
        {"node_id": "node-3",  "strategy": "restart",  "success": True,  "trust": "NORMAL",      "time": "2m ago"},
        {"node_id": "node-7",  "strategy": "failover", "success": True,  "trust": "MONITOR",     "time": "8m ago"},
        {"node_id": "node-9",  "strategy": "reroute",  "success": False, "trust": "SUSPICIOUS",  "time": "12m ago"},
        {"node_id": "node-2",  "strategy": "isolate",  "success": False, "trust": "QUARANTINE",  "time": "15m ago"},
    ]

@app.get("/api/decision/latest")
def latest_decision():
    return {
        "node_id": "node-11",
        "scores": [
            {"strategy": "reroute",  "score": 87, "color": "#6366f1"},
            {"strategy": "failover", "score": 61, "color": "#3b82f6"},
            {"strategy": "restart",  "score": 34, "color": "#f59e0b"},
            {"strategy": "isolate",  "score": 18, "color": "#ef4444"},
        ]
    }

@app.get("/api/services/resilience")
def service_resilience():
    return [
        {"service": "web",         "uptime_percent": 96, "is_up": True},
        {"service": "db",          "uptime_percent": 98, "is_up": True},
        {"service": "auth",        "uptime_percent": 91, "is_up": True},
        {"service": "cache",       "uptime_percent": 88, "is_up": True},
        {"service": "api-gateway", "uptime_percent": 41, "is_up": False},
    ]

@app.get("/api/queue/pending")
def pending_approvals():
    return [
        {"request_id": "req-1", "node_id": "node-1", "strategy": "restart"},
        {"request_id": "req-2", "node_id": "node-2", "strategy": "restart"},
    ]
