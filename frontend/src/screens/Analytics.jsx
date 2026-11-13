import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Download, Sparkles, Loader2, FileDown } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, errMsg, downloadFile } from "@/lib/api";
import { useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, Kpi, Loading, Notice } from "@/components/Common";
import { Frame } from "@/components/Frame";
import { fmtDT, inr } from "@/lib/fmt";

const COLORS = ["#3976d5", "#46a394", "#efbd59", "#d0606b", "#8a7bd6", "#9db9e3"];
const pct = (v) => (v == null ? "Not enough data" : `${v}%`);
const num = (v, u = "") => (v == null ? "Not enough data" : `${v}${u}`);

function Bars({ data, k = "value", name = "name", height = 230 }) {
  if (!data?.length) return <div className="ce-muted">Not enough data in this period.</div>;
  return <div style={{ height }}><ResponsiveContainer><BarChart data={data} margin={{ left: -20 }}><CartesianGrid stroke="#eef2f7" vertical={false} /><XAxis dataKey={name} tick={{ fontSize: 10 }} interval={0} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey={k} fill="#3976d5" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>;
}

function Product({ a }) {
  return (
    <>
      <div className="ce-kpis">
        <Kpi label="Safety incidents" value={a.quality.safety_incidents} sub="In period" testid="kpi-safety" />
        <Kpi label="Repeat failures" value={a.quality.repeat_failures} sub="Technical reviews with prior repairs" testid="kpi-repeat" />
        <Kpi label="CAPA verified" value={pct(a.quality.capa_progress_pct)} sub="Effectiveness verified" testid="kpi-capa" />
        <Kpi label="Parts availability" value={pct(a.quality.parts_availability_pct)} sub="Stock lines with available units" testid="kpi-parts" />
      </div>
      <div className="ce-two">
        <Card title="Complaints by product"><Bars data={a.quality.product_issues} /></Card>
        <Card title="Warranty outcomes">{!a.quality.warranty.length ? <div className="ce-muted">No warranty decisions yet.</div> :
          <div style={{ height: 230 }}><ResponsiveContainer><PieChart><Pie data={a.quality.warranty} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>{a.quality.warranty.map((x, i) => <Cell key={x.name} fill={COLORS[i % 6]} />)}</Pie><Legend /><Tooltip /></PieChart></ResponsiveContainer></div>}</Card>
      </div>
    </>
  );
}

function Performance({ a }) {
  const s = a.service;
  return (
    <>
      <div className="ce-kpis">
        <Kpi label="SLA compliance" value={pct(s.sla_compliance_pct)} sub={`${s.sla_breaches} breaches`} testid="kpi-sla" />
        <Kpi label="First response" value={num(s.first_response_min, " min")} sub="Average" testid="kpi-first-response" />
        <Kpi label="Average resolution" value={num(s.avg_resolution_h, " h")} sub="Closed cases" testid="kpi-resolution" />
        <Kpi label="First-time fix" value={pct(s.first_time_fix_pct)} sub={`Appointment adherence ${pct(s.appointment_adherence_pct)}`} testid="kpi-ftf" />
      </div>
      <Card title="Cases created and closed (14 days)"><div style={{ height: 240 }}><ResponsiveContainer><LineChart data={a.trend} margin={{ left: -20 }}><CartesianGrid stroke="#eef2f7" vertical={false} /><XAxis dataKey="day" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Legend /><Line dataKey="created" stroke="#3976d5" strokeWidth={2} name="Created" /><Line dataKey="closed" stroke="#46a394" strokeWidth={2} name="Closed" /></LineChart></ResponsiveContainer></div></Card>
      <div className="ce-two equal">
        <Card title="Open and breached by region"><div style={{ height: 220 }}><ResponsiveContainer><BarChart data={a.by_region} margin={{ left: -20 }}><CartesianGrid stroke="#eef2f7" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="open" fill="#3976d5" name="Open" /><Bar dataKey="breached" fill="#d0606b" name="Breached" /></BarChart></ResponsiveContainer></div></Card>
        <Card title="Centre backlog"><Bars data={s.centre_backlog} height={220} /></Card>
      </div>
      <Card title="Engineer productivity (accepted jobs)"><DataTable rows={s.technician_productivity} cols={[{ key: "name", label: "Engineer" }, { key: "value", label: "Accepted jobs" }]} testid="productivity-table" /></Card>
    </>
  );
}

function Costs({ a }) {
  const q = a.quality;
  return (
    <>
      <div className="ce-kpis">
        <Kpi label="Remedy exposure" value={inr(q.exposure_inr)} sub="Pending and approved remedies" testid="kpi-exposure" />
        <Kpi label="Settled" value={inr(q.settled_inr)} sub="Executed settlements" testid="kpi-settled" />
        <Kpi label="Settlement turnaround" value={num(q.settlement_turnaround_h, " h")} sub="Approval to execution" testid="kpi-turnaround" />
        <Kpi label="Pending approvals" value={a.operational.pending_approvals} sub="All approval types" testid="kpi-approvals" />
      </div>
      <Card title="Exposure by remedy type"><Bars data={q.exposure_by_type} /></Card>
      <Notice tone="gray">Financial figures are derived from recorded approvals and settlements. The payment provider is SIMULATED in this environment - no real funds move.</Notice>
    </>
  );
}

export function Analytics({ screen: s }) {
  const { role } = useMeta();
  const [frm, setFrm] = useState("");
  const [to, setTo] = useState("");
  const [region, setRegion] = useState("");
  const [a, setA] = useState(null);
  const [err, setErr] = useState("");
  const [ai, setAi] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get("/analytics", { params: { frm: frm || undefined, to: to || undefined, region: region || undefined } }).then((r) => { setA(r.data); setErr(""); }).catch((e) => setErr(errMsg(e))), [frm, to, region]);
  useEffect(() => { load(); }, [load]);
  const trend = async () => {
    setBusy(true);
    try { const { data } = await api.post("/ai/assist", { task: "trend", text: JSON.stringify({ operational: a.operational, service: { ...a.service, technician_productivity: undefined }, by_region: a.by_region }) }); setAi(data); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const o = a?.operational;
  return (
    <Frame screen={s} actions={<button className="ce-btn" disabled={!a || busy} onClick={trend} data-testid="ai-trend-btn">{busy ? <Loader2 className="animate-spin" /> : <Sparkles />}AI trend summary</button>}>
      <Card>
        <div className="flex gap-3 flex-wrap items-end">
          <div className="ce-field"><label>From</label><input className="ce-input" type="date" value={frm} onChange={(e) => setFrm(e.target.value)} data-testid="analytics-from" /></div>
          <div className="ce-field"><label>To</label><input className="ce-input" type="date" value={to} onChange={(e) => setTo(e.target.value)} data-testid="analytics-to" /></div>
          {role !== "R09" && <div className="ce-field"><label>Region</label><select className="ce-input" value={region} onChange={(e) => setRegion(e.target.value)} data-testid="analytics-region"><option value="">All regions</option>{["North", "South", "East", "West"].map((r) => <option key={r}>{r}</option>)}</select></div>}
          {a && <div className="ce-muted ml-auto">Generated {fmtDT(a.generated_at)} · aggregated data only{a.demo_records ? ` · ${a.demo_records} demo cases included` : ""}</div>}
        </div>
      </Card>
      {err && <Notice tone="red">{err}</Notice>}
      {ai && <Notice tone="blue" title="AI trend summary - unverified, review before sharing" testid="ai-trend-result">{ai.output?.summary} {(ai.output?.notable || []).join(" · ")}</Notice>}
      {!a ? <Card><Loading /></Card> : (
        <>
          <div className="flex gap-2 flex-wrap mb-4" data-testid="ops-strip">
            {[["Open", o.open], ["New (7d)", o.new], ["Overdue", o.overdue], ["Unassigned", o.unassigned], ["Escalated", o.escalated], ["Reopened", o.reopened], ["Resolved", o.resolved], ["Closed", o.closed]].map(([l, v]) => <Badge key={l} tone="outline">{l}: <b>{v}</b></Badge>)}
            {a.customer.csat_avg != null && <Badge tone="green">CSAT {a.customer.csat_avg}/5</Badge>}
            {a.hr_open_aggregate != null && <Badge tone="gray">Confidential HR (aggregate only): {a.hr_open_aggregate}</Badge>}
          </div>
          {s.variant === "product" && <Product a={a} />}
          {s.variant === "performance" && <Performance a={a} />}
          {s.variant === "costs" && <Costs a={a} />}
        </>
      )}
    </Frame>
  );
}

export function Exports({ screen: s }) {
  const { role } = useMeta();
  const [items, setItems] = useState(null);
  const [scope, setScope] = useState("analytics");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get("/exports").then((r) => setItems(r.data.items)).catch((e) => toast.error(errMsg(e))), []);
  useEffect(() => { load(); }, [load]);
  const scopes = [["analytics", "Aggregated analytics"], ["records:case", "Case register (scoped)"], ["records:incident", "Safety incident register"], ...(["R18", "R21"].includes(role) ? [["audit", "Audit history"]] : [])];
  const req = async () => { setBusy(true); try { await api.post("/exports", { scope }); toast.success("Export generated with watermark"); load(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); } };
  return (
    <Frame screen={s}>
      <Card title="Request a governed export" sub="Exports are watermarked, scoped to your access, logged and expire after 7 days">
        <div className="flex gap-2 flex-wrap">
          <select className="ce-input" style={{ maxWidth: 320 }} value={scope} onChange={(e) => setScope(e.target.value)} data-testid="export-scope">{scopes.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
          <button className="ce-btn primary" disabled={busy} onClick={req} data-testid="export-request-btn"><FileDown />Generate export</button>
        </div>
      </Card>
      <Card title="My exports">{!items ? <Loading /> : <DataTable rows={items} testid="exports-table" cols={[{ key: "scope", label: "Scope" }, { key: "at", label: "Generated", render: (e) => fmtDT(e.at) }, { key: "expires_at", label: "Expires", render: (e) => fmtDT(e.expires_at) }, { key: "watermark", label: "Watermark" },
        { key: "x", label: "", render: (e) => <button className="ce-btn sm" onClick={() => downloadFile(`/exports/${e.id}/download`, `${e.id}.csv`).catch((x) => toast.error(errMsg(x)))} data-testid={`export-download-${e.id}`}><Download />CSV</button> }]} />}</Card>
    </Frame>
  );
}
