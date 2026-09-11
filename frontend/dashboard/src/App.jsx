import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Activity, Shield, Server, AlertTriangle, CheckCircle, XCircle, Clock } from "lucide-react";
import axios from "axios";

const API = "http://localhost:8000";

const COLORS = {
  healthy: "#22c55e",
  failed: "#ef4444",
  recovering: "#f59e0b",
  up: "#22c55e",
  down: "#ef4444",
  NORMAL: "#22c55e",
  MONITOR: "#3b82f6",
  SUSPICIOUS: "#f59e0b",
  RESTRICT: "#ef4444",
  QUARANTINE: "#7c3aed",
};

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 12, padding: 20, flex: 1, minWidth: 150 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <Icon size={20} color={color} />
        <span style={{ color: "#94a3b8", fontSize: 13 }}>{label}</span>
      </div>
      <div style={{ fontSize: 32, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState(null);
  const [recoveries, setRecoveries] = useState([]);
  const [services, setServices] = useState([]);
  const [threats, setThreats] = useState([]);
  const [queue, setQueue] = useState([]);

  const fetchAll = async () => {
    try {
      const [s, r, sv, t, q] = await Promise.all([
        axios.get(`${API}/api/network/status`),
        axios.get(`${API}/api/recovery/recent`),
        axios.get(`${API}/api/services/resilience`),
        axios.get(`${API}/api/security/threat-levels`),
        axios.get(`${API}/api/queue/pending`),
      ]);
      setStatus(s.data);
      setRecoveries(r.data);
      setServices(sv.data);
      setThreats(t.data);
      setQueue(q.data);
    } catch (e) {
      console.error("API error", e);
    }
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#f1f5f9", fontFamily: "system-ui, sans-serif", padding: 24 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <Shield size={28} color="#6366f1" />
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Sentinel Star X — Command Center</h1>
        <span style={{ marginLeft: "auto", color: "#64748b", fontSize: 12 }}>Auto-refresh: 5s</span>
      </div>

      {/* Stat Cards */}
      {status && (
        <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
          <StatCard icon={Server} label="Total Nodes" value={status.total_nodes} color="#6366f1" />
          <StatCard icon={CheckCircle} label="Healthy" value={status.healthy_nodes} color={COLORS.healthy} />
          <StatCard icon={XCircle} label="Failed" value={status.failed_nodes} color={COLORS.failed} />
          <StatCard icon={Clock} label="Recovering" value={status.recovering_nodes} color={COLORS.recovering} />
          <StatCard icon={Activity} label="Health Score" value={`${status.overall_health}%`} color="#6366f1" />
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        {/* Recent Recoveries */}
        <div style={{ background: "#1e293b", borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: "#e2e8f0" }}>Recent Recoveries</h2>
          {recoveries.map((r, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #334155" }}>
              <span style={{ color: "#94a3b8", fontSize: 13 }}>{r.node_id}</span>
              <span style={{ background: "#334155", borderRadius: 6, padding: "2px 8px", fontSize: 12 }}>{r.strategy}</span>
              <span style={{ color: r.success ? COLORS.healthy : COLORS.failed, fontSize: 13 }}>{r.success ? "✓ Success" : "✗ Failed"}</span>
              <span style={{ color: "#64748b", fontSize: 12 }}>{r.duration_seconds}s</span>
            </div>
          ))}
        </div>

        {/* Service Resilience */}
        <div style={{ background: "#1e293b", borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: "#e2e8f0" }}>Service Resilience</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={services}>
              <XAxis dataKey="service" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "none", borderRadius: 8 }} />
              <Bar dataKey="uptime_percent" radius={[4, 4, 0, 0]}>
                {services.map((s, i) => (
                  <Cell key={i} fill={s.is_up ? COLORS.healthy : COLORS.failed} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Threat Levels */}
        <div style={{ background: "#1e293b", borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: "#e2e8f0" }}>
            <AlertTriangle size={16} style={{ marginRight: 8, verticalAlign: "middle" }} />
            Threat Levels
          </h2>
          {threats.map((t, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #334155" }}>
              <span style={{ color: "#94a3b8", fontSize: 13 }}>{t.node_id}</span>
              <span style={{ color: COLORS[t.threat_level] || "#94a3b8", fontWeight: 600, fontSize: 13 }}>{t.threat_level}</span>
            </div>
          ))}
        </div>

        {/* Pending Approvals */}
        <div style={{ background: "#1e293b", borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, color: "#e2e8f0" }}>
            <Clock size={16} style={{ marginRight: 8, verticalAlign: "middle" }} />
            Pending Approvals ({queue.length})
          </h2>
          {queue.length === 0 ? (
            <p style={{ color: "#64748b", fontSize: 13 }}>No pending approvals</p>
          ) : queue.map((q, i) => (
            <div key={i} style={{ background: "#0f172a", borderRadius: 8, padding: 12, marginBottom: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{q.node_id} — {q.strategy}</div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{q.reason}</div>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button style={{ background: COLORS.healthy, color: "#fff", border: "none", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontSize: 12 }}>Approve</button>
                <button style={{ background: COLORS.failed, color: "#fff", border: "none", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontSize: 12 }}>Reject</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
