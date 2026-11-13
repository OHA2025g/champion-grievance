import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Bell, Search, Menu, LogOut, Settings2, LayoutGrid, List, FilePlus2, FileText, Upload, KanbanSquare, CalendarDays, Timer, BarChart3, Settings, Users, ShieldCheck, Package, Truck, BookOpen, Download, Network, Gauge, AlertOctagon, Boxes, Wrench, RefreshCw, UserCircle2, FlaskConical } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { api, errMsg } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { initials, rel } from "@/lib/fmt";

const ICON = { dashboard: LayoutGrid, list: List, create: FilePlus2, record: FileText, upload: Upload, kanban: KanbanSquare, calendar: CalendarDays, sla: Timer, analytics: BarChart3,
  admin_users: Users, invite: Users, admin_permissions: ShieldCheck, admin_config: Settings, admin_integrations: Network, admin_events: RefreshCw, admin_retention: Boxes, admin_audit: ShieldCheck,
  stock: Package, movements: Truck, knowledge: BookOpen, exports: Download, capacity: Gauge, network: Network, roster: Users, orders: Boxes, customer_search: Search, forbidden: AlertOctagon,
  integration_error: AlertOctagon, quarantine_evidence: ShieldCheck, models: Package, m_dashboard: LayoutGrid, m_jobs: List, m_job: Wrench, m_sync: RefreshCw, prefs: Settings2, components: FlaskConical };
const HIDDEN = ["CE-001", "CE-002", "CE-003"];

function NavList({ screens, onNav }) {
  return screens.map((s) => {
    const I = ICON[s.kind] || FileText;
    return (
      <NavLink key={s.id} to={`/app/s/${s.id}`} onClick={onNav} className={({ isActive }) => `ce-nav ${isActive ? "active" : ""}`} data-testid={`nav-${s.id}`}>
        <I /><span>{s.title}</span>
      </NavLink>
    );
  });
}

function Sidebar({ onNav }) {
  const { user } = useAuth();
  const m = useMeta();
  const shared = m.screens.filter((s) => s.role === "shared" && !HIDDEN.includes(s.id));
  return (
    <aside className="ce-sidebar" data-testid="sidebar">
      <div className="ce-brand">CHAMPION<small>SERVICE DESK</small></div>
      <div className="ce-sidebar-scroll">
        <div className="ce-side-label">{m.roleInfo?.workspace || "Workspace"}</div>
        <NavList screens={m.roleScreens} onNav={onNav} />
        <div className="ce-side-label">Support</div>
        <NavList screens={shared} onNav={onNav} />
      </div>
      <div className="ce-side-foot">
        <div className="ce-avatar">{initials(user.name)}</div>
        <div className="min-w-0"><div className="text-white font-semibold truncate">{user.name}</div><div className="truncate">{m.roleInfo?.name}</div></div>
      </div>
    </aside>
  );
}

function Notifications() {
  const [d, setD] = useState({ items: [], unread: 0 });
  const nav = useNavigate();
  const load = () => api.get("/notifications").then((r) => setD(r.data)).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 45000); return () => clearInterval(t); }, []);
  return (
    <Popover onOpenChange={(o) => { if (!o && d.unread) api.post("/notifications/read").then(load); }}>
      <PopoverTrigger asChild>
        <button className="relative p-2 rounded-md hover:bg-slate-100" data-testid="notifications-btn">
          <Bell size={18} />
          {d.unread > 0 && <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[9px] rounded-full min-w-[16px] h-4 grid place-items-center px-1" data-testid="notifications-unread">{d.unread}</span>}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0" data-testid="notifications-panel">
        <div className="px-4 py-3 border-b font-semibold text-sm">Notifications</div>
        <div className="max-h-96 overflow-auto">
          {!d.items.length && <div className="p-4 text-xs text-slate-500">No notifications.</div>}
          {d.items.map((n) => (
            <button key={n.id} className={`block w-full text-left px-4 py-3 border-b hover:bg-slate-50 ${n.read ? "" : "bg-blue-50/50"}`} onClick={() => n.record_id && nav(`/app/r/${n.record_id}`)} data-testid={`notification-${n.id}`}>
              <div className="text-[12.5px] font-semibold text-slate-700">{n.title}</div>
              <div className="text-[11.5px] text-slate-500 line-clamp-2">{n.body}</div>
              <div className="text-[10.5px] text-slate-400 mt-1">{rel(n.at)}</div>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

export function RoleControls({ compact }) {
  const { user, switchRole, devLogin } = useAuth();
  const m = useMeta();
  const nav = useNavigate();
  const go = async (fn, v) => { try { await fn(v); nav("/app"); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className={`flex gap-2 items-center ${compact ? "flex-col items-stretch" : ""}`}>
      {user.roles.length > 1 && (
        <select className="ce-input" style={{ minHeight: 34, padding: "5px 28px 5px 10px", fontSize: 12, width: compact ? "100%" : 210 }} value={user.active_role} onChange={(e) => go(switchRole, e.target.value)} data-testid="role-switch">
          {user.roles.map((r) => <option key={r} value={r}>{r} · {m.roles[r]?.name}</option>)}
        </select>
      )}
      {m.dev_switcher && (
        <select className="ce-input" style={{ minHeight: 34, padding: "5px 28px 5px 10px", fontSize: 12, width: compact ? "100%" : 190, borderColor: "#e9bd5b", background: "#fffaf0" }} value="" onChange={(e) => go(devLogin, e.target.value)} data-testid="dev-role-switcher">
          <option value="">DEV · switch demo role</option>
          {Object.entries(m.roles).map(([k, v]) => <option key={k} value={k}>{k} · {v.name}</option>)}
        </select>
      )}
    </div>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const m = useMeta();
  const nav = useNavigate();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><button className="ce-avatar" data-testid="user-menu-btn">{initials(user.name)}</button></DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel><div className="text-sm">{user.name}</div><div className="text-xs text-slate-500 font-normal">{user.email}</div><div className="text-xs text-blue-700 font-normal">{m.roleInfo?.name}</div></DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => nav("/app/s/CE-004")} data-testid="menu-preferences"><Settings2 size={14} className="mr-2" />Notifications and preferences</DropdownMenuItem>
        <DropdownMenuItem onClick={async () => { await logout(); nav("/login"); }} data-testid="logout-btn"><LogOut size={14} className="mr-2" />Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Topbar({ onMenu }) {
  const m = useMeta();
  const loc = useLocation();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const sid = loc.pathname.split("/")[3];
  const s = m.byId[sid];
  return (
    <header className="ce-topbar" data-testid="topbar">
      <div className="flex items-center gap-3 min-w-0">
        <button className="lg:hidden p-1" onClick={onMenu} data-testid="mobile-menu-btn"><Menu size={20} /></button>
        <div className="truncate"><span>{m.roleInfo?.workspace}</span>{s && <><span className="mx-2 text-slate-300">/</span><span className="text-slate-700">{s.title}</span></>}</div>
      </div>
      <div className="flex items-center gap-3">
        <form className="ce-search" onSubmit={(e) => { e.preventDefault(); if (q.trim()) nav(`/app/search?q=${encodeURIComponent(q.trim())}`); }}>
          <Search size={15} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search permitted records" data-testid="global-search" />
        </form>
        <div className="hidden md:flex"><RoleControls /></div>
        <Notifications />
        <UserMenu />
      </div>
    </header>
  );
}

const MOBILE_NAV = [["CE-042", "Today", LayoutGrid], ["CE-043", "Jobs", List], ["CE-051", "Drafts", RefreshCw], ["CE-004", "Profile", UserCircle2]];
function MobileShell() {
  const m = useMeta();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  return (
    <div className="ce-mobile" data-testid="mobile-shell">
      <div className="ce-mobile-header">
        <div className="ce-mobile-brand"><span>CHAMPION / FIELD SERVICE</span>
          <div className="flex gap-2 items-center"><Notifications /><button onClick={() => setOpen(true)} data-testid="mobile-menu-btn"><Menu size={20} /></button></div>
        </div>
      </div>
      <Outlet />
      <nav className="ce-mobile-nav" data-testid="mobile-bottom-nav">
        {MOBILE_NAV.map(([id, l, I]) => <NavLink key={id} to={`/app/s/${id}`} className={loc.pathname.includes(id) ? "on" : ""} data-testid={`mnav-${id}`}><I size={19} />{l}</NavLink>)}
      </nav>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="ce-sheet w-80 p-0 bg-[#101e34] border-0 flex flex-col"><div className="flex-1 min-h-0"><Sidebar onNav={() => setOpen(false)} /></div><div className="p-3 border-t border-[#2b394e]"><RoleControls compact /></div></SheetContent>
      </Sheet>
    </div>
  );
}

export default function Shell() {
  const { user } = useAuth();
  const m = useMeta();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  if (user.active_role === "R06") return <MobileShell />;
  const sid = loc.pathname.split("/")[3];
  const s = m.byId[sid];
  return (
    <div className="ce-app">
      <Sidebar />
      <main className="min-w-0">
        <Topbar onMenu={() => setOpen(true)} />
        <div className="ce-workspace"><Outlet />
          <div className="ce-footer"><span>Champion Electricals · Service Desk{s ? ` · ${s.id} · ${s.fr}` : ""}</span><span>Records marked "Demo data" are synthetic seed records</span></div>
        </div>
      </main>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="ce-sheet w-72 p-0 bg-[#101e34] border-0 flex flex-col" data-testid="mobile-sidebar"><div className="flex-1 min-h-0"><Sidebar onNav={() => setOpen(false)} /></div><div className="p-3 md:hidden border-t border-[#2b394e]"><RoleControls compact /></div></SheetContent>
      </Sheet>
    </div>
  );
}
