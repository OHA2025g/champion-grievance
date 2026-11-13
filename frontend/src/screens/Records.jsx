import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Plus, ArrowLeft, ShieldAlert } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { Card, DataTable, Empty, Loading, Notice, Pager, StateBadge, renderCell, DemoTag, PageHead } from "@/components/Common";
import { CreateDialog, CreateForm } from "@/components/ActionDialog";
import { RecordDetail } from "@/components/RecordDetail";
import { EvidencePanel } from "@/components/Evidence";
import { Frame } from "@/components/Frame";
import { humanize, fmtDT } from "@/lib/fmt";

const qparams = (s, extra = {}) => ({ type: s.t, state: s.st, subtype: s.sub, filter: s.f ? JSON.stringify(s.f) : undefined, ...extra });

function useCreatable(s) {
  const { wf, role } = useMeta();
  if (!s.create_type) return null;
  const [t, sub] = s.create_type.split("/");
  const spec = wf[t]?.create?.[sub];
  return spec && spec.roles.includes(role) ? { t, sub, label: spec.label } : null;
}

export function ListScreen({ screen: s }) {
  const { wf } = useMeta();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [state, setState] = useState("");
  const [page, setPage] = useState(1);
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(false);
  const creatable = useCreatable(s);

  const load = useCallback(async () => {
    try { const { data } = await api.get("/records", { params: qparams(s, { state: state || s.st, q: q || undefined, page, size: 20, sort: s.sort ? s.sort : "-created_at" }) }); setD(data); setErr(""); } catch (e) { setErr(errMsg(e)); }
  }, [s, state, q, page]);
  useEffect(() => { load(); }, [load]);

  const cols = (s.cols || ["ref", "title", "state"]).map((k, i) => ({ key: k, label: s.col_labels?.length === s.cols?.length ? s.col_labels[i] : humanize(k), render: (r) => renderCell(r, k, wf) }));
  const actions = (
    <>
      {s.create && <button className="ce-btn primary" onClick={() => nav(`/app/s/${s.create}`)} data-testid="list-create-btn"><Plus />{s.action || "Create"}</button>}
      {creatable && <button className="ce-btn primary" onClick={() => setOpen(true)} data-testid="list-create-btn"><Plus />New {creatable.label.toLowerCase()}</button>}
    </>
  );
  return (
    <Frame screen={s} actions={actions}>
      <Card>
        <div className="flex gap-2 mb-4 flex-wrap">
          <input className="ce-input" style={{ maxWidth: 300 }} placeholder="Search reference, title, serial…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} data-testid="list-search" />
          <select className="ce-input" style={{ maxWidth: 240 }} value={state} onChange={(e) => { setState(e.target.value); setPage(1); }} data-testid="list-state-filter">
            <option value="">{s.st ? "Default stage filter" : "All states"}</option>
            {Object.entries(wf[s.t]?.states || {}).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>
        {err && <Notice tone="red" testid="list-error">{err}</Notice>}
        {!d ? <Loading /> : <><DataTable cols={cols} rows={d.items} onRow={(r) => nav(s.row ? `/app/s/${s.row}/${r.id}` : `/app/r/${r.id}`)} testid="records-table" /><Pager page={page} size={20} total={d.total} onPage={setPage} /></>}
      </Card>
      {creatable && <CreateDialog open={open} onClose={() => setOpen(false)} type={creatable.t} sub={creatable.sub} onCreated={(x) => nav(`/app/r/${x.id}`)} />}
    </Frame>
  );
}

export function CreateScreen({ screen: s }) {
  const { wf, role } = useMeta();
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [created, setCreated] = useState(null);
  const spec = wf[s.t]?.create?.[s.sub];
  const prefill = {};
  const labels = {};
  sp.forEach((v, k) => { if (k.endsWith("_label")) labels[k.slice(0, -6)] = v; else prefill[k] = v; });
  if (!spec) return <Frame screen={s}><Notice tone="red">Form not configured.</Notice></Frame>;
  const allowed = spec.roles.includes(role);
  const states = Object.values(wf[s.t].states).filter((x) => !x.terminal).slice(0, 5);
  const done = (x) => {
    setCreated(x);
    if (!x.safety_flag && !(x.possible_duplicates || []).length) nav(s.after ? `/app/s/${s.after}/${x.id}` : `/app/r/${x.id}`);
  };
  return (
    <Frame screen={s}>
      {!allowed && <Notice tone="red" title="Not permitted">Your role cannot submit a {spec.label.toLowerCase()}.</Notice>}
      {created && (
        <Notice tone={created.safety_flag ? "red" : "blue"} testid="create-result" title={`${created.ref} registered`}
          right={<button className="ce-btn sm" onClick={() => nav(s.after ? `/app/s/${s.after}/${created.id}` : `/app/r/${created.id}`)} data-testid="open-created">Continue</button>}>
          {created.safety_flag && <span className="flex gap-1 items-center"><ShieldAlert size={13} /> Safety concern escalated to Quality and Product Safety. If safe, switch off and unplug the product.</span>}
          {created.possible_duplicates?.length > 0 && <span>Possible related records: {created.possible_duplicates.map((p) => p.ref || p).join(", ")}. Support will confirm.</span>}
        </Notice>
      )}
      {allowed && !created && (
        <div className="ce-two">
          <Card title={spec.label} sub="Fields marked * are required"><CreateForm type={s.t} sub={s.sub} prefill={prefill} labels={labels} onCreated={done} submitLabel={s.action} /></Card>
          <div>
            <Card title="What happens next">
              {states.map((x, i) => <div key={x.label} className="ce-kv"><span>{i + 1}. {x.label}</span><b className="font-normal text-slate-500">{x.next}</b></div>)}
            </Card>
            {s.t === "case" && <Notice tone="red" title="Safety first">If there is smoke, sparks, a burning smell, an electric shock or water near live power, select it under safety concern. It is escalated immediately.</Notice>}
          </div>
        </div>
      )}
    </Frame>
  );
}

export function Queue({ s, rid, onPick, reloadKey }) {
  const { wf } = useMeta();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get("/records", { params: qparams(s, { size: 50, sort: "-updated_at" }) }).then((r) => { setD(r.data); setErr(""); }).catch((e) => setErr(errMsg(e)));
  }, [s, reloadKey]);
  useEffect(() => { if (!rid && d?.items?.length) onPick(d.items[0].id, true); }, [d, rid, onPick]);
  return (
    <div className="ce-card" style={{ padding: 0 }} data-testid="record-queue">
      <div className="px-4 py-3 border-b flex justify-between items-center"><b className="text-[12.5px] text-slate-700">Work queue</b><span className="ce-badge gray">{d?.total ?? "…"}</span></div>
      {err && <div className="p-3"><Notice tone="red">{err}</Notice></div>}
      {!d ? <div className="p-4"><Loading rows={3} /></div> : !d.items.length ? <Empty title="Queue is clear">No records are currently at this stage for your scope.</Empty> :
        <div className="max-h-[640px] overflow-auto">
          {d.items.map((r, i) => (
            <div key={r.id} className={`ce-queue-item ${rid === r.id ? "on" : ""}`} onClick={() => onPick(r.id)} data-testid={`queue-item-${i}`}>
              <div className="flex justify-between gap-2"><span className="ce-mono text-[11.5px] text-blue-700 font-semibold">{r.ref}</span><StateBadge wf={wf} type={r.type} state={r.state} /></div>
              <div className="text-slate-700 mt-1 line-clamp-2">{r.title}</div>
              <div className="text-[10.5px] text-slate-400 mt-1">{r.customer_name || r.org_name || r.technician_name || ""} · {fmtDT(r.updated_at)} <DemoTag show={false} /></div>
            </div>
          ))}
        </div>}
    </div>
  );
}

export function RecordScreen({ screen: s, rid }) {
  const nav = useNavigate();
  const [k, setK] = useState(0);
  const [open, setOpen] = useState(false);
  const creatable = useCreatable(s);
  const pick = useCallback((id, replace) => nav(`/app/s/${s.id}/${id}`, { replace: !!replace }), [nav, s.id]);
  return (
    <Frame screen={s} actions={creatable && <button className="ce-btn primary" onClick={() => setOpen(true)} data-testid="record-create-btn"><Plus />New {creatable.label.toLowerCase()}</button>}>
      <div className="ce-split">
        <Queue s={s} rid={rid} onPick={pick} reloadKey={k} />
        <div className="min-w-0">{rid ? <RecordDetail key={rid} rid={rid} focus={s.focus} panels={s.panels} onChanged={() => setK((x) => x + 1)} /> : <Card><Empty title="Select a record">Choose a record from the work queue to continue.</Empty></Card>}</div>
      </div>
      {creatable && <CreateDialog open={open} onClose={() => setOpen(false)} type={creatable.t} sub={creatable.sub} onCreated={(x) => { setK((v) => v + 1); pick(x.id); }} />}
    </Frame>
  );
}

export function UploadScreen({ screen: s, rid }) {
  const nav = useNavigate();
  const pick = useCallback((id, replace) => nav(`/app/s/${s.id}/${id}`, { replace: !!replace }), [nav, s.id]);
  const [rec, setRec] = useState(null);
  useEffect(() => { if (rid) api.get(`/records/${rid}`).then((r) => setRec(r.data.record)).catch(() => setRec(null)); }, [rid]);
  return (
    <Frame screen={s}>
      <div className="ce-split">
        <Queue s={s} rid={rid} onPick={pick} />
        <div className="min-w-0">
          {rec ? (
            <Card title={`Evidence for ${rec.ref}`} sub={rec.title} right={<button className="ce-link" onClick={() => nav(`/app/r/${rec.id}`)} data-testid="open-record-link">Open record</button>}>
              <Notice tone="blue">Upload photos of the product and serial label, and your invoice or warranty card if available. Files are scanned before anyone can open them.</Notice>
              <EvidencePanel record={rec} />
            </Card>
          ) : <Card><Empty title="Select a request">Choose an open request to attach evidence.</Empty></Card>}
        </div>
      </div>
    </Frame>
  );
}

const PANELS = { case: ["blocking", "duplicates"], job: ["estimate", "prior_repairs"], incident: ["exposure"], tech_review: ["prior_repairs"], audit: ["sample"], supplier_dispute: ["lines"] };
export function RecordPage() {
  const { rid } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [type, setType] = useState(null);
  useEffect(() => { api.get(`/records/${rid}`).then((r) => setType(r.data.record.type)).catch(() => setType("")); }, [rid]);
  const staff = !["R01", "R02", "R03"].includes(user.active_role);
  const panels = [...(PANELS[type] || []), ...(staff && ["case", "incident"].includes(type) && user.active_role !== "R13" ? ["ai"] : [])].filter((p) => staff || !["blocking", "duplicates", "prior_repairs"].includes(p));
  return (
    <div data-testid="record-page" className={user.active_role === "R06" ? "ce-mobile-content" : ""}>
      <button className="ce-btn sm mb-4" onClick={() => nav(-1)} data-testid="back-btn"><ArrowLeft />Back</button>
      {type !== null && <RecordDetail key={rid} rid={rid} panels={panels} />}
    </div>
  );
}

const SEARCH_TYPES = ["case", "job", "warranty", "settlement", "requisition", "incident", "channel_dispute", "appeal", "supplier_dispute", "audit_finding", "task", "approval", "contact", "tech_review", "escalation"];
export function SearchPage() {
  const [sp] = useSearchParams();
  const q = sp.get("q") || "";
  const { wf } = useMeta();
  const nav = useNavigate();
  const [rows, setRows] = useState(null);
  useEffect(() => {
    setRows(null);
    Promise.all(SEARCH_TYPES.map((t) => api.get("/records", { params: { type: t, q, size: 10 } }).then((r) => r.data.items).catch(() => []))).then((all) => setRows(all.flat()));
  }, [q]);
  const cols = useMemo(() => [{ key: "ref", label: "Reference" }, { key: "type", label: "Type", render: (r) => wf[r.type]?.label }, { key: "title", label: "Title" }, { key: "state", label: "State", render: (r) => renderCell(r, "state", wf) }, { key: "updated_at", label: "Updated", render: (r) => fmtDT(r.updated_at) }], [wf]);
  return (
    <div data-testid="search-page">
      <PageHead eyebrow="Search" title={`Results for "${q}"`} sub="Only records inside your authorised scope are searched." />
      <Card>{!rows ? <Loading /> : <DataTable cols={cols} rows={rows} onRow={(r) => nav(`/app/r/${r.id}`)} testid="search-results" empty={{ title: "No permitted records match", body: "Try a full reference such as CE-2026-00001, a serial number or a customer name." }} />}</Card>
    </div>
  );
}
