import { useParams } from "react-router-dom";
import { useMeta } from "@/context/AuthContext";
import { Notice } from "@/components/Common";
import Dashboard from "@/screens/Dashboard";
import { ListScreen, CreateScreen, RecordScreen, UploadScreen } from "@/screens/Records";
import { MDashboard, MJobs, MJob, MSync } from "@/screens/Mobile";
import { Kanban, CalendarScreen, SlaBoard } from "@/screens/Boards";
import { CustomerSearch, Orders, Roster, Capacity, NetworkScreen, Stock, Movements, Knowledge } from "@/screens/Ops";
import { Analytics, Exports } from "@/screens/Analytics";
import { AdminUsers, Invite, Permissions, Models, AdminConfig, Integrations, Events, Retention, AuditLog, Quarantine } from "@/screens/Admin";
import { Forbidden, IntegrationError, Components, Prefs, Unmapped } from "@/screens/Misc";

const KINDS = {
  dashboard: Dashboard, list: ListScreen, create: CreateScreen, record: RecordScreen, upload: UploadScreen,
  m_dashboard: MDashboard, m_jobs: MJobs, m_job: MJob, m_sync: MSync,
  kanban: Kanban, calendar: CalendarScreen, sla: SlaBoard,
  customer_search: CustomerSearch, orders: Orders, roster: Roster, capacity: Capacity, network: NetworkScreen, stock: Stock, movements: Movements, knowledge: Knowledge,
  analytics: Analytics, exports: Exports,
  admin_users: AdminUsers, invite: Invite, admin_permissions: Permissions, models: Models, admin_config: AdminConfig, admin_integrations: Integrations,
  admin_events: Events, admin_retention: Retention, admin_audit: AuditLog, quarantine_evidence: Quarantine,
  forbidden: Forbidden, integration_error: IntegrationError, components: Components, prefs: Prefs,
};

export default function ScreenHost() {
  const { sid, rid } = useParams();
  const m = useMeta();
  const s = m.byId?.[sid];
  if (!s) return <Notice tone="red" testid="screen-not-found">Screen {sid} does not exist.</Notice>;
  if (["login", "otp", "recover"].includes(s.kind)) return <Notice tone="blue">This screen is shown before sign-in.</Notice>;
  if (s.role !== "shared" && s.role !== m.role) return <Forbidden screen={s} blocked={s} />;
  const C = KINDS[s.kind] || Unmapped;
  return <C key={sid} screen={s} rid={rid} />;
}
