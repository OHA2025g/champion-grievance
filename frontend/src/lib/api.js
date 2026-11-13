import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config || {};
    if (err.response?.status === 401 && !cfg._retry && !(cfg.url || "").startsWith("/auth/")) {
      cfg._retry = true;
      try {
        refreshing = refreshing || api.post("/auth/refresh");
        await refreshing;
        refreshing = null;
        return api(cfg);
      } catch (e) {
        refreshing = null;
        window.dispatchEvent(new Event("ce-session-expired"));
      }
    }
    return Promise.reject(err);
  }
);

export const errMsg = (e) => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join("; ");
  if (d?.message) return d.message;
  if (!e?.response) return "Network unavailable. Check your connection and retry.";
  return e.message || "Something went wrong";
};
export const errFields = (e) => e?.response?.data?.detail?.fields || {};
export const errCode = (e) => e?.response?.data?.detail?.code;
export const uid = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`);

export async function downloadFile(path, name) {
  const r = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
