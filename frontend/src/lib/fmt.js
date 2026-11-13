export const get = (o, path) => path.split(".").reduce((a, k) => (a == null ? a : a[k]), o);

export const fmtDT = (s) => {
  if (!s) return "—";
  const d = new Date(s.length === 16 ? s : s);
  if (isNaN(d)) return s;
  return d.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};
export const fmtD = (s) => {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d)) return s;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};
export const rel = (s) => {
  if (!s) return "";
  const m = Math.round((Date.now() - new Date(s).getTime()) / 60000);
  if (Math.abs(m) < 1) return "just now";
  const f = (v, u) => (v > 0 ? `${v} ${u} ago` : `in ${-v} ${u}`);
  if (Math.abs(m) < 60) return f(m, "min");
  const h = Math.round(m / 60);
  if (Math.abs(h) < 48) return f(h, "h");
  return f(Math.round(h / 24), "d");
};
export const inr = (v) => (v == null || v === "" ? "—" : `INR ${Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`);
export const humanize = (k) => k.replace(/^data\./, "").replace(/_label$/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const initials = (n = "") => n.split(" ").filter(Boolean).slice(0, 2).map((x) => x[0]).join("").toUpperCase();
export const TONE = { info: "", pending: "amber", urgent: "red", blocked: "amber", done: "green", muted: "gray" };
export const SLA_TONE = { breached: "red", warning: "amber", on_track: "green", met: "green", paused: "gray" };

export const fmtVal = (v) => {
  if (v == null || v === "") return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (Array.isArray(v)) return v.map((x) => (typeof x === "object" ? x.ref || x.label || JSON.stringify(x) : x)).join(", ");
  if (typeof v === "object") return v.start ? `${fmtDT(v.start)} – ${fmtDT(v.end)}` : JSON.stringify(v);
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(v)) return fmtDT(v);
  return String(v);
};

export const nextDue = (rec) => {
  const open = (rec?.sla || []).filter((k) => k.state === "running" || k.state === "paused");
  open.sort((a, b) => (a.due < b.due ? -1 : 1));
  return open[0];
};
