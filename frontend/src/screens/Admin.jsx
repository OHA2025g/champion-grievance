import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { UserPlus, RefreshCw, Plus, FileDown } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, errMsg, errFields } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, Loading, Notice, Pager } from "@/components/Common";
import { CreateDialog } from "@/components/ActionDialog";
import { Frame } from "@/components/Frame";
import { DynamicForm, Lookup, validateFields } from "@/components/DynamicForm";
import { fmtDT } from "@/lib/fmt";

function useGet(path, params) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const key = JSON.stringify(params || {});
  const load = useCallback(() => api.get(path, { params: JSON.parse(key) }).then((r) => { setD(r.data); setErr(""); }).catch((e) => setErr(errMsg(e))), [path, key]);
  useEffect(() => { load(); }, [load]);
  return [d, err, load];
}

function AccessDialog({ user: u, mode, onClose, onDone }) {
  const m = useMeta();
  const [ref, setRef] = useState("");
  const [roles, setRoles] = useState(u?.roles || []);
  useEffect(() => { setRoles(u?.roles || []); setRef(""); }, [u]);
  if (!u) return null;
  const save = async () => {
    const body = { approval_reference: ref, ...(mode === "roles" ? { roles } : { status: u.status === "active" ? "disabled" : "active" }) };
    try { await api.patch(`/admin/users/${u.id}`, body); toast.success("Access change recorded in the audit log"); onDone(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto" data-testid="access-dialog">
        <DialogHeader><DialogTitle>{mode === "roles" ? `Roles for ${u.name}` : `${u.status === "active" ? "Disable" : "Enable"} ${u.name}`}</DialogTitle></DialogHeader>
        {mode === "roles" && (
          <div className="grid grid-cols-2 gap-1.5 max-h-72 overflow-auto">
            {Object.entries(m.roles).map(([k, v]) => (
              <label key={k} className="flex gap-2 items-center text-[12px] p-1.5 border rounded"><input type="checkbox" checked={roles.includes(k)} onChange={(e) => setRoles(e.target.checked ? [...roles, k] : roles.filter((x) => x !== k))} data-testid={`role-check-${k}`} /><b className="ce-mono">{k}</b> {v.name}</label>
            ))}
          </div>
        )}
        <div className="ce-field mt-3"><label>Access approval reference<em>*</em></label><input className="ce-input" value={ref} onChange={(e) => setRef(e.target.value)} data-testid="approval-ref-input" /><div className="ce-hint">Required for every access change. Administrators cannot change their own roles.</div></div>
        <div className="ce-actions"><button className="ce-btn primary" disabled={ref.trim().length < 4} onClick={save} data-testid="access-save">Save access change</button></div>
      </DialogContent>
    </Dialog>
  );
}

export function AdminUsers({ screen: s }) {
  const nav = useNavigate();
  const { user: me } = useAuth();
  const [d, err, load] = useGet("/admin/users");
  const [sel, setSel] = useState(null);
  const [q, setQ] = useState("");
  const rows = (d?.items || []).filter((u) => !q || `${u.name} ${u.email} ${u.roles.join(" ")}`.toLowerCase().includes(q.toLowerCase()));
  const cols = [{ key: "name", label: "Name" }, { key: "email", label: "Email" }, { key: "roles", label: "Roles", render: (u) => u.roles.join(", ") }, { key: "org", label: "Organisation / centre", render: (u) => u.org_name || u.centre_name || "—" },
    { key: "status", label: "Status", render: (u) => <Badge tone={u.status === "active" ? "green" : "gray"}>{u.status}</Badge> }, { key: "demo", label: "Type", render: (u) => (u.demo ? <Badge tone="outline">Demo</Badge> : <Badge>Real</Badge>) }, { key: "last_login", label: "Last sign-in", render: (u) => fmtDT(u.last_login) },
    { key: "x", label: "", render: (u) => <div className="flex gap-1"><button className="ce-btn sm" disabled={u.id === me.id} title={u.id === me.id ? "You cannot change your own access" : ""} onClick={() => setSel({ u, mode: "roles" })} data-testid={`edit-roles-${u.email}`}>Roles</button><button className="ce-btn sm" disabled={u.id === me.id} onClick={() => setSel({ u, mode: "status" })} data-testid={`toggle-status-${u.email}`}>{u.status === "active" ? "Disable" : "Enable"}</button></div> }];
  return (
    <Frame screen={s} actions={<button className="ce-btn primary" onClick={() => nav("/app/s/CE-158")} data-testid="invite-user-btn"><UserPlus />Invite user</button>}>
      {err && <Notice tone="red">{err}</Notice>}
      <Card><input className="ce-input mb-3" style={{ maxWidth: 320 }} placeholder="Filter by name, email or role" value={q} onChange={(e) => setQ(e.target.value)} data-testid="users-filter" />
        {!d ? <Loading /> : <DataTable cols={cols} rows={rows} testid="users-table" />}</Card>
      {sel && <AccessDialog user={sel.u} mode={sel.mode} onClose={() => setSel(null)} onDone={() => { setSel(null); load(); }} />}
    </Frame>
  );
}

const ORG_SRC = { R02: "orgs:dealer", R03: "orgs:distributor", R06: "centres", R07: "centres", R20: "orgs:supplier" };
export function Invite({ screen: s }) {
  const m = useMeta();
  const nav = useNavigate();
  const [v, setV] = useState({ role: "R04" });
  const [errs, setErrs] = useState({});
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const fields = [{ k: "name", l: "Full name", req: true }, { k: "email", l: "Work email", req: true }, { k: "role", l: "Role", t: "select", req: true, opts: Object.keys(m.roles) },
    { k: "region", l: "Region", t: "select", opts: ["North", "South", "East", "West"] }, { k: "effective_from", l: "Effective from", t: "date" }, { k: "approval_reference", l: "Access approval reference", req: true }];
  const submit = async () => {
    const e = validateFields(fields, v);
    setErrs(e);
    if (Object.keys(e).length) return;
    try { const { data } = await api.post("/admin/users", v); setRes(data); } catch (x) { setErr(errMsg(x)); setErrs(errFields(x)); }
  };
  return (
    <Frame screen={s}>
      {res ? (
        <Notice tone="green" title={`${res.name} provisioned as ${m.roles[res.active_role]?.name}`} testid="invite-result" right={<button className="ce-btn sm" onClick={() => nav("/app/s/CE-116")}>Back to users</button>}>
          Invitation email: {res.invitation_delivery === "sent" ? "sent" : res.invitation_delivery?.replace(/_/g, " ")}. The user signs in with Google using this email, or sets a password via "Recover staff access".
        </Notice>
      ) : (
        <div className="ce-two">
          <Card title="Provision a user" sub="Access is granted only to the selected role and scope">
            <DynamicForm fields={fields} values={v} setValues={setV} errors={errs} prefix="invite" />
            {ORG_SRC[v.role] && <div className="ce-field mt-4"><label>{v.role === "R06" || v.role === "R07" ? "Service centre" : "Organisation"}</label><Lookup src={ORG_SRC[v.role]} value={v.org_id} onChange={(x) => setV({ ...v, org_id: x })} testid="invite-org" /></div>}
            {err && <div className="mt-3"><Notice tone="red">{err}</Notice></div>}
            <div className="ce-actions"><button className="ce-btn primary" onClick={submit} data-testid="invite-submit"><UserPlus />Send invitation</button></div>
          </Card>
          <Card title="Role summary">{v.role && <><div className="ce-h2">{m.roles[v.role]?.name}</div><div className="ce-muted">{m.roles[v.role]?.workspace} · {m.roles[v.role]?.scope}</div></>}</Card>
        </div>
      )}
    </Frame>
  );
}

export function Permissions({ screen: s }) {
  const [d, err] = useGet("/admin/permissions");
  const [t, setT] = useState("case");
  const types = d ? Object.keys(d.types) : [];
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      {!d ? <Card><Loading /></Card> : <>
        <Card title="Role scope matrix" sub="Data scope enforced on the server for every record type">
          <div className="ce-table-wrap" data-testid="permission-matrix">
            <table className="ce-table"><thead><tr><th>Role</th>{types.map((x) => <th key={x}>{d.types[x]}</th>)}</tr></thead>
              <tbody>{d.roles.map((r) => <tr key={r.role}><td className="ref">{r.role} <span className="sub">{r.name}</span></td>{types.map((x) => <td key={x}>{r.types[x] ? <Badge tone={r.types[x] === "ro" ? "gray" : r.types[x] === "all" ? "" : "green"}>{r.types[x]}</Badge> : <span className="text-slate-300">–</span>}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </Card>
        <Card title="Workflow action permissions" right={<select className="ce-input" style={{ maxWidth: 260 }} value={t} onChange={(e) => setT(e.target.value)} data-testid="perm-type">{types.map((x) => <option key={x} value={x}>{d.types[x]}</option>)}</select>}>
          <DataTable rows={d.actions[t]} cols={[{ key: "label", label: "Action" }, { key: "key", label: "Key" }, { key: "roles", label: "Permitted roles", render: (a) => a.roles.join(", ") }]} testid="perm-actions-table" />
        </Card>
      </>}
    </Frame>
  );
}

export function Models({ screen: s }) {
  const nav = useNavigate();
  const [d, err] = useGet("/lookup/models");
  return (
    <Frame screen={s} actions={<button className="ce-btn primary" onClick={() => nav("/app/s/CE-159")} data-testid="propose-model-btn"><Plus />Propose model change</button>}>
      {err && <Notice tone="red">{err}</Notice>}
      <Notice tone="gray">Product model changes are governed: proposals are reviewed and published by a second authorised person.</Notice>
      <Card>{!d ? <Loading /> : <DataTable rows={d} testid="models-table" cols={[{ key: "label", label: "Category / model" }, { key: "sub", label: "Required skill" }, { key: "value", label: "Model ID" }]} />}</Card>
    </Frame>
  );
}

export function AdminConfig({ screen: s }) {
  const nav = useNavigate();
  const [d, err, load] = useGet("/admin/config");
  const [v] = useGet(`/admin/config/${s.key}/versions`);
  const [open, setOpen] = useState(false);
  const cur = d?.items.find((c) => c.key === s.key);
  const base = cur?.value ?? d?.defaults?.[s.key];
  return (
    <Frame screen={s} actions={<button className="ce-btn primary" onClick={() => setOpen(true)} data-testid="propose-config-btn"><Plus />Propose change</button>}>
      {err && <Notice tone="red">{err}</Notice>}
      <Notice tone="blue">Changes follow the controlled release workflow: scope check, automated tests, second-administrator approval, release and rollback. Values marked PLACEHOLDER await Champion policy confirmation.</Notice>
      <div className="ce-two">
        <Card title={`Current ${s.key.replace(/_/g, " ")}`} sub={cur ? `Version ${cur.version} · updated ${fmtDT(cur.updated_at)} by ${cur.updated_by}` : "Using built-in defaults"} testid="config-current">
          <pre className="ce-json">{JSON.stringify(base ?? "Built-in defaults (no override saved)", null, 2)}</pre>
        </Card>
        <Card title="Version history">{!v ? <Loading /> : <DataTable rows={v.items} testid="config-versions" cols={[{ key: "version", label: "Version" }, { key: "at", label: "Saved", render: (x) => fmtDT(x.at) }, { key: "by", label: "By" }, { key: "note", label: "Note" }]} />}</Card>
      </div>
      <CreateDialog open={open} onClose={() => setOpen(false)} type="config_change" sub="change" prefill={{ target: s.key, proposed_value: JSON.stringify(base ?? {}, null, 2) }} onCreated={(x) => { toast.success(`${x.ref} created - continue the controlled release`); load(); nav(`/app/s/CE-153/${x.id}`); }} />
    </Frame>
  );
}

const MODE_TONE = (m) => (m.startsWith("LIVE") ? "green" : m.includes("MOCK") || m.includes("SIMULATED") || m.includes("DEV") ? "amber" : "gray");
export function Integrations({ screen: s }) {
  const [d, err] = useGet("/admin/integrations");
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      <Card>{!d ? <Loading /> : <DataTable rows={d.items} testid="integrations-table" cols={[{ key: "adapter", label: "Adapter" }, { key: "mode", label: "Mode", render: (r) => <Badge tone={MODE_TONE(r.mode)}>{r.mode}</Badge> }, { key: "health", label: "Health" },
        { key: "last_sync", label: "Last activity", render: (r) => fmtDT(r.last_sync) }, { key: "queue_lag", label: "Queued" }, { key: "failures", label: "Failures" }, { key: "owner", label: "Owner" }, { key: "note", label: "Note" }]} />}</Card>
    </Frame>
  );
}

export function Events({ screen: s }) {
  const [d, err, load] = useGet("/admin/events");
  const replay = async (e) => { try { const { data } = await api.post(`/admin/events/${e.id}/replay`); toast.success(`Replay result: ${data.state}`); load(); } catch (x) { toast.error(errMsg(x)); load(); } };
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      <Card>{!d ? <Loading /> : <DataTable rows={d.items} testid="events-table" empty={{ title: "No failed integration events", body: "Failed deliveries and provider errors appear here for safe replay." }}
        cols={[{ key: "at", label: "Time", render: (e) => fmtDT(e.at) }, { key: "adapter", label: "Adapter" }, { key: "event", label: "Event" }, { key: "error", label: "Error" }, { key: "attempts", label: "Attempts" },
          { key: "state", label: "State", render: (e) => <Badge tone={e.state === "failed" ? "red" : "green"}>{e.state}</Badge> }, { key: "x", label: "", render: (e) => e.state === "failed" && <button className="ce-btn sm" onClick={() => replay(e)} data-testid={`replay-${e.id}`}><RefreshCw />Replay</button> }]} />}</Card>
    </Frame>
  );
}

export function Retention({ screen: s }) {
  const nav = useNavigate();
  const [d, err] = useGet("/admin/retention");
  return (
    <Frame screen={s} actions={<button className="ce-btn primary" onClick={() => nav("/app/s/CE-160")} data-testid="legal-hold-btn"><Plus />Request legal hold</button>}>
      {err && <Notice tone="red">{err}</Notice>}
      {d?.note && <Notice>{d.note}</Notice>}
      <Card title="Retention schedules">{!d ? <Loading /> : <DataTable rows={d.items} testid="retention-table" cols={[{ key: "class", label: "Record class" }, { key: "schedule", label: "Schedule" }, { key: "eligible", label: "Eligible for review" }, { key: "hold_status", label: "Holds" }, { key: "owner", label: "Owner" }, { key: "next_run", label: "Next run" }]} />}</Card>
      <Card title="Legal holds">{d && <DataTable rows={d.holds} onRow={(h) => nav(`/app/r/${h.id}`)} testid="holds-table" cols={[{ key: "ref", label: "Hold" }, { key: "title", label: "Title" }, { key: "state", label: "State" }, { key: "created_at", label: "Requested", render: (h) => fmtDT(h.created_at) }]} />}</Card>
    </Frame>
  );
}

export function AuditLog({ screen: s }) {
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const [d, err] = useGet("/admin/audit", { actor, action, page });
  const exp = async () => { try { await api.post("/exports", { scope: "audit" }); toast.success("Audit export generated - download from Exports"); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <Frame screen={s} actions={<button className="ce-btn" onClick={exp} data-testid="audit-export-btn"><FileDown />Export audit history</button>}>
      {err && <Notice tone="red">{err}</Notice>}
      <Card>
        <div className="flex gap-2 mb-3 flex-wrap">
          <input className="ce-input" style={{ maxWidth: 260 }} placeholder="Actor email" value={actor} onChange={(e) => { setActor(e.target.value); setPage(1); }} data-testid="audit-actor" />
          <input className="ce-input" style={{ maxWidth: 260 }} placeholder="Action e.g. login, action:approve" value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} data-testid="audit-action" />
        </div>
        {!d ? <Loading /> : <><DataTable rows={d.items} testid="audit-table" cols={[{ key: "at", label: "Time", render: (a) => fmtDT(a.at) }, { key: "actor", label: "Actor" }, { key: "role", label: "Role" }, { key: "action", label: "Action" }, { key: "object_type", label: "Object" },
          { key: "object_id", label: "Object ID" }, { key: "outcome", label: "Outcome", render: (a) => <Badge tone={a.outcome === "ok" ? "green" : "red"}>{a.outcome}</Badge> }, { key: "sensitive", label: "Sensitive", render: (a) => (a.sensitive ? <Badge tone="amber">Yes</Badge> : "") }]} />
          <Pager page={page} size={50} total={d.total} onPage={setPage} /></>}
      </Card>
    </Frame>
  );
}

export function Quarantine({ screen: s }) {
  const { role } = useMeta();
  const [d, err, load] = useGet("/evidence/quarantine");
  const req = async (e) => { try { await api.post(`/evidence/${e.id}/request-replacement`); toast.success("Safe replacement requested from the complainant"); load(); } catch (x) { toast.error(errMsg(x)); } };
  return (
    <Frame screen={s}>
      {err && <Notice tone="red">{err}</Notice>}
      <Notice tone="red" title="Quarantined files cannot be opened">Ask the complainant for a safe replacement copy. Quarantined files stay isolated for security review.</Notice>
      <Card>{!d ? <Loading /> : <DataTable rows={d.items} testid="quarantine-table" empty={{ title: "No quarantined evidence", body: "Files failing the security scan appear here." }}
        cols={[{ key: "ref", label: "Record" }, { key: "filename", label: "File" }, { key: "scan_note", label: "Scan result" }, { key: "uploaded_by_name", label: "Uploaded by" }, { key: "at", label: "Uploaded", render: (e) => fmtDT(e.at) },
          { key: "x", label: "", render: (e) => (["R04", "R05"].includes(role) && e.scan_state === "quarantined" ? <button className="ce-btn sm" onClick={() => req(e)} data-testid={`request-replacement-${e.id}`}>Request replacement</button> : <Badge tone="amber">{e.scan_state.replace(/_/g, " ")}</Badge>) }]} />}</Card>
    </Frame>
  );
}
