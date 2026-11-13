import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowRight, MapPin, Clock, Wifi, WifiOff, RefreshCw, Trash2 } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { Badge, Card, Empty, Kpi, Loading, Notice, StateBadge } from "@/components/Common";
import { MFrame } from "@/components/Frame";
import { RecordDetail } from "@/components/RecordDetail";
import { readDrafts, writeDrafts } from "@/components/ActionDialog";
import { fmtDT } from "@/lib/fmt";

const STEP_SCREEN = { dispatched: "CE-044", on_site: "CE-045", diagnosed: "CE-048", authorised: "CE-048", repaired: "CE-049", tested: "CE-050", returned: "CE-050" };

export function JobCard({ j, onOpen, i }) {
  const { wf } = useMeta();
  return (
    <div className="ce-card" style={{ padding: 16, cursor: "pointer" }} onClick={onOpen} data-testid={`job-card-${i}`}>
      <div className="flex justify-between items-center"><span className="ce-mono text-[12px] text-blue-700 font-semibold">{j.ref}</span><StateBadge wf={wf} type="job" state={j.state} /></div>
      <div className="text-[15px] font-semibold text-slate-800 mt-2">{j.product || j.title}</div>
      <div className="text-[12px] text-slate-500 mt-1 flex items-center gap-1.5"><MapPin size={12} />{j.customer_name} · {j.centre_name}</div>
      {j.appointment && <div className="text-[12px] text-slate-500 mt-1 flex items-center gap-1.5"><Clock size={12} />{fmtDT(j.appointment.start)}</div>}
      <div className="flex justify-between items-center mt-3 pt-3 border-t text-[11.5px] text-slate-500"><span>{j.next_action}</span><ArrowRight size={14} className="text-blue-600" /></div>
    </div>
  );
}

function useJobs(states) {
  const [jobs, setJobs] = useState(null);
  const key = states.join(",");
  useEffect(() => { api.get("/records", { params: { type: "job", state: key, size: 50, sort: "-updated_at" } }).then((r) => setJobs(r.data.items)).catch(() => setJobs([])); }, [key]);
  return jobs;
}

export function MDashboard({ screen }) {
  const { user } = useAuth();
  const { wf } = useMeta();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const jobs = useJobs(["open"]);
  useEffect(() => { api.get("/dashboard").then((r) => setD(r.data)).catch(() => {}); }, []);
  const next = (jobs || []).filter((j) => j.appointment).sort((a, b) => (a.appointment.start < b.appointment.start ? -1 : 1))[0];
  const hour = new Date().getHours();
  return (
    <MFrame screen={screen} greeting={`Good ${hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening"}, ${user.name.split(" ")[0]}`} sub={`${user.centre_name || ""} · Authorised service engineer`}>
      <div className="ce-kpis">{(d?.kpis || []).map((k, i) => <Kpi key={k.label} label={k.label} value={k.value} sub={k.sub} testid={`kpi-${i}`} onClick={() => nav("/app/s/CE-043")} />)}</div>
      <Card title="Next appointment" testid="next-appointment">
        {!jobs ? <Loading rows={2} /> : !next ? <div className="ce-muted">No upcoming appointment.</div> : (
          <>
            <div className="flex gap-2 items-center"><span className="ce-mono text-blue-700 font-semibold text-[12px]">{next.ref}</span><StateBadge wf={wf} type="job" state={next.state} /></div>
            <div className="text-[16px] font-semibold mt-1">{next.product}</div>
            <div className="ce-muted">{next.customer_name} · {fmtDT(next.appointment.start)}</div>
            <button className="ce-btn primary mt-3" onClick={() => nav(`/app/s/${STEP_SCREEN[next.state] || "CE-044"}/${next.id}`)} data-testid="view-visit-btn"><ArrowRight />View visit</button>
          </>
        )}
      </Card>
      <Card title="Today at a glance">{(d?.kpis || []).map((k) => <div key={k.label} className="ce-kv"><span>{k.label}</span><b>{k.value}</b></div>)}</Card>
    </MFrame>
  );
}

export function MJobs({ screen }) {
  const nav = useNavigate();
  const jobs = useJobs(["open"]);
  return (
    <MFrame screen={screen}>
      {!jobs ? <Loading /> : !jobs.length ? <Empty title="No assigned jobs">New allocations from your service centre appear here.</Empty> :
        jobs.map((j, i) => <JobCard key={j.id} j={j} i={i} onOpen={() => nav(STEP_SCREEN[j.state] ? `/app/s/${STEP_SCREEN[j.state]}/${j.id}` : `/app/r/${j.id}`)} />)}
    </MFrame>
  );
}

export function MJob({ screen, rid }) {
  const { wf } = useMeta();
  const nav = useNavigate();
  const key = screen.focus?.[0];
  const action = wf.job.actions.find((a) => a.key === key);
  const jobs = useJobs(action?.from || ["open"]);
  if (rid) {
    return (
      <MFrame screen={screen} sub={action?.label}>
        <button className="ce-link mb-3 block" onClick={() => nav(`/app/s/${screen.id}`)} data-testid="mobile-back">← Eligible jobs</button>
        <RecordDetail key={rid} rid={rid} focus={screen.focus} inlineAction={key} panels={["estimate"]} onChanged={() => {}} />
      </MFrame>
    );
  }
  return (
    <MFrame screen={screen} sub={`Jobs ready for: ${action?.label}`}>
      {!jobs ? <Loading /> : !jobs.length ? <Empty title="No jobs at this step">Jobs appear here when they reach this stage.</Empty> :
        jobs.map((j, i) => <JobCard key={j.id} j={j} i={i} onOpen={() => nav(`/app/s/${screen.id}/${j.id}`)} />)}
    </MFrame>
  );
}

export function MSync({ screen }) {
  const [drafts, setDrafts] = useState(readDrafts());
  const [online, setOnline] = useState(navigator.onLine);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  const save = (d) => { writeDrafts(d); setDrafts(d); };
  const sync = async () => {
    setBusy(true);
    let left = [];
    for (const d of drafts) {
      try {
        await api.post(`/records/${d.record_id}/actions/${d.key}`, d.payload, { headers: { "Idempotency-Key": d.id } });
        toast.success(`${d.ref}: ${d.label} synced`);
      } catch (e) {
        left.push({ ...d, error: errMsg(e) });
      }
    }
    save(left);
    setBusy(false);
  };
  return (
    <MFrame screen={screen}>
      <Notice tone={online ? "green" : ""} title={online ? "Online" : "Offline"}>{online ? "Drafts can be synchronised now." : "Work is saved on this device until a connection is available."}</Notice>
      <div className="flex gap-2 mb-3"><button className="ce-btn primary flex-1 justify-center" disabled={!drafts.length || busy || !online} onClick={sync} data-testid="sync-now-btn"><RefreshCw className={busy ? "animate-spin" : ""} />Sync {drafts.length} draft(s)</button></div>
      {!drafts.length ? <Empty title="No offline drafts">Steps you submit without a connection are kept here and synced with duplicate protection.</Empty> :
        drafts.map((d, i) => (
          <Card key={d.id} testid={`draft-${i}`}>
            <div className="flex justify-between"><b className="ce-mono text-blue-700">{d.ref}</b><Badge tone={d.error ? "red" : "amber"}>{d.error ? "Conflict" : "Pending sync"}</Badge></div>
            <div className="font-semibold mt-1">{d.label}</div>
            <div className="ce-muted">Saved {fmtDT(d.at)}</div>
            {d.error && <Notice tone="red">{d.error}</Notice>}
            <button className="ce-btn sm mt-2" onClick={() => save(drafts.filter((x) => x.id !== d.id))} data-testid={`discard-draft-${i}`}><Trash2 />Discard</button>
          </Card>
        ))}
      <div className="ce-muted text-center mt-4 flex items-center justify-center gap-1">{online ? <Wifi size={13} /> : <WifiOff size={13} />} Idempotency keys prevent duplicate submissions.</div>
    </MFrame>
  );
}
