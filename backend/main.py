from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import random

app = FastAPI(title="Sentinel Star X - Command Center API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mock data endpoints (real impl connects to your modules) ---

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

@app.get("/api/recovery/recent")
def recent_recoveries():
    strategies = ["reroute", "restart", "failover", "isolate"]
    return [
        {
            "node_id": f"node-{i}",
            "strategy": random.choice(strategies),
            "success": random.choice([True, True, True, False]),
            "duration_seconds": round(random.uniform(1.5, 15.0), 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        for i in range(1, 8)
    ]

@app.get("/api/services/resilience")
def service_resilience():
    services = ["web", "db", "auth", "cache", "api-gateway"]
    return [
        {
            "service": s,
            "is_up": random.choice([True, True, True, False]),
            "uptime_percent": round(random.uniform(85.0, 100.0), 1),
        }
        for s in services
    ]

@app.get("/api/security/threat-levels")
def threat_levels():
    levels = ["NORMAL", "MONITOR", "SUSPICIOUS", "RESTRICT"]
    return [
        {"node_id": f"node-{i}", "threat_level": random.choice(levels)}
        for i in range(1, 8)
    ]

@app.get("/api/queue/pending")
def pending_approvals():
    return [
        {
            "request_id": f"req-{i}",
            "node_id": f"node-{i}",
            "strategy": "restart",
            "reason": "High load detected",
        }
        for i in range(1, 3)
    ]
