import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Search, UserPlus, FilePlus2, Sparkles, Loader2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, errMsg, errFields } from "@/lib/api";
import { useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, Empty, Kpi, Loading, Notice } from "@/components/Common";
import { CreateDialog } from "@/components/ActionDialog";
import { Frame } from "@/components/Frame";
import { DynamicForm, validateFields } from "@/components/DynamicForm";
import { fmtDT, fmtD } from "@/lib/fmt";

const CUST_FIELDS = [{ k: "name", l: "Full name", req: true }, { k: "phone", l: "Mobile number", req: true, hint: "10 to 13 digits" }, { k: "email", l: "Email" }, { k: "pin", l: "PIN code", req: true, pattern: "^\\d{6}$", hint: "6 digit PIN code" }, { k: "address", l: "Address", t: "textarea" }];

function RegisterCustomer({ open, onClose, onDone }) {
  const [v, setV] = useState({});
  const [errs, setErrs] = useState({});
  const [err, setErr] = useState("");
  const save = async () => {
    const e = validateFields(CUST_FIELDS, v);
    setErrs(e);
    if (Object.keys(e).length) return;
    try { const { data } = await api.post("/customers", v); toast.success(`${data.name} registered`); onDone(data); } catch (x) { setErr(errMsg(x)); setErrs(errFields(x)); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl" data-testid="register-customer-dialog">
        <DialogHeader><DialogTitle>Register a new customer</DialogTitle></DialogHeader>
        <DynamicForm fields={CUST_FIELDS} values={v} setValues={setV} errors={errs} prefix="customer" />
        {err && <Notice tone="red">{err}</Notice>}
        <div className="ce-actions"><button className="ce-btn primary" onClick={save} data-testid="customer-save">Register customer</button></div>
      </DialogContent>
    </Dialog>
  );
}

export function CustomerSearch({ screen: s }) {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [res, setRes] = useState(null);
  const [reg, setReg] = useState(false);
  const [ticket, setTicket] = useState(null);
  const search = async (e) => { e?.preventDefault(); if (!q.trim()) return; try { const { data } = await api.get("/customers/search", { params: { q } }); setRes(data.items); } catch (x) { toast.error(errMsg(x)); } };
  return (
    <Frame screen={s} actions={<button className="ce-btn" onClick={() => setReg(true)} data-testid="register-customer-btn"><UserPlus />Register new customer</button>}>
      <Card>
        <form onSubmit={search} className="flex gap-2">
          <input className="ce-input" placeholder="Name, mobile number, email or product serial" value={q} onChange={(e) => setQ(e.target.value)} data-testid="customer-search-input" />
          <button className="ce-btn primary" data-testid="customer-search-btn"><Search />Search</button>
        </form>
      </Card>
      {res === null && <Card><Empty title={s.variant === "empty" ? "Search before creating a duplicate" : "Find the customer first"}>Search by mobile number, name, email or serial number. Linking to an existing customer keeps the full service history together.</Empty></Card>}
      {res && !res.length && (
        <Card testid="no-customer-found"><Empty title="No matching customer found">Check the spelling or try the mobile number. If this is a new customer, register them with verified contact details.</Empty>
          <div className="text-center"><button className="ce-btn primary" onClick={() => setReg(true)} data-testid="register-from-empty"><UserPlus />Register new customer</button></div></Card>
      )}
      {(res || []).map((c, i) => (
        <Card key={c.id} title={c.name} sub={`${c.phone} · ${c.email || "no email"} · ${c.region}`} testid={`customer-result-${i}`}
          right={<button className="ce-btn primary" onClick={() => setTicket(c)} data-testid={`create-ticket-${i}`}><FilePlus2 />Create support ticket</button>}>
          <div className="flex gap-2 flex-wrap mb-2">{c.products.map((p) => <Badge key={p.serial} tone="outline">{p.model} · {p.serial}</Badge>)}</div>
          <div className="ce-muted mb-2">{c.previous_cases} previous case(s){c.last_activity ? ` · last activity ${fmtDT(c.last_activity)}` : ""}</div>
          {c.cases.map((x) => <div key={x.id} className="ce-kv"><span><button className="ce-link" onClick={() => nav(`/app/r/${x.id}`)}>{x.ref}</button></span><b>{x.state}</b></div>)}
        </Card>
      ))}
      <RegisterCustomer open={reg} onClose={() => setReg(false)} onDone={(c) => { setReg(false); setRes([{ ...c, previous_cases: 0, cases: [], products: [] }]); }} />
      <CreateDialog open={!!ticket} onClose={() => setTicket(null)} type="case" sub="support_ticket" prefill={ticket ? { customer_id: ticket.id } : {}} labels={ticket ? { customer_id: ticket.name } : {}} onCreated={(x) => nav(`/app/r/${x.id}`)} />
    </Frame>
  );
}

function useGet(path, params) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const key = JSON.stringify(params || {});
  const load = useCallback(() => api.get(path, { params: JSON.parse(key) }).then((r) => { setD(r.data); setErr(""); }).catch((e) => setErr(errMsg(e))), [path, key]);
  useEffect(() => { load(); }, [load]);
  return [d, err, load];
}

export function Orders({ screen: s }) {
  const nav = useNavigate();
  const [d, err] = useGet("/orders");
  const cols = [{ key: "ref", label: "Order" }, { key: "date", label: "Date", render: (o) => fmtD(o.date) }, { key: "site", label: "Site" }, { key: "units", label: "Units" }, { key: "claims", label: "Grievances" },
    { key: "x", label: "", render: (o) => <button className="ce-btn sm" onClick={(e) => { e.stopPropagation(); nav(`/app/s/CE-023?order_ref=${o.id}&order_ref_label=${encodeURIComponent(o.ref)}`); }} data-testid={`raise-${o.ref}`}>Raise grievance</button> }];
  return <Frame screen={s}>{err && <Notice tone="red">{err}</Notice>}<Card>{!d ? <Loading /> : <DataTable cols={cols} rows={d.items} testid="orders-table" />}</Card></Frame>;
}

export function Roster({ screen: s }) {
  const nav = useNavigate();
  const [d, err] = useGet("/roster");
  const cols = [{ key: "name", label: "Engineer" }, { key: "centre", label: "Centre" }, { key: "skills", label: "Skills", render: (t) => t.skills.join(", ") }, { key: "open_jobs", label: "Open jobs", render: (t) => `${t.open_jobs} / ${t.capacity}` },
    { key: "available", label: "Availability", render: (t) => <Badge tone={t.available ? "green" : "red"}>{t.available ? "Available" : "At capacity"}</Badge> }, { key: "jobs", label: "Current jobs", render: (t) => t.jobs.map((j) => j.ref).join(", ") || "—" }];
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      {!d ? <Card><Loading /></Card> : <>
        <Card title="Engineer roster and capacity"><DataTable cols={cols} rows={d.technicians} testid="roster-table" /></Card>
        <Card title="Jobs awaiting allocation"><DataTable rows={d.unallocated} onRow={(j) => nav(`/app/s/CE-054/${j.id}`)} testid="unallocated-table" cols={[{ key: "ref", label: "Job" }, { key: "product", label: "Product" }, { key: "skill", label: "Skill" }, { key: "customer_name", label: "Customer" }, { key: "created_at", label: "Created", render: (j) => fmtDT(j.created_at) }]} /></Card>
      </>}
    </Frame>
  );
}

export function Capacity({ screen: s }) {
  const [d, err] = useGet("/capacity");
  const cols = [{ key: "name", label: "Centre" }, { key: "region", label: "Region" }, { key: "technicians", label: "Engineers" }, { key: "open_jobs", label: "Open jobs" }, { key: "unallocated", label: "Unallocated" },
    { key: "utilisation_pct", label: "Utilisation", render: (c) => (c.utilisation_pct == null ? "—" : `${c.utilisation_pct}%`) }, { key: "ftf_pct", label: "First-time fix", render: (c) => (c.ftf_pct == null ? "—" : `${c.ftf_pct}%`) }, { key: "breached_cases", label: "Breached cases" }];
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      {!d ? <Card><Loading /></Card> : <>
        <Card title="Utilisation by centre"><div style={{ height: 240 }}><ResponsiveContainer><BarChart data={d.centres} margin={{ left: -20 }}><CartesianGrid stroke="#eef2f7" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="open_jobs" fill="#3976d5" name="Open jobs" radius={[4, 4, 0, 0]} /><Bar dataKey="capacity" fill="#c9d8f2" name="Capacity" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div></Card>
        <Card><DataTable cols={cols} rows={d.centres} testid="capacity-table" /></Card>
      </>}
    </Frame>
  );
}

export function NetworkScreen({ screen: s }) {
  const [d, err] = useGet("/network");
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      {!d ? <Card><Loading /></Card> : <>
        <div className="ce-kpis">{d.regions.map((r, i) => <Kpi key={r.region} label={`${r.region} region`} value={r.open_jobs} sub={`${r.centres} centres · ${r.technicians} engineers · ${r.breached_cases} breached`} testid={`region-${i}`} />)}</div>
        <Card title="Service centre network"><DataTable testid="network-table" rows={d.centres} cols={[{ key: "name", label: "Centre" }, { key: "region", label: "Region" }, { key: "technicians", label: "Engineers" }, { key: "open_jobs", label: "Open jobs" }, { key: "utilisation_pct", label: "Utilisation %" }, { key: "breached_cases", label: "Breached" }]} /></Card>
      </>}
    </Frame>
  );
}

function CountDialog({ line, onClose, onDone }) {
  const [n, setN] = useState("");
  const submit = async () => {
    try { const { data } = await api.post("/stock/reconcile", { sku: line.sku, warehouse_id: line.warehouse_id, counted: Number(n) }); toast.success(data.difference === 0 ? "Count matches system stock" : `Difference ${data.difference} - adjustment approval ${data.approval} requested`); onDone(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Dialog open={!!line} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="count-dialog">
        <DialogHeader><DialogTitle>Record physical count</DialogTitle></DialogHeader>
        {line && <div className="ce-muted">{line.sku} · {line.part} at {line.warehouse}. System on hand: {line.on_hand}. Differences need approval before stock changes.</div>}
        <input className="ce-input" type="number" min={0} value={n} onChange={(e) => setN(e.target.value)} data-testid="count-input" />
        <div className="ce-actions"><button className="ce-btn primary" disabled={n === ""} onClick={submit} data-testid="count-submit">Submit count</button></div>
      </DialogContent>
    </Dialog>
  );
}

export function Stock({ screen: s }) {
  const { role } = useMeta();
  const [d, err, load] = useGet("/stock");
  const [line, setLine] = useState(null);
  const [f, setF] = useState("");
  const tone = { "Out of stock": "red", Low: "amber", Available: "green" };
  const cols = [{ key: "sku", label: "SKU" }, { key: "part", label: "Part" }, { key: "warehouse", label: "Warehouse" }, { key: "on_hand", label: "On hand" }, { key: "reserved", label: "Reserved" }, { key: "available", label: "Available" },
    { key: "status", label: "Status", render: (r) => <Badge tone={tone[r.status]}>{r.status}</Badge> }, ...(role === "R12" ? [{ key: "x", label: "", render: (r) => <button className="ce-btn sm" onClick={() => setLine(r)} data-testid={`count-${r.sku}-${r.warehouse_id}`}>Count</button> }] : [])];
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      <Card>
        <div className="flex gap-2 mb-3">{["", "Available", "Low", "Out of stock"].map((x) => <button key={x} className={`ce-chip ${f === x ? "on" : ""}`} onClick={() => setF(x)} data-testid={`stock-filter-${x || "all"}`}>{x || "All"}</button>)}</div>
        {!d ? <Loading /> : <DataTable cols={cols} rows={d.items.filter((r) => !f || r.status === f)} testid="stock-table" />}
      </Card>
      <CountDialog line={line} onClose={() => setLine(null)} onDone={() => { setLine(null); load(); }} />
    </Frame>
  );
}

export function Movements({ screen: s }) {
  const [d, err] = useGet("/movements");
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      <Card>{!d ? <Loading /> : <DataTable testid="movements-table" rows={d.items} empty={{ title: "No stock movements yet", body: "Reservations, dispatches, receipts and usage are recorded here automatically." }}
        cols={[{ key: "at", label: "Time", render: (r) => fmtDT(r.at) }, { key: "type", label: "Movement" }, { key: "sku", label: "SKU" }, { key: "warehouse_id", label: "Warehouse" }, { key: "qty", label: "Qty" }, { key: "ref", label: "Reference" }]} />}</Card>
    </Frame>
  );
}

export function Knowledge({ screen: s }) {
  const [q, setQ] = useState("");
  const [d, setD] = useState(null);
  const [ask, setAsk] = useState("");
  const [ans, setAns] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback((x) => api.get("/knowledge", { params: { q: x || undefined } }).then((r) => setD(r.data.items)).catch((e) => toast.error(errMsg(e))), []);
  useEffect(() => { load(""); }, [load]);
  const run = async () => { setBusy(true); try { const { data } = await api.post("/ai/knowledge", { question: ask }); setAns(data); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); } };
  return (
    <Frame screen={s}>
      <div className="ce-two">
        <div>
          <Card><form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); load(q); }}><input className="ce-input" placeholder="Search approved procedures" value={q} onChange={(e) => setQ(e.target.value)} data-testid="kb-search" /><button className="ce-btn primary" data-testid="kb-search-btn"><Search />Search</button></form></Card>
          {!d ? <Card><Loading /></Card> : !d.length ? <Card><Empty title="No articles for your role" /></Card> : d.map((a) => (
            <Card key={a.id} title={a.title} sub={`${a.category} · ${a.version}`} right={<Badge tone="amber">{a.approved}</Badge>} testid={`kb-article-${a.id}`}><div className="text-[13px] text-slate-600 leading-relaxed">{a.body}</div></Card>
          ))}
        </div>
        <Card title="Ask the knowledge base" sub="AI answers only from approved articles and cites them" testid="kb-ask">
          <textarea className="ce-input" value={ask} onChange={(e) => setAsk(e.target.value)} placeholder="e.g. How do I test insulation resistance?" data-testid="kb-question" />
          <div className="ce-actions"><button className="ce-btn primary" disabled={!ask.trim() || busy} onClick={run} data-testid="kb-ask-btn">{busy ? <Loader2 className="animate-spin" /> : <Sparkles />}Ask</button></div>
          {ans && <div data-testid="kb-answer">{ans.label && <Notice tone="blue">{ans.label}</Notice>}{ans.note && <Notice tone="gray">{ans.note}</Notice>}{ans.answer && <div className="ce-step-block text-[13px]">{ans.answer}</div>}{(ans.sources || []).map((x) => <Badge key={x.id} tone="outline">{x.title}</Badge>)}</div>}
        </Card>
      </div>
    </Frame>
  );
}
