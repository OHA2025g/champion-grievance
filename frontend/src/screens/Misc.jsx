import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Lock, PlugZap, LogOut, ArrowRight } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { Badge, Card, DataTable, Kpi, KV, Notice, StateBadge } from "@/components/Common";
import { Frame } from "@/components/Frame";
import { DynamicForm } from "@/components/DynamicForm";
import { RoleControls } from "@/components/Shell";

export function Forbidden({ screen, blocked }) {
  const m = useMeta();
  const nav = useNavigate();
  return (
    <div className="ce-status-page" data-testid="forbidden-page">
      <div className="ce-status-symbol"><Lock size={30} /></div>
      <div className="ce-eyebrow">CE-142 · Access controlled</div>
      <h2 className="text-2xl font-semibold text-slate-800">You do not have access to this function</h2>
      <p className="ce-sub mt-3">{blocked ? `"${blocked.title}" (${blocked.id}) belongs to the ${m.roles[blocked.role]?.name || "another"} workspace.` : "This function is outside your role's permitted scope."} The attempt has been recorded. If you need access, ask your administrator with an approval reference.</p>
      <button className="ce-btn primary mt-5" onClick={() => nav("/app")} data-testid="return-workspace-btn"><ArrowRight />Return to my workspace</button>
    </div>
  );
}

export function IntegrationError({ screen }) {
  const { role } = useMeta();
  const nav = useNavigate();
  const [rows, setRows] = useState(null);
  useEffect(() => { if (role === "R18") api.get("/admin/integrations").then((r) => setRows(r.data.items.filter((x) => x.health !== "Healthy"))).catch(() => setRows([])); }, [role]);
  return (
    <div data-testid="integration-error-page">
      <div className="ce-status-page">
        <div className="ce-status-symbol"><PlugZap size={30} /></div>
        <div className="ce-eyebrow">CE-145 · Service status</div>
        <h2 className="text-2xl font-semibold text-slate-800">A connected service is unavailable</h2>
        <p className="ce-sub mt-3">Your work has been saved. Messages and provider steps that could not complete are queued for safe retry and never reported as sent.</p>
        <div className="flex gap-2 justify-center mt-5"><button className="ce-btn primary" onClick={() => window.location.reload()} data-testid="retry-btn">Retry</button>{role === "R18" && <button className="ce-btn" onClick={() => nav("/app/s/CE-124")} data-testid="open-events-btn">Open failed events</button>}</div>
      </div>
      {rows && <Card title="Integrations needing attention"><DataTable rows={rows} testid="unhealthy-table" cols={[{ key: "adapter", label: "Adapter" }, { key: "mode", label: "Mode" }, { key: "health", label: "Health" }, { key: "note", label: "Note" }]} /></Card>}
    </div>
  );
}

export function Components({ screen }) {
  const { wf } = useMeta();
  const [v, setV] = useState({ ok: "Air cooler", bad: "" });
  return (
    <Frame screen={screen}>
      <div className="ce-two equal">
        <Card title="Actions">
          <div className="flex gap-2 flex-wrap"><button className="ce-btn primary">Primary action</button><button className="ce-btn">Secondary</button><button className="ce-btn danger">Destructive</button><button className="ce-btn" disabled>Disabled</button><button className="ce-btn sm">Small</button></div>
        </Card>
        <Card title="Status badges">
          <div className="flex gap-2 flex-wrap">{["", "green", "amber", "red", "gray", "outline"].map((t) => <Badge key={t} tone={t}>{t || "info"}</Badge>)}</div>
        </Card>
      </div>
      <Card title="Notices">
        <Notice tone="blue" title="Information">Next action and accountable owner.</Notice><Notice title="Warning">Approaching SLA breach.</Notice>
        <Notice tone="red" title="Error / safety">Hazard reported - escalate immediately.</Notice><Notice tone="green" title="Success">Outcome verified.</Notice>
      </Card>
      <div className="ce-two equal">
        <Card title="Form fields">
          <DynamicForm prefix="demo" values={v} setValues={setV} errors={{ bad: "This field is required" }} fields={[{ k: "ok", l: "Valid field", req: true }, { k: "bad", l: "Field with error", req: true }, { k: "sel", l: "Select", t: "select", opts: ["Option A", "Option B"] }, { k: "dt", l: "Date", t: "date" }]} />
        </Card>
        <Card title="KPI"><div className="ce-kpis" style={{ gridTemplateColumns: "1fr 1fr" }}><Kpi label="Open cases" value={24} sub="Within scope" /><Kpi label="Breached" value={2} sub="Requires recovery" /></div></Card>
      </div>
      <Card title="Case state reference">{Object.entries(wf.case.states).map(([k, s]) => <KV key={k} k={<StateBadge wf={wf} type="case" state={k} />} v={s.next || "Terminal state"} />)}</Card>
    </Frame>
  );
}

const PREF_FIELDS = [{ k: "language", l: "Language", t: "select", opts: ["English", "हिन्दी (Hindi)"] }, { k: "contact_channel", l: "Preferred channel", t: "select", opts: ["Email", "SMS", "WhatsApp", "Phone call", "Portal message"] },
  { k: "timezone", l: "Time zone", t: "select", opts: ["Asia/Kolkata"] }, { k: "service_updates", l: "Service updates", t: "select", opts: ["All updates", "Important updates only", "Portal only"] },
  { k: "appointment_reminder", l: "Appointment reminder", t: "select", opts: ["24 hours before", "2 hours before", "No reminder"] }, { k: "accessibility", l: "Accessibility", t: "select", opts: ["Standard", "Large text", "High contrast"] }];

export function Prefs({ screen }) {
  const { user, logout, reload } = useAuth();
  const nav = useNavigate();
  const [v, setV] = useState({ language: "English", contact_channel: "Email", timezone: "Asia/Kolkata", service_updates: "All updates", appointment_reminder: "24 hours before", accessibility: "Standard", ...(user.preferences || {}) });
  const save = async () => { try { await api.put("/auth/preferences", v); toast.success("Preferences saved"); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className={user.active_role === "R06" ? "ce-mobile-content" : ""}>
      <Frame screen={screen}>
        <div className="ce-two">
          <Card title="Notifications and preferences" sub="Mock SMS and WhatsApp adapters are clearly labelled until real providers are configured">
            <DynamicForm fields={PREF_FIELDS} values={v} setValues={setV} prefix="pref" />
            {v.language.startsWith("हिन्दी") && <div className="ce-step-block mt-3" lang="hi">आपकी शिकायत दर्ज कर ली गई है। हम आपको हर अपडेट भेजेंगे।</div>}
            <div className="ce-actions"><button className="ce-btn primary" onClick={save} data-testid="prefs-save">Save preferences</button></div>
          </Card>
          <Card title="My account">
            <KV k="Name" v={user.name} /><KV k="Email" v={user.email} /><KV k="Active role" v={user.active_role} /><KV k="Account type" v={user.demo ? "Demo account" : "Provisioned account"} />
            <div className="mt-4"><RoleControls compact /></div>
            <button className="ce-btn mt-4 w-full justify-center" onClick={async () => { await logout(); nav("/login"); }} data-testid="prefs-logout"><LogOut />Sign out</button>
          </Card>
        </div>
      </Frame>
    </div>
  );
}

export function Unmapped({ screen }) {
  return <Frame screen={screen}><Notice tone="red">This screen is not configured.</Notice></Frame>;
}
