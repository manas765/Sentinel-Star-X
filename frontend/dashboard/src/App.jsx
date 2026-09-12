import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://localhost:8000";

const GATE_COLOR = { PROCEED: "#22c55e", BLOCKED: "#7c3aed", HOLD: "#f59e0b", MANUAL: "#ef4444" };
const TRUST_COLOR = { NORMAL: "#22c55e", MONITOR: "#3b82f6", SUSPICIOUS: "#f59e0b", RESTRICT: "#ef4444", QUARANTINE: "#7c3aed", EMERGENCY: "#dc2626" };
const STRATEGY_COLOR = { reroute: "#6366f1", failover: "#3b82f6", restart: "#f59e0b", isolate: "#ef4444" };

function Dot({ color, blink, ping }) {
  return (
    <div style={{ position: "relative", width: 9, height: 9, flexShrink: 0 }}>
      <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: color, animation: blink ? "blink 1.5s infinite" : ping ? "pulse 2s infinite" : "none" }} />
      {ping && <div style={{ position: "absolute", inset: 0, borderRadius: "50%", background: color, animation: "ping 2s infinite" }} />}
    </div>
  );
}

function Tag({ label, color }) {
  return <span style={{ fontSize: 11, color, background: color + "18", border: `1px solid ${color}30`, borderRadius: 4, padding: "3px 10px", fontWeight: 700, letterSpacing: "0.04em" }}>{label}</span>;
}

function Bar({ pct, color }) {
  return (
    <div style={{ background: "#0f1015", borderRadius: 2, height: 3, overflow: "hidden" }}>
      <div style={{ background: color, height: 3, width: `${pct}%`, transition: "width 1.2s ease" }} />
    </div>
  );
}

function KpiCard({ label, value, color, sub }) {
  return (
    <div style={{ background: "#111318", border: "1px solid #1a1a2e", borderRadius: 12, padding: "24px 28px" }}>
      <div style={{ fontSize: 11, color: "#374151", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 14, fontWeight: 600 }}>{label}</div>
      <div style={{ fontSize: 36, fontWeight: 800, color, letterSpacing: "-0.03em", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#2a2f3e", marginTop: 10 }}>{sub}</div>
    </div>
  );
}

function Panel({ title, badge, dot, dotColor, children }) {
  return (
    <div style={{ background: "#111318", border: "1px solid #1a1a2e", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "16px 24px", borderBottom: "1px solid #1a1a2e", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {dot && <Dot color={dotColor} blink={dotColor === "#ef4444"} ping={dotColor === "#22c55e"} />}
          <span style={{ fontSize: 14, fontWeight: 700, color: "#e2e8f0", letterSpacing: "-0.01em" }}>{title}</span>
        </div>
        {badge && <span style={{ fontSize: 10, color: "#374151", background: "#0d0d0f", border: "1px solid #1a1a2e", borderRadius: 4, padding: "3px 10px", letterSpacing: "0.04em" }}>{badge}</span>}
      </div>
      <div style={{ padding: "20px 24px" }}>{children}</div>
    </div>
  );
}

function Spinner() {
  return <div style={{ width: 14, height: 14, border: "2px solid #22c55e", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 1s linear infinite", flexShrink: 0 }} />;
}

function SectionLabel({ text }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16, margin: "40px 0 20px" }}>
      <div style={{ flex: 1, height: 1, background: "#111318" }} />
      <span style={{ fontSize: 11, color: "#1f2937", letterSpacing: "0.12em", fontWeight: 700 }}>{text}</span>
      <div style={{ flex: 1, height: 1, background: "#111318" }} />
    </div>
  );
}

export default function App() {
  const [status, setStatus]     = useState(null);
  const [trust, setTrust]       = useState([]);
  const [active, setActive]     = useState(null);
  const [recent, setRecent]     = useState([]);
  const [decision, setDecision] = useState(null);
  const [services, setServices] = useState([]);
  const [queue, setQueue]       = useState([]);
  const [approved, setApproved] = useState({});
  const [time, setTime]         = useState("");

  const fetchAll = async () => {
    try {
      const [s, t, a, r, d, sv, q] = await Promise.all([
        axios.get(`${API}/api/network/status`),
        axios.get(`${API}/api/trust/levels`),
        axios.get(`${API}/api/recovery/active`),
        axios.get(`${API}/api/recovery/recent`),
        axios.get(`${API}/api/decision/latest`),
        axios.get(`${API}/api/services/resilience`),
        axios.get(`${API}/api/queue/pending`),
      ]);
      setStatus(s.data); setTrust(t.data); setActive(a.data);
      setRecent(r.data); setDecision(d.data); setServices(sv.data); setQueue(q.data);
      setTime(new Date().toLocaleTimeString("en-GB", { hour12: false }) + " UTC");
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchAll(); const i = setInterval(fetchAll, 5000); return () => clearInterval(i); }, []);

  const decide = (id, val) => setApproved(p => ({ ...p, [id]: val }));

  return (
    <div style={{ background: "#0d0d0f", minHeight: "100vh", fontFamily: "'Inter',system-ui,sans-serif", color: "#e2e8f0", scrollBehavior: "smooth" }}>
      <style>{`
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0d0d0f; }
        ::-webkit-scrollbar-thumb { background: #1a1a2e; border-radius: 3px; }
        @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.6)}}
        @keyframes ping{0%{transform:scale(1);opacity:.7}100%{transform:scale(2.6);opacity:0}}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}
        @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
        @keyframes scan{0%{top:-4px}100%{top:100%}}
        @keyframes fadein{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        @keyframes slideup{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
      `}</style>

      {/* Background grid */}
      <div style={{ position: "fixed", inset: 0, backgroundImage: "linear-gradient(#ffffff03 1px,transparent 1px),linear-gradient(90deg,#ffffff03 1px,transparent 1px)", backgroundSize: "40px 40px", pointerEvents: "none", zIndex: 0 }} />
      <div style={{ position: "fixed", left: 0, right: 0, height: 1, background: "linear-gradient(90deg,transparent,#6366f120,transparent)", animation: "scan 8s linear infinite", pointerEvents: "none", zIndex: 1 }} />

      <div style={{ position: "relative", zIndex: 2 }}>

        {/* Nav */}
        <div style={{ background: "#0a0a0cee", backdropFilter: "blur(12px)", borderBottom: "1px solid #1a1a2e", padding: "0 40px", display: "flex", alignItems: "center", justifyContent: "space-between", height: 52, position: "sticky", top: 0, zIndex: 100 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 22, height: 22, background: "#6366f1", borderRadius: 5, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800 }}>⬡</div>
              <span style={{ fontSize: 15, fontWeight: 800, letterSpacing: "-0.03em" }}>Sentinel Star X</span>
              <span style={{ fontSize: 10, color: "#555", background: "#111", border: "1px solid #1a1a1a", borderRadius: 4, padding: "2px 8px", letterSpacing: "0.06em", fontWeight: 600 }}>AIOps</span>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {["Overview", "Recovery", "Security", "Nodes", "Experiments"].map((t, i) => (
                <div key={t} style={{ padding: "5px 14px", fontSize: 12, fontWeight: i === 0 ? 700 : 500, color: i === 0 ? "#a5b4fc" : "#444", background: i === 0 ? "#6366f115" : "transparent", borderRadius: 5, cursor: "pointer" }}>{t}</div>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Dot color="#22c55e" ping />
              <span style={{ fontSize: 12, color: "#4b5563", fontWeight: 500 }}>Live · 5s refresh</span>
            </div>
            <span style={{ fontSize: 11, color: "#222", fontFamily: "monospace" }}>{time}</span>
          </div>
        </div>

        <div style={{ padding: "40px 40px 80px", maxWidth: 1400, margin: "0 auto" }}>

          {/* Page title */}
          <div style={{ marginBottom: 40, animation: "slideup .6s ease both" }}>
            <div style={{ fontSize: 11, color: "#374151", letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 10, fontWeight: 600 }}>Autonomous Network Resilience Platform</div>
            <div style={{ fontSize: 42, fontWeight: 900, letterSpacing: "-0.04em", lineHeight: 1, color: "#f1f5f9" }}>Command Center</div>
            <div style={{ fontSize: 15, color: "#374151", marginTop: 10 }}>Real-time monitoring · Trust gating · Autonomous self-healing</div>
          </div>

          {/* KPI Row */}
          {status && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 12, marginBottom: 0, animation: "fadein .5s .1s ease both", opacity: 0, animationFillMode: "both" }}>
              <KpiCard label="Network Health"    value={`${status.overall_health}%`} color="#22c55e" sub="↑ 3% from last hour" />
              <KpiCard label="Nodes Online"      value={`${status.healthy_nodes} / ${status.total_nodes}`} color="#f1f5f9" sub={`${status.failed_nodes + status.recovering_nodes} degraded`} />
              <KpiCard label="Active Recoveries" value={status.recovering_nodes}     color="#f59e0b" sub="reroute in progress" />
              <KpiCard label="Trust Gate Blocks" value="2"                            color="#ef4444" sub="quarantine hold active" />
              <KpiCard label="Decisions Today"   value="14"                           color="#6366f1" sub="12 auto · 2 manual" />
            </div>
          )}

          <SectionLabel text="CORE SYSTEMS" />

          {/* Trust Gate + Self Healing */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16, animation: "fadein .5s .2s ease both", animationFillMode: "both" }}>

            {/* Trust Gate */}
            <Panel title="Trust Gate" badge="Manas · Security" dot dotColor="#ef4444">
              {/* Flow */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24, overflowX: "auto", paddingBottom: 4 }}>
                {[["Node", "#6366f1"], ["Trust Check", "#f59e0b"], ["Gate Decision", "#ef4444"], ["Recovery Engine", "#22c55e"]].map(([l, c], i) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                    <div style={{ background: c + "15", border: `1px solid ${c}35`, borderRadius: 7, padding: "8px 14px" }}>
                      <div style={{ fontSize: 11, color: c, fontWeight: 700, whiteSpace: "nowrap" }}>{l}</div>
                    </div>
                    {i < 3 && <div style={{ fontSize: 14, color: "#1f2937" }}>→</div>}
                  </div>
                ))}
              </div>
              {/* Nodes */}
              {trust.map(({ node_id, trust_level, gate }) => {
                const tc = TRUST_COLOR[trust_level] || "#6b7280";
                const gc = GATE_COLOR[gate] || "#6b7280";
                const pct = gate === "PROCEED" ? 100 : gate === "BLOCKED" ? 15 : gate === "HOLD" ? 45 : 60;
                return (
                  <div key={node_id} style={{ display: "grid", gridTemplateColumns: "80px 120px 1fr 90px", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #111318", gap: 12 }}>
                    <span style={{ fontSize: 13, color: "#4b5563", fontFamily: "monospace", fontWeight: 600 }}>{node_id}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Dot color={tc} blink={trust_level === "QUARANTINE" || trust_level === "RESTRICT"} />
                      <span style={{ fontSize: 11, color: tc, fontWeight: 700, letterSpacing: "0.04em" }}>{trust_level}</span>
                    </div>
                    <Bar pct={pct} color={gc} />
                    <span style={{ fontSize: 12, fontWeight: 800, textAlign: "right", color: gc, letterSpacing: "0.04em" }}>{gate}</span>
                  </div>
                );
              })}
            </Panel>

            {/* Self Healing */}
            <Panel title="Autonomous Self-Healing" badge="Aakash · Recovery" dot dotColor="#22c55e">
              {active && (
                <div style={{ background: "#0a0a0c", border: "1px solid #1a2e1a", borderRadius: 8, padding: 18, marginBottom: 20, borderLeft: "3px solid #22c55e" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <Spinner />
                      <span style={{ fontSize: 14, color: "#22c55e", fontWeight: 800, letterSpacing: "-0.01em" }}>{active.node_id} · {active.strategy}ing</span>
                    </div>
                    <span style={{ fontSize: 12, color: "#374151", fontWeight: 500 }}>{active.elapsed_seconds}s elapsed</span>
                  </div>
                  <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
                    {active.stages.map(({ name, status }) => (
                      <div key={name} style={{ flex: 1 }}>
                        <div style={{ height: 4, background: status === "pending" ? "#1a1a2e" : "#22c55e", borderRadius: 2, marginBottom: 6, opacity: status === "active" ? 0.6 : 1, animation: status === "active" ? "blink 1s infinite" : "none" }} />
                        <div style={{ fontSize: 11, color: status === "pending" ? "#1f2937" : "#22c55e", textAlign: "center", fontWeight: 600 }}>{name}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: "#374151", fontWeight: 500 }}>Decision Engine chose <span style={{ color: "#6366f1" }}>reroute</span> · confidence <span style={{ color: "#22c55e" }}>{active.confidence}%</span> · cost score {active.cost_score}/100</div>
                </div>
              )}
              <div style={{ fontSize: 11, color: "#374151", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 700, marginBottom: 14 }}>Recent heals</div>
              {recent.map(({ node_id, strategy, success, trust, time }) => (
                <div key={node_id} style={{ display: "grid", gridTemplateColumns: "80px 90px 24px 1fr 70px", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #111318", gap: 12 }}>
                  <span style={{ fontSize: 13, color: "#4b5563", fontFamily: "monospace", fontWeight: 600 }}>{node_id}</span>
                  <Tag label={strategy} color={STRATEGY_COLOR[strategy] || "#6b7280"} />
                  <span style={{ fontSize: 16, color: success ? "#22c55e" : "#ef4444", fontWeight: 800 }}>{success ? "✓" : "✗"}</span>
                  <span style={{ fontSize: 11, color: "#374151", fontWeight: 500 }}>trust: <span style={{ color: TRUST_COLOR[trust] }}>{trust}</span></span>
                  <span style={{ fontSize: 11, color: "#1f2937", textAlign: "right" }}>{time}</span>
                </div>
              ))}
            </Panel>
          </div>

          <SectionLabel text="NETWORK · SERVICES · DECISIONS" />

          {/* Bottom row */}
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 0.85fr", gap: 16, marginBottom: 0, animation: "fadein .5s .3s ease both", animationFillMode: "both" }}>

            {/* Nodes */}
            <Panel title="Node Topology" badge="12 nodes">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 14, marginBottom: 20 }}>
                {Array.from({ length: 12 }, (_, i) => {
                  const s = i < 9 ? "healthy" : i < 11 ? "failed" : "recovering";
                  const c = { healthy: "#22c55e", failed: "#ef4444", recovering: "#f59e0b" }[s];
                  return (
                    <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                      <Dot color={c} blink={s === "failed"} ping={s === "recovering"} />
                      <span style={{ fontSize: 10, color: "#1f2937", fontFamily: "monospace", fontWeight: 600 }}>{i + 1}</span>
                    </div>
                  );
                })}
              </div>
              <div style={{ display: "flex", gap: 20 }}>
                {[["#22c55e", "Online (9)"], ["#ef4444", "Failed (2)"], ["#f59e0b", "Healing (1)"]].map(([c, l]) => (
                  <div key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#374151", fontWeight: 500 }}>
                    <div style={{ width: 7, height: 7, borderRadius: "50%", background: c }} />{l}
                  </div>
                ))}
              </div>
            </Panel>

            {/* Services */}
            <Panel title="Service Resilience">
              {services.map(({ service, uptime_percent, is_up }) => (
                <div key={service} style={{ marginBottom: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: "#6b7280", fontFamily: "monospace", fontWeight: 600 }}>{service}</span>
                    <span style={{ fontSize: 13, color: is_up ? "#22c55e" : "#ef4444", fontWeight: 700 }}>{uptime_percent}%</span>
                  </div>
                  <Bar pct={uptime_percent} color={is_up ? "#22c55e" : "#ef4444"} />
                </div>
              ))}
            </Panel>

            {/* Decision Engine */}
            <Panel title="Decision Engine" badge="Multi-objective">
              {decision && (
                <>
                  <div style={{ fontSize: 12, color: "#374151", marginBottom: 16, fontWeight: 500 }}>Last decision · <span style={{ color: "#6366f1", fontWeight: 700 }}>{decision.node_id}</span></div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 24 }}>
                    {decision.scores.map(({ strategy, score, color }) => (
                      <div key={strategy}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                          <span style={{ fontSize: 12, color: "#4b5563", fontWeight: 600 }}>{strategy}</span>
                          <span style={{ fontSize: 12, color, fontWeight: 800 }}>{score}</span>
                        </div>
                        <Bar pct={score} color={color} />
                      </div>
                    ))}
                  </div>
                </>
              )}
              <div style={{ borderTop: "1px solid #1a1a2e", paddingTop: 16 }}>
                <div style={{ fontSize: 11, color: "#374151", letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 700, marginBottom: 12 }}>Pending approvals</div>
                {queue.map(({ request_id, node_id }) => (
                  <div key={request_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <span style={{ fontSize: 13, color: "#4b5563", fontFamily: "monospace", fontWeight: 600 }}>{node_id}</span>
                    {approved[request_id] ? (
                      <span style={{ fontSize: 12, color: approved[request_id] === "approved" ? "#22c55e" : "#ef4444", fontWeight: 700 }}>{approved[request_id] === "approved" ? "✓ approved" : "✗ rejected"}</span>
                    ) : (
                      <div style={{ display: "flex", gap: 6 }}>
                        <div onClick={() => decide(request_id, "approved")} style={{ fontSize: 11, color: "#22c55e", border: "1px solid #22c55e30", borderRadius: 4, padding: "4px 10px", cursor: "pointer", fontWeight: 700 }}>✓ Approve</div>
                        <div onClick={() => decide(request_id, "rejected")} style={{ fontSize: 11, color: "#ef4444", border: "1px solid #ef444430", borderRadius: 4, padding: "4px 10px", cursor: "pointer", fontWeight: 700 }}>✗ Reject</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          {/* Credits */}
          <div style={{ borderTop: "1px solid #111318", marginTop: 60, paddingTop: 32, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 24 }}>
            <div>
              <div style={{ fontSize: 11, color: "#1f2937", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 700, marginBottom: 6 }}>Created by</div>
              <div style={{ fontSize: 12, color: "#1a1a2e" }}>SRM Institute of Science and Technology · 2026</div>
            </div>
            <div style={{ display: "flex", gap: 28 }}>
              {[["Aakash Sairam", "Recovery · Platform", "#6366f1"], ["Manashvi Sharma", "Cybersecurity · Trust", "#ef4444"], ["Akshata Srivastava", "Network · Digital Twin", "#22c55e"], ["Pushkar Arun", "AI · Prediction", "#3b82f6"]].map(([name, role, color]) => (
                <div key={name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: color + "18", border: `1px solid ${color}30`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800, color }}>{name[0]}</div>
                  <div>
                    <div style={{ fontSize: 13, color: "#6b7280", fontWeight: 700 }}>{name}</div>
                    <div style={{ fontSize: 11, color: "#1f2937", marginTop: 2 }}>{role}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
