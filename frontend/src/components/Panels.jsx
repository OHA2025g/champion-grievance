import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Loader2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, KV, Notice, StateBadge } from "@/components/Common";
import { SlaClocks } from "@/components/RecordParts";
import { fmtDT, fmtVal, inr } from "@/lib/fmt";

function Duplicates({ rec }) {
  const [items, setItems] = useState(null);
  const nav = useNavigate();
  useEffect(() => { api.get(`/records/${rec.id}/duplicates`).then((r) => setItems(r.data.items)).catch(() => setItems([])); }, [rec.id]);
  return (
    <Card title="Possible duplicates" sub="Matches on customer, serial and product" testid="panel-duplicates">
      {items === null ? <div className="ce-muted">Checking…</div> : !items.length ? <div className="ce-muted">No likely duplicates found.</div> :
        items.map((i) => (
          <div key={i.id} className="ce-kv"><span><button className="ce-link" onClick={() => nav(`/app/r/${i.id}`)}>{i.ref}</button> {i.title}</span><b>{i.match.join(", ") || "Related"}</b></div>
        ))}
    </Card>
  );
}

function AiOutput({ out }) {
  return (
    <div className="ce-step-block text-[12px]">
      {Object.entries(out || {}).map(([k, v]) => <div key={k} className="mb-1"><b className="text-slate-600 capitalize">{k.replace(/_/g, " ")}:</b> {Array.isArray(v) ? v.join("; ") : String(v)}</div>)}
    </div>
  );
}

function Ai({ rec, tasks }) {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState("");
  const [res, setRes] = useState(null);
  const [text, setText] = useState("");
  useEffect(() => { api.get("/ai/status").then((r) => setStatus(r.data)).catch(() => setStatus({ configured: false })); }, []);
  const run = async (t) => {
    setBusy(t);
    try {
      const { data } = await api.post("/ai/assist", { task: t, record_id: rec.id });
      setRes(data);
      setText(data.output?.summary || data.output?.draft || "");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };
  const accept = async () => {
    try { await api.post("/ai/accept", { log_id: res.id, apply_text: text }); toast.success("Reviewed suggestion accepted and logged"); setRes({ ...res, accepted: true }); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Card title="Reviewed AI assistance" sub="Suggestions only - a person decides" right={<Badge tone="outline"><Sparkles size={11} /> {status?.model || "Mistral AI"}</Badge>} testid="panel-ai">
      {status && !status.configured && <Notice tone="gray" title="AI assistance not configured">Add a Mistral API key to enable suggestions. All workflows keep working without AI.</Notice>}
      <div className="flex flex-wrap gap-2 mb-3">
        {tasks.map((t) => <button key={t} className="ce-btn sm" disabled={!status?.configured || !!busy} onClick={() => run(t)} data-testid={`ai-task-${t}`}>{busy === t && <Loader2 className="animate-spin" />}{t.replace(/_/g, " ")}</button>)}
      </div>
      {res && (
        <div data-testid="ai-result">
          <Notice tone="blue">{res.label} · {res.model}</Notice>
          <AiOutput out={res.output} />
          {(res.task === "summary" || res.task === "draft_reply") && <textarea className="ce-input mt-2" value={text} onChange={(e) => setText(e.target.value)} data-testid="ai-review-text" />}
          <div className="ce-actions"><button className="ce-btn primary" disabled={res.accepted} onClick={accept} data-testid="ai-accept">{res.accepted ? "Accepted" : "Accept after review"}</button></div>
        </div>
      )}
    </Card>
  );
}

function Exposure({ rec }) {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get(`/incidents/${rec.id}/exposure`).then((r) => setItems(r.data.items)).catch(() => {}); }, [rec.id]);
  const cols = [{ key: "batch", label: "Batch / serial prefix" }, { key: "model", label: "Model" }, { key: "cases", label: "Cases" }, { key: "safety", label: "Safety flags" }, { key: "linked", label: "Linked" },
    { key: "risk", label: "Risk", render: (r) => <Badge tone={r.risk === "High" ? "red" : r.risk === "Medium" ? "amber" : "green"}>{r.risk}</Badge> }];
  return <Card title="Affected units and exposure" testid="panel-exposure"><DataTable cols={cols} rows={items} testid="exposure-table" /></Card>;
}

function PriorRepairs({ rec }) {
  const [d, setD] = useState(null);
  const serial = rec.data?.serial || rec.serial;
  useEffect(() => { if (serial) api.get("/products/history", { params: { serial } }).then((r) => setD(r.data)).catch(() => {}); }, [serial]);
  return (
    <Card title="Product service history" sub={serial ? `Serial ${serial}` : "No serial recorded"} testid="panel-prior-repairs">
      {(d?.jobs || []).map((j) => <KV key={j.id} k={`${j.ref} · ${fmtDT(j.created_at)}`} v={`${j.diagnosis || j.title} (${j.state})`} />)}
      {d && !d.jobs.length && <div className="ce-muted">No previous service jobs for this serial.</div>}
    </Card>
  );
}

function Blocking({ deps }) {
  const nav = useNavigate();
  return (
    <Card title="Closure dependencies" sub="Mandatory linked work must be complete before resolution or closure" testid="panel-blocking">
      {!deps?.length ? <Notice tone="green">No open blocking work. The case can be resolved when the outcome is verified.</Notice> :
        deps.map((d) => <div key={d.id} className="ce-kv"><span><button className="ce-link" onClick={() => nav(`/app/r/${d.id}`)}>{d.ref}</button> {d.title}</span><b>{d.state}</b></div>)}
    </Card>
  );
}

function Estimate({ rec }) {
  const e = rec.estimate;
  return (
    <Card title="Repair estimate" testid="panel-estimate">
      {!e ? <div className="ce-muted">No estimate submitted.</div> : (
        <>
          <KV k="Labour" v={inr(e.labour)} /><KV k="Parts" v={inr(e.parts)} /><KV k="Chargeable to customer" v={e.chargeable} />
          <div className="ce-kv"><span>Total</span><b className="text-lg">{inr(e.total)}</b></div>
          <KV k="Customer decision" v={fmtVal(rec.estimate_state)} />
        </>
      )}
    </Card>
  );
}

function Units({ children, wf }) {
  const nav = useNavigate();
  const units = (children || []).filter((c) => c.type === "unit");
  const cols = [{ key: "data.site", label: "Site", render: (r) => r.data?.site }, { key: "data.serial", label: "Serial", render: (r) => r.data?.serial }, { key: "job_ref", label: "Job" },
    { key: "state", label: "State", render: (r) => <StateBadge wf={wf} type="unit" state={r.state} /> }];
  return <Card title={`Affected units (${units.length})`} testid="panel-units"><DataTable cols={cols} rows={units} onRow={(r) => nav(`/app/r/${r.id}`)} testid="units-table" /></Card>;
}

function ListPanel({ title, rows, testid }) {
  if (!rows?.length) return null;
  const keys = Object.keys(rows[0]).filter((k) => typeof rows[0][k] !== "object");
  return <Card title={title} testid={testid}><DataTable cols={keys.map((k) => ({ key: k, label: k.replace(/_/g, " ") }))} rows={rows} testid={`${testid}-table`} /></Card>;
}

export function Panels({ panels = [], d }) {
  const { wf } = useMeta();
  const rec = d.record;
  return panels.map((p) => {
    if (p === "duplicates") return <Duplicates key={p} rec={rec} />;
    if (p === "ai") return <Ai key={p} rec={rec} tasks={["summary", "sentiment", "priority", "categorise", "routing", "draft_reply"]} />;
    if (p === "ai_root") return <Ai key={p} rec={rec} tasks={["root_cause", "summary"]} />;
    if (p === "exposure") return <Exposure key={p} rec={rec} />;
    if (p === "prior_repairs") return <PriorRepairs key={p} rec={rec} />;
    if (p === "blocking") return <Blocking key={p} deps={d.dependencies} />;
    if (p === "estimate") return <Estimate key={p} rec={rec} />;
    if (p === "units" || p === "reconcile") return p === "units" ? <Units key={p} children={d.children} wf={wf} /> : null;
    if (p === "sla") return <Card key={p} title="SLA clocks" testid="panel-sla"><SlaClocks rec={rec} /></Card>;
    if (p === "sample") return <ListPanel key={p} title="Audit sample" rows={rec.sample} testid="panel-sample" />;
    if (p === "lines") return <ListPanel key={p} title="Reconciliation lines" rows={rec.lines} testid="panel-lines" />;
    if (p === "safety") return rec.safety_flag ? <Notice key={p} tone="red" title="Safety concern flagged" testid="panel-safety">{rec.data?.safety_concern} - specialist containment is coordinated by Quality and Product Safety.</Notice> : null;
    if (p === "translation") return rec.data?.save_translation ? <Card key={p} title="Saved translation" testid="panel-translation"><div className="ce-muted">{rec.data.save_translation.translation}</div></Card> : null;
    return null;
  });
}
