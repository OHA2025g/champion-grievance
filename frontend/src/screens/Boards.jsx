import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, ChevronLeft, ChevronRight, Play, FastForward } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, Loading, Notice, StateBadge } from "@/components/Common";
import { CreateDialog } from "@/components/ActionDialog";
import { Frame } from "@/components/Frame";
import { fmtDT, fmtD } from "@/lib/fmt";

export function Kanban({ screen: s }) {
  const { wf, role } = useMeta();
  const nav = useNavigate();
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const load = useCallback(() => api.get("/records", { params: { type: s.t, size: 100, sort: "-updated_at" } }).then((r) => setItems(r.data.items)).catch((e) => { setItems([]); toast.error(errMsg(e)); }), [s.t]);
  useEffect(() => { load(); }, [load]);
  const [ct, csub] = (s.create_type || "").split("/");
  const canCreate = s.create_type && wf[ct]?.create?.[csub]?.roles.includes(role);
  const states = Object.entries(wf[s.t].states).filter(([k, v]) => !v.terminal || (items || []).some((i) => i.state === k));
  return (
    <Frame screen={s} actions={<>
      {s.create_screen && <button className="ce-btn primary" onClick={() => nav(`/app/s/${s.create_screen}`)} data-testid="kanban-create-btn"><Plus />Create linked work</button>}
      {canCreate && <button className="ce-btn primary" onClick={() => setOpen(true)} data-testid="kanban-create-btn"><Plus />New {wf[ct].create[csub].label.toLowerCase()}</button>}
    </>}>
      {!items ? <Card><Loading /></Card> : (
        <div className="ce-kanban" data-testid="kanban-board">
          {states.map(([k, v]) => {
            const col = items.filter((i) => i.state === k);
            return (
              <div className="ce-col" key={k} data-testid={`kanban-col-${k}`}>
                <div className="ce-col-title"><span>{v.label}</span><span className="ce-badge gray">{col.length}</span></div>
                {col.map((i) => (
                  <div className="ce-taskcard" key={i.id} onClick={() => nav(`/app/r/${i.id}`)} data-testid={`kanban-card-${i.ref}`}>
                    <div className="flex justify-between"><span className="ce-mono text-blue-700 font-semibold">{i.ref}</span>{i.data?.mandatory === "Yes" && <Badge tone="red">Mandatory</Badge>}</div>
                    <div className="font-semibold text-slate-700 my-1.5">{i.title}</div>
                    <div className="text-[10.5px] text-slate-500">{i.assignee_name || i.owner_name || "Unassigned"}{i.data?.due ? ` · due ${fmtD(i.data.due)}` : ""}</div>
                    {i.root_ref && <div className="text-[10.5px] text-slate-400 mt-1">Case {i.root_ref}</div>}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      )}
      {canCreate && <CreateDialog open={open} onClose={() => setOpen(false)} type={ct} sub={csub} onCreated={() => load()} />}
    </Frame>
  );
}

const monday = (d) => { const x = new Date(d); const day = (x.getDay() + 6) % 7; x.setDate(x.getDate() - day); x.setHours(0, 0, 0, 0); return x; };
export function CalendarScreen({ screen: s }) {
  const nav = useNavigate();
  const { wf } = useMeta();
  const [d, setD] = useState(null);
  const [start, setStart] = useState(monday(new Date()));
  useEffect(() => { api.get("/appointments").then((r) => setD(r.data)).catch((e) => toast.error(errMsg(e))); }, []);
  const days = Array.from({ length: 7 }, (_, i) => { const x = new Date(start); x.setDate(x.getDate() + i); return x; });
  const key = (x) => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
  const tone = { appointment_confirmed: "green", appointment_proposed: "amber" };
  const shift = (n) => { const x = new Date(start); x.setDate(x.getDate() + n); setStart(x); };
  return (
    <Frame screen={s} actions={<><button className="ce-btn" onClick={() => shift(-7)} data-testid="cal-prev"><ChevronLeft /></button><span className="ce-badge outline">{fmtD(days[0])} – {fmtD(days[6])}</span><button className="ce-btn" onClick={() => shift(7)} data-testid="cal-next"><ChevronRight /></button></>}>
      {!d ? <Card><Loading /></Card> : (
        <>
          <div className="overflow-x-auto mb-4">
            <div className="ce-calendar" data-testid="calendar-grid">
              {days.map((x) => <div key={key(x)} className="ce-cal-head">{x.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" })}</div>)}
              {days.map((x) => (
                <div key={`c${key(x)}`} className="ce-cal-cell">
                  {d.items.filter((j) => (j.appointment?.start || "").startsWith(key(x))).map((j) => (
                    <div key={j.id} className={`ce-cal-event ${tone[j.state] || ""}`} onClick={() => nav(`/app/r/${j.id}`)} data-testid={`cal-event-${j.ref}`}>
                      <b>{j.appointment.start.slice(11, 16)}</b> {j.ref}<br />{j.customer_name} · {j.technician_name || "Unallocated"}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <Card title="Jobs to schedule" sub="Allocated or missed visits without a confirmed window">
            <DataTable rows={d.to_schedule} onRow={(j) => nav(`/app/r/${j.id}`)} testid="to-schedule-table"
              cols={[{ key: "ref", label: "Job" }, { key: "customer_name", label: "Customer" }, { key: "technician_name", label: "Technician" }, { key: "centre_name", label: "Centre" }, { key: "state", label: "State", render: (j) => <StateBadge wf={wf} type="job" state={j.state} /> }]} />
          </Card>
        </>
      )}
    </Frame>
  );
}

export function SlaBoard({ screen: s }) {
  const nav = useNavigate();
  const m = useMeta();
  const [rows, setRows] = useState(null);
  const load = useCallback(() => api.get("/sla/clocks").then((r) => setRows(r.data.items)).catch((e) => toast.error(errMsg(e))), []);
  useEffect(() => { load(); }, [load]);
  const age = async (id) => { try { await api.post("/dev/sla/age", { record_id: id, minutes: 240 }); toast.success("Simulated 4 hours of elapsed time"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const run = async () => { try { await api.post("/admin/sla/run"); toast.success("SLA evaluation completed"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const tone = { Breached: "red", "At risk": "amber", "On track": "green" };
  const cols = [{ key: "ref", label: "Case" }, { key: "milestone", label: "Milestone", render: (r) => r.milestone.replace(/_/g, " ") }, { key: "owner_name", label: "Owner" }, { key: "due", label: "Due", render: (r) => fmtDT(r.due) },
    { key: "state", label: "Clock", render: (r) => <Badge tone={r.state === "paused" ? "gray" : ""}>{r.state}</Badge> }, { key: "waiting_reason", label: "Waiting reason" }, { key: "risk", label: "Risk", render: (r) => <Badge tone={tone[r.risk]}>{r.risk}</Badge> },
    ...(m.dev_mode ? [{ key: "dev", label: "Dev", render: (r) => <button className="ce-btn sm" onClick={(e) => { e.stopPropagation(); age(r.id); }} data-testid={`sla-age-${r.ref}-${r.milestone}`}><FastForward />+4h</button> }] : [])];
  return (
    <Frame screen={s} actions={["R09", "R10", "R18"].includes(m.role) && <button className="ce-btn" onClick={run} data-testid="sla-run-btn"><Play />Run SLA check</button>}>
      <Notice tone="blue">Clocks use the configured business calendar. Paused clocks only resume when the approved waiting reason clears. {m.dev_mode && "DEV: '+4h' simulates elapsed time for testing breach and escalation."}</Notice>
      <Card>{!rows ? <Loading /> : <DataTable cols={cols} rows={rows} onRow={(r) => nav(`/app/r/${r.id}`)} testid="sla-table" />}</Card>
    </Frame>
  );
}
