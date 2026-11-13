import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Clock, AlertTriangle, CheckCircle2, Plus } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, errMsg } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, Kpi, Loading, Notice, renderCell } from "@/components/Common";
import { Frame } from "@/components/Frame";
import { fmtDT } from "@/lib/fmt";

const ICONS = [FileText, Clock, AlertTriangle, CheckCircle2];
const TONE_COLOR = { info: "#3976d5", pending: "#efbd59", urgent: "#d0606b", blocked: "#e39a4b", done: "#46a394", muted: "#c3ccd9" };
const TONE_LABEL = { info: "In progress", pending: "Awaiting response", urgent: "Urgent", blocked: "Blocked / waiting", done: "Completed", muted: "Closed other" };

function Inbox({ inbox }) {
  const nav = useNavigate();
  const { wf, roles } = useMeta();
  const groups = Object.entries(inbox || {}).filter(([, v]) => v.length);
  return (
    <Card title="My inbox" sub="Approvals and assigned work awaiting you" testid="dashboard-inbox">
      {!groups.length && <div className="ce-muted">Nothing is waiting for you.</div>}
      {groups.map(([k, items]) => (
        <div key={k} className="mb-3">
          <div className="ce-eyebrow mt-2">{k === "approvals" ? "Approvals for your authority" : wf[k]?.label}</div>
          {items.slice(0, 6).map((r) => (
            <div key={r.id} className="ce-kv cursor-pointer hover:bg-slate-50 px-1 rounded" onClick={() => nav(`/app/r/${r.id}`)} data-testid={`inbox-item-${r.ref}`}>
              <span><b className="ce-mono text-blue-700 font-semibold">{r.ref}</b> {r.title}</span>
              <b>{r.amount != null ? `INR ${Number(r.amount).toLocaleString("en-IN")}` : r.required_role ? roles[r.required_role]?.name.split(" /")[0] : renderCell(r, "state", wf)}</b>
            </div>
          ))}
        </div>
      ))}
    </Card>
  );
}

export default function Dashboard({ screen }) {
  const { user } = useAuth();
  const m = useMeta();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [inbox, setInbox] = useState(null);
  const [err, setErr] = useState("");
  const staff = !["R01", "R02", "R03"].includes(user.active_role);
  useEffect(() => {
    api.get("/dashboard").then((r) => setD(r.data)).catch((e) => setErr(errMsg(e)));
    if (staff) api.get("/inbox").then((r) => setInbox(r.data)).catch(() => setInbox({}));
  }, [staff, user.active_role]);
  const target = (t) => m.roleScreens.find((s) => s.t === t && ["list", "kanban"].includes(s.kind)) || m.roleScreens.find((s) => s.t === t && s.kind === "record");
  const creates = m.roleScreens.filter((s) => s.kind === "create").slice(0, 3);
  const dist = d ? Object.entries(d.distribution).map(([k, v]) => ({ name: TONE_LABEL[k] || k, value: v, color: TONE_COLOR[k] || "#999" })) : [];
  const cols = [{ key: "ref", label: "Reference" }, { key: "title", label: "Title" }, { key: "state", label: "State", render: (r) => renderCell(r, "state", m.wf) }, { key: "sla_state", label: "SLA", render: (r) => renderCell(r, "sla_state", m.wf) }, { key: "updated_at", label: "Updated", render: (r) => fmtDT(r.updated_at) }];
  return (
    <Frame screen={screen} sub={`Welcome back, ${user.name.split(" ")[0]}. ${m.roleInfo?.scope}.`}
      actions={<>{d?.demo_records > 0 && <Badge tone="outline" testid="demo-tag">Includes demo data</Badge>}{creates.map((s, i) => <button key={s.id} className={`ce-btn ${i === 0 ? "primary" : ""}`} onClick={() => nav(`/app/s/${s.id}`)} data-testid={`quick-${s.id}`}><Plus />{s.title}</button>)}</>}>
      {err && <Notice tone="red">{err}</Notice>}
      {!d ? <Card><Loading /></Card> : (
        <>
          <div className="ce-kpis" data-testid="dashboard-kpis">
            {d.kpis.map((k, i) => {
              const t = k.type && target(k.type);
              return <Kpi key={k.label} label={k.label} value={k.value} sub={k.sub} icon={ICONS[i % 4]} testid={`kpi-${i}`} style={{ animationDelay: `${i * 60}ms` }} onClick={() => t && nav(`/app/s/${t.id}`)} />;
            })}
          </div>
          <div className="ce-two">
            <Card title="Activity in the last 7 days" sub={`${m.wf[d.primary]?.label} records created and completed`} testid="dashboard-trend">
              <div style={{ height: 230 }}>
                <ResponsiveContainer>
                  <AreaChart data={d.series} margin={{ left: -20, right: 8, top: 8 }}>
                    <defs><linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3976d5" stopOpacity={0.25} /><stop offset="100%" stopColor="#3976d5" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid stroke="#eef2f7" vertical={false} /><XAxis dataKey="day" tick={{ fontSize: 11, fill: "#8590a2" }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#8590a2" }} axisLine={false} tickLine={false} /><Tooltip />
                    <Area type="monotone" dataKey="created" stroke="#3976d5" strokeWidth={2} fill="url(#g1)" name="Created" /><Area type="monotone" dataKey="completed" stroke="#46a394" strokeWidth={2} fill="transparent" name="Completed" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="Work by status" sub={`${d.total} ${m.wf[d.primary]?.label.toLowerCase()} records in scope`} testid="dashboard-distribution">
              <div className="flex items-center gap-4">
                <div style={{ width: 150, height: 150 }}>
                  <ResponsiveContainer><PieChart><Pie data={dist} dataKey="value" innerRadius={48} outerRadius={70} paddingAngle={2}>{dist.map((x) => <Cell key={x.name} fill={x.color} />)}</Pie></PieChart></ResponsiveContainer>
                </div>
                <div className="flex-1">{dist.map((x) => <div key={x.name} className="ce-kv"><span><span className="ce-dot mr-2" style={{ background: x.color }} />{x.name}</span><b>{x.value}</b></div>)}{!dist.length && <div className="ce-muted">No records yet.</div>}</div>
              </div>
            </Card>
          </div>
          <div className={staff ? "ce-two" : ""}>
            <Card title="Recently updated open work" testid="dashboard-recent"><DataTable cols={cols} rows={d.table} onRow={(r) => nav(`/app/r/${r.id}`)} testid="dashboard-table" /></Card>
            {staff && <Inbox inbox={inbox} />}
          </div>
        </>
      )}
    </Frame>
  );
}
