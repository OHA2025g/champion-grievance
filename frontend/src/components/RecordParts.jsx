import { useNavigate } from "react-router-dom";
import { useMeta } from "@/context/AuthContext";
import { Badge, DataTable, Empty, KV, StateBadge } from "@/components/Common";
import { fmtDT, fmtVal, inr } from "@/lib/fmt";

const COMM_STATE = {
  delivered_in_app: ["In-app delivered", "green"], sent: ["Email sent", "green"], dev_adapter_not_sent: ["MOCKED adapter - not sent", "amber"],
  suppressed_demo_recipient: ["Demo recipient - suppressed", "gray"], failed: ["Delivery failed", "red"], queued: ["Queued", "amber"],
};

export function Facts({ rec, wf }) {
  const W = wf[rec.type];
  const spec = W.create?.[rec.subtype];
  const fields = spec?.fields || [];
  const data = rec.data || {};
  const shown = fields.filter((f) => data[f.k] != null && data[f.k] !== "" && f.k !== "description");
  return (
    <div data-testid="record-facts">
      {data.description && <div className="ce-step-block text-[13px] text-slate-600 leading-relaxed" data-testid="record-description">{data.description}</div>}
      {rec.type === "approval" && (
        <div data-testid="approval-request">
          <KV k="Request" v={data.summary || rec.title} />
          {rec.subject_ref && <KV k="Subject" v={rec.subject_ref} />}
          {Object.entries(rec.payload || {}).map(([k, v]) => (typeof v === "object" && v !== null ? <div key={k} className="mt-2"><div className="ce-eyebrow">{k.replace(/_/g, " ")}</div><pre className="ce-json">{JSON.stringify(v, null, 2)}</pre></div> : <KV key={k} k={k.replace(/_/g, " ")} v={fmtVal(v)} />))}
        </div>
      )}
      {shown.map((f) => <KV key={f.k} k={f.l} v={fmtVal(data[`${f.k}_label`] ?? data[f.k])} />)}
      {!data.description && !shown.length && rec.type !== "approval" && <div className="ce-muted">This {W.label.toLowerCase()} was created from {rec.parent_ref || rec.root_ref || "its parent record"}; intake details are on the parent. Work recorded on this item is listed under workflow steps.</div>}
    </div>
  );
}

export function Steps({ rec, wf }) {
  const W = wf[rec.type];
  const done = W.actions.filter((a) => rec.data?.[a.key] && typeof rec.data[a.key] === "object");
  if (!done.length) return <div className="ce-muted">No workflow steps recorded yet.</div>;
  return (
    <div data-testid="record-steps">
      {done.map((a) => {
        const v = rec.data[a.key];
        return (
          <div className="ce-step-block" key={a.key}>
            <div className="font-semibold text-[12.5px] text-slate-700 mb-1">{a.label}</div>
            {a.fields.filter((f) => v[f.k] != null && v[f.k] !== "").map((f) => <KV key={f.k} k={f.l} v={fmtVal(v[`${f.k}_label`] ?? v[f.k])} />)}
            {!a.fields.length && <div className="ce-muted">Confirmed</div>}
          </div>
        );
      })}
    </div>
  );
}

const CTX_KEYS = [["customer_name", "Complainant"], ["org_name", "Organisation"], ["product", "Product"], ["region", "Region"], ["priority", "Priority"], ["owner_name", "Accountable owner"],
  ["proposed_owner_name", "Proposed owner"], ["technician_name", "Technician"], ["centre_name", "Service centre"], ["assignee_name", "Assignee"], ["reviewer_name", "Reviewer"],
  ["action_owner_name", "Action owner"], ["approval_type", "Approval type"], ["coverage", "Coverage"], ["severity", "Severity"], ["estimate_state", "Estimate"], ["provider_ref", "Provider reference"],
  ["created_by_name", "Created by"]];

export function Context({ rec, roles, parent }) {
  const nav = useNavigate();
  return (
    <div data-testid="record-context">
      <KV k="Reference" v={<span className="ce-mono">{rec.ref}</span>} />
      {CTX_KEYS.filter(([k]) => rec[k] != null && rec[k] !== "").map(([k, l]) => <KV key={k} k={l} v={fmtVal(rec[k])} />)}
      {rec.amount != null && !(rec.type === "approval" && !rec.amount) && <KV k="Amount" v={inr(rec.amount)} />}
      {rec.required_role && <KV k="Required authority" v={roles?.[rec.required_role]?.name || rec.required_role} />}
      {rec.appointment && <KV k="Appointment" v={fmtVal(rec.appointment)} />}
      {parent && <KV k="Parent record" v={<button className="ce-link" onClick={() => nav(`/app/r/${parent.id}`)} data-testid="parent-link">{parent.ref}</button>} />}
      {rec.root_ref && rec.root_ref !== parent?.ref && <KV k="Root case" v={<button className="ce-link" onClick={() => nav(`/app/r/${rec.root_id}`)}>{rec.root_ref}</button>} />}
      <KV k="Created" v={fmtDT(rec.created_at)} />
      <KV k="Last updated" v={fmtDT(rec.updated_at)} />
      <KV k="Version" v={rec.version} />
    </div>
  );
}

export function Activity({ events }) {
  if (!events?.length) return <Empty title="No activity yet" />;
  return (
    <div className="ce-timeline" data-testid="record-activity">
      {events.map((e) => (
        <div className={`ce-event ${e.cust ? "cust" : ""}`} key={e.id}>
          <h4>{e.label}</h4>
          <div className="time">{fmtDT(e.at)} · {e.actor_name || "System"}{e.actor_role ? ` (${e.actor_role})` : ""}</div>
          {e.from_label !== e.to_label && e.to_label && <p>{e.from_label ? `${e.from_label} → ` : ""}{e.to_label}</p>}
          {e.note && <p>{e.note}</p>}
          {e.values && Object.entries(e.values).filter(([k, v]) => !k.endsWith("_id") && typeof v !== "object" && String(v).length < 160).slice(0, 4).map(([k, v]) => <p key={k}><b className="text-slate-600">{k.replace(/_label$/, "").replace(/_/g, " ")}:</b> {String(v)}</p>)}
        </div>
      ))}
    </div>
  );
}

export function Related({ items, wf }) {
  const nav = useNavigate();
  const cols = [{ key: "ref", label: "Reference" }, { key: "type", label: "Work item", render: (r) => wf[r.type]?.label || r.type }, { key: "title", label: "Title" },
    { key: "who", label: "Owner", render: (r) => r.owner_name || r.assignee_name || r.technician_name || "—" }, { key: "state", label: "State", render: (r) => <StateBadge wf={wf} type={r.type} state={r.state} /> }];
  return <DataTable cols={cols} rows={items} onRow={(r) => nav(`/app/r/${r.id}`)} testid="related-table" empty={{ title: "No linked work", body: "Jobs, tasks, approvals and claims created from this record appear here." }} />;
}

export function Comms({ items }) {
  if (!items?.length) return <Empty title="No communications" />;
  return (
    <div data-testid="record-comms">
      {items.map((c) => {
        const [l, t] = COMM_STATE[c.state] || [c.state, "gray"];
        return (
          <div className="ce-step-block" key={c.id}>
            <div className="flex justify-between gap-2 flex-wrap">
              <div className="font-semibold text-[12.5px] text-slate-700">{c.subject}</div>
              <div className="flex gap-1.5"><Badge tone="outline">{c.channel}</Badge><Badge tone={t}>{l}</Badge></div>
            </div>
            <div className="ce-muted mt-1">{c.body}</div>
            <div className="text-[11px] text-slate-400 mt-1">{c.direction} · to {c.recipient} · {fmtDT(c.at)}{c.error ? ` · ${c.error}` : ""}</div>
          </div>
        );
      })}
    </div>
  );
}

export function SlaClocks({ rec }) {
  const clocks = rec.sla || [];
  if (!clocks.length) return <Empty title="No SLA clocks">This record type has no service level milestones.</Empty>;
  const tone = { met: "green", running: "", paused: "gray", stopped: "gray", breached: "red" };
  return (
    <div className="ce-table-wrap" data-testid="sla-clocks">
      <table className="ce-table">
        <thead><tr><th>Milestone</th><th>Calendar</th><th>Started</th><th>Due</th><th>Paused (min)</th><th>State</th></tr></thead>
        <tbody>
          {clocks.map((k) => (
            <tr key={k.id}>
              <td className="ref">{k.m.replace(/_/g, " ")}</td><td>{k.calendar}</td><td>{fmtDT(k.start)}</td><td>{fmtDT(k.due)}</td><td>{Math.round(k.paused_minutes || 0)}</td>
              <td><Badge tone={k.breached_at ? "red" : k.warned && k.state === "running" ? "amber" : tone[k.state]}>{k.breached_at ? "Breached" : k.warned && k.state === "running" ? "At risk" : k.state}</Badge></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
