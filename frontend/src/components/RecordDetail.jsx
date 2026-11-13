import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ShieldAlert, Lock, ArrowRight } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { api, errMsg } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { Badge, Card, Loading, Notice, SlaBadge, StateBadge, DemoTag } from "@/components/Common";
import { ActionDialog, ActionForm } from "@/components/ActionDialog";
import { EvidencePanel } from "@/components/Evidence";
import { Activity, Comms, Context, Facts, Related, SlaClocks, Steps } from "@/components/RecordParts";
import { Panels } from "@/components/Panels";
import { fmtDT, nextDue } from "@/lib/fmt";

const EXTERNAL = ["R01", "R02", "R03"];

function ActionBar({ d, focus, onPick }) {
  const allowed = d.actions || [];
  const primary = focus ? allowed.filter((a) => focus.includes(a.key)) : allowed.slice(0, 2);
  const more = allowed.filter((a) => !primary.includes(a));
  return (
    <div className="flex gap-2 flex-wrap items-center" data-testid="record-actions">
      {primary.map((a, i) => (
        <button key={a.key} className={`ce-btn ${a.danger ? "danger" : i === 0 ? "primary" : ""}`} onClick={() => onPick(a)} data-testid={`action-btn-${a.key}`}>
          {i === 0 && <ArrowRight />}{a.label}
        </button>
      ))}
      {more.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild><button className="ce-btn" data-testid="more-actions-btn">More actions <ChevronDown /></button></DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {more.map((a) => <DropdownMenuItem key={a.key} onClick={() => onPick(a)} data-testid={`action-menu-${a.key}`}>{a.label}</DropdownMenuItem>)}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}

function Header({ d, wf, focus, onPick }) {
  const r = d.record;
  const W = wf[r.type];
  const st = W.states[r.state] || {};
  const due = nextDue(r);
  const who = r.owner_name || r.proposed_owner_name || r.assignee_name || r.technician_name || r.reviewer_name;
  const noFocus = focus && focus.length > 0 && !(d.actions || []).some((a) => focus.includes(a.key));
  return (
    <Card testid="record-header">
      <div className="flex justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="ce-eyebrow">{W.label} · <span className="ce-mono">{r.ref}</span></div>
          <h2 className="text-xl font-semibold text-slate-800 tracking-tight" data-testid="record-title">{r.title}</h2>
          <div className="flex gap-1.5 flex-wrap mt-2">
            <StateBadge wf={wf} type={r.type} state={r.state} testid="record-state" />
            <SlaBadge state={r.sla_state} />
            {r.priority && <Badge tone={r.priority.startsWith("P1") ? "red" : r.priority.startsWith("P2") ? "amber" : "gray"}>{r.priority}</Badge>}
            {r.safety_flag && <Badge tone="red" testid="safety-badge"><ShieldAlert size={11} /> Safety</Badge>}
            {r.under_appeal && <Badge tone="amber">Under appeal</Badge>}
            {d.read_only && <Badge tone="gray" testid="read-only-badge"><Lock size={11} /> Read-only access</Badge>}
            <DemoTag show={r.demo} />
          </div>
        </div>
        <ActionBar d={d} focus={focus} onPick={onPick} />
      </div>
      {st.next && (
        <div className="mt-4"><Notice tone="blue" testid="next-action" title={`Next action: ${st.next}`}>
          {who ? `Accountable: ${who}` : "Awaiting assignment"}{due ? ` · ${due.m.replace(/_/g, " ")} due ${fmtDT(due.due)}` : ""}
        </Notice></div>
      )}
      {noFocus && <Notice tone="gray" testid="no-step-available">The step on this screen is not available to your role while this record is "{st.label}". {d.actions?.length ? "Other permitted actions are listed above." : ""}</Notice>}
    </Card>
  );
}

export function RecordDetail({ rid, focus, panels = [], onChanged, inlineAction }) {
  const { wf, roles } = useMeta();
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [tab, setTab] = useState("overview");
  const [act, setAct] = useState(null);
  const ext = EXTERNAL.includes(user?.active_role);

  const load = useCallback(async () => {
    try { const { data } = await api.get(`/records/${rid}`); setD(data); setErr(""); } catch (e) { setErr(errMsg(e)); setD(null); }
  }, [rid]);
  useEffect(() => { setD(null); load(); }, [load]);

  if (err) return <Notice tone="red" testid="record-error" title="Record unavailable">{err}</Notice>;
  if (!d) return <Card><Loading /></Card>;
  const r = d.record;
  if (d.minimal) return <Card testid="record-minimal" title={r.ref} sub={r.title}><Notice tone="gray">Minimal case view - your role sees only the fields needed for settlement.</Notice></Card>;
  const done = () => { load(); onChanged && onChanged(); };
  const inline = inlineAction && (d.actions || []).find((a) => a.key === inlineAction);
  const tabs = [["overview", "Overview"], ["activity", ext ? "Timeline" : "Activity"], ["evidence", `Evidence (${d.evidence.length})`], ["related", `Related work (${d.children.length})`], ["comms", ext ? "Updates" : "Communications"], ...(!ext && r.sla?.length ? [["sla", "SLA"]] : [])];

  return (
    <div data-testid="record-detail">
      <Header d={d} wf={wf} focus={focus} onPick={setAct} />
      {inline && <Card title={inline.label} testid="inline-action"><ActionForm record={r} action={inline} onDone={done} inline /></Card>}
      <div className="ce-two">
        <div className="min-w-0">
          <div className="ce-tabs" data-testid="record-tabs">
            {tabs.map(([k, l]) => <button key={k} className={`ce-tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)} data-testid={`tab-${k}`}>{l}</button>)}
          </div>
          {tab === "overview" && <><Card title="Reported details"><Facts rec={r} wf={wf} /></Card><Card title="Workflow steps recorded"><Steps rec={r} wf={wf} /></Card></>}
          {tab === "activity" && <Card><Activity events={d.events} /></Card>}
          {tab === "evidence" && <Card>{d.read_only ? null : <EvidencePanel record={r} items={d.evidence} onChanged={load} />}{d.read_only && <Notice tone="gray">Read-only scope - evidence can be viewed, not added.</Notice>}</Card>}
          {tab === "related" && <Card><Related items={d.children} wf={wf} /></Card>}
          {tab === "comms" && <Card><Comms items={d.comms} /></Card>}
          {tab === "sla" && <Card><SlaClocks rec={r} /></Card>}
        </div>
        <div className="min-w-0">
          <Card title="Record context"><Context rec={r} roles={roles} parent={d.parent} /></Card>
          <Panels panels={panels} d={d} />
        </div>
      </div>
      {act && <ActionDialog record={r} action={act} onClose={() => setAct(null)} onDone={done} />}
    </div>
  );
}
