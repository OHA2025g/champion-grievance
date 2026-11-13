import { Info, AlertTriangle, ShieldAlert, CheckCircle2, ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { TONE, SLA_TONE, fmtDT, fmtVal, get, inr } from "@/lib/fmt";

export const PageHead = ({ eyebrow, title, sub, children, testid = "page-head" }) => (
  <div className="ce-pagehead" data-testid={testid}>
    <div className="min-w-0">
      {eyebrow && <div className="ce-eyebrow">{eyebrow}</div>}
      <h1 className="ce-h1" data-testid="page-title">{title}</h1>
      {sub && <div className="ce-sub">{sub}</div>}
    </div>
    {children && <div className="flex gap-2 items-center flex-wrap">{children}</div>}
  </div>
);

export const Badge = ({ tone = "", children, testid }) => <span className={`ce-badge ${tone}`} data-testid={testid}>{children}</span>;

export const StateBadge = ({ wf, type, state, testid }) => {
  const s = wf?.[type]?.states?.[state];
  return <Badge tone={TONE[s?.tone] ?? ""} testid={testid || "state-badge"}>{s?.label || state || "—"}</Badge>;
};

export const SlaBadge = ({ state }) => (state ? <Badge tone={SLA_TONE[state] || "gray"} testid="sla-badge">SLA {state.replace("_", " ")}</Badge> : null);

const ICONS = { blue: Info, red: ShieldAlert, green: CheckCircle2, gray: Info, "": AlertTriangle };
export const Notice = ({ tone = "", title, children, testid, right }) => {
  const I = ICONS[tone] || Info;
  return (
    <div className={`ce-notice ${tone}`} data-testid={testid}>
      <I />
      <div className="flex-1 min-w-0">{title && <strong>{title}</strong>}{children}</div>
      {right}
    </div>
  );
};

export const Card = ({ title, sub, right, children, className = "", testid, style }) => (
  <div className={`ce-card ${className}`} data-testid={testid} style={style}>
    {(title || right) && (
      <div className="ce-cardhead">
        <div>{title && <h2 className="ce-h2">{title}</h2>}{sub && <div className="ce-muted">{sub}</div>}</div>
        {right}
      </div>
    )}
    {children}
  </div>
);

export const KV = ({ k, v, testid }) => (
  <div className="ce-kv" data-testid={testid}><span>{k}</span><b>{v ?? "—"}</b></div>
);

export const Empty = ({ title = "Nothing here yet", children, testid = "empty-state" }) => (
  <div className="text-center py-10 px-4" data-testid={testid}>
    <div className="ce-status-symbol" style={{ width: 54, height: 54, marginBottom: 14 }}><Inbox size={22} /></div>
    <div className="ce-h2">{title}</div>
    <div className="ce-muted max-w-md mx-auto mt-1">{children}</div>
  </div>
);

export const Loading = ({ rows = 4 }) => (
  <div data-testid="loading">{Array.from({ length: rows }).map((_, i) => <div key={i} className="ce-skel" style={{ width: `${90 - i * 12}%` }} />)}</div>
);

export const Kpi = ({ label, value, sub, icon: Icon, onClick, testid, style }) => (
  <div className="ce-kpi" onClick={onClick} data-testid={testid} style={style}>
    <div className="ce-kpi-top"><span>{label}</span>{Icon && <span className="ce-kpi-icon"><Icon /></span>}</div>
    <div className="ce-kpi-value" data-testid={testid ? `${testid}-value` : undefined}>{value ?? "—"}</div>
    {sub && <div className="ce-kpi-sub">{sub}</div>}
  </div>
);

export const Pager = ({ page, size, total, onPage }) => {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex justify-between items-center pt-3 text-[11px] text-slate-500" data-testid="pager">
      <span>Showing {total ? (page - 1) * size + 1 : 0}–{Math.min(page * size, total)} of {total} permitted records</span>
      <div className="flex gap-1.5">
        <button className="ce-btn sm" disabled={page <= 1} onClick={() => onPage(page - 1)} data-testid="pager-prev"><ChevronLeft /></button>
        <span className="ce-badge outline">{page} / {pages}</span>
        <button className="ce-btn sm" disabled={page >= pages} onClick={() => onPage(page + 1)} data-testid="pager-next"><ChevronRight /></button>
      </div>
    </div>
  );
};

const DATE_KEYS = ["created_at", "updated_at", "closed_at", "appointment.start", "sla_due", "due", "at", "last_activity", "expires_at"];
export function renderCell(row, key, wf) {
  if (key === "state") return <StateBadge wf={wf} type={row.type} state={row.state} />;
  if (key === "sla_state") return <SlaBadge state={row.sla_state} />;
  if (key === "amount") return inr(row.amount);
  if (key === "sla_due") return fmtDT((row.sla || []).find((k) => k.state === "running")?.due || row.sla_due);
  if (DATE_KEYS.includes(key)) return fmtDT(get(row, key));
  if (key.startsWith("data.")) {
    const k = key.slice(5);
    return fmtVal(row.data?.[`${k}_label`] ?? row.data?.[k]);
  }
  return fmtVal(get(row, key));
}

export function DataTable({ cols, rows, onRow, testid = "data-table", empty }) {
  if (!rows?.length) return <Empty title={empty?.title || "No records in this view"}>{empty?.body || "Records appear here when they enter this stage of the workflow."}</Empty>;
  return (
    <div className="ce-table-wrap" data-testid={testid}>
      <table className="ce-table">
        <thead><tr>{cols.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id || i} className={onRow ? "clickable" : ""} onClick={() => onRow && onRow(r)} data-testid={`${testid}-row-${i}`}>
              {cols.map((c, j) => <td key={c.key} className={j === 0 ? "ref" : ""}>{c.render ? c.render(r) : fmtVal(get(r, c.key))}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const DemoTag = ({ show }) => (show ? <Badge tone="outline" testid="demo-tag">Demo data</Badge> : null);
