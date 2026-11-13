import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

const Ctx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [meta, setMeta] = useState(null);
  const [ready, setReady] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/meta");
      setMeta(data);
      setUser(data.user);
      return data;
    } catch (e) {
      setUser(null);
      setMeta(null);
      return null;
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    if (window.location.hash.includes("session_id=")) {
      setReady(true);
      return;
    }
    load();
  }, [load]);

  useEffect(() => {
    const h = () => { setUser(null); setMeta(null); };
    window.addEventListener("ce-session-expired", h);
    return () => window.removeEventListener("ce-session-expired", h);
  }, []);

  const value = useMemo(() => ({
    user, meta, ready, reload: load,
    login: async (email, password) => { await api.post("/auth/login", { email, password }); return load(); },
    devLogin: async (role) => { await api.post("/auth/dev-login", { role }); return load(); },
    switchRole: async (role) => { await api.post("/auth/switch-role", { role }); return load(); },
    logout: async () => { try { await api.post("/auth/logout"); } finally { setUser(null); setMeta(null); } },
  }), [user, meta, ready, load]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export function useMeta() {
  const { meta, user } = useAuth();
  return useMemo(() => {
    if (!meta) return {};
    const byId = Object.fromEntries(meta.screens.map((s) => [s.id, s]));
    const role = user?.active_role;
    const roleScreens = meta.screens.filter((s) => s.role === role);
    return { ...meta, byId, role, roleScreens, wf: meta.workflows, roleInfo: meta.roles[role] };
  }, [meta, user]);
}
