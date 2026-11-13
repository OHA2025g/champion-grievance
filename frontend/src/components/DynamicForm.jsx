import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";

export function Lookup({ src, value, onChange, ctx = {}, testid, initialLabel }) {
  const [q, setQ] = useState("");
  const [label, setLabel] = useState(initialLabel || "");
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const box = useRef(null);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(async () => {
      try {
        const { data } = await api.get(`/lookup/${src}`, { params: { q, model_id: ctx.model_id || undefined } });
        setItems(data);
      } catch (e) {
        setItems([]);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [q, open, src, ctx.model_id]);

  useEffect(() => {
    const h = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  if (value && label) {
    return (
      <div className="ce-input flex items-center justify-between" data-testid={testid}>
        <span className="truncate">{label}</span>
        <button type="button" onClick={() => { onChange(""); setLabel(""); }} data-testid={`${testid}-clear`}><X size={14} /></button>
      </div>
    );
  }
  return (
    <div className="relative" ref={box}>
      <div className="relative">
        <Search size={14} className="absolute left-3 top-3 text-slate-400" />
        <input className="ce-input" style={{ paddingLeft: 32 }} value={q} placeholder="Search and select" onFocus={() => setOpen(true)} onChange={(e) => setQ(e.target.value)} data-testid={testid} />
      </div>
      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border rounded-md shadow-lg max-h-60 overflow-auto" data-testid={`${testid}-options`}>
          {items.length === 0 && <div className="p-3 text-xs text-slate-500">No matches</div>}
          {items.map((it, i) => (
            <button type="button" key={it.value} className="block w-full text-left px-3 py-2 hover:bg-blue-50 text-[12.5px]" data-testid={`${testid}-option-${i}`}
              onClick={() => { onChange(it.value); setLabel(it.label); setOpen(false); }}>
              <div className="font-medium text-slate-700">{it.label}</div>
              {it.sub && <div className="text-[11px] text-slate-500">{it.sub}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Field({ f, value, onChange, error, ctx, testid }) {
  const id = testid || `field-${f.k}`;
  const common = { className: "ce-input", value: value ?? "", onChange: (e) => onChange(e.target.value), "data-testid": id };
  let input;
  if (f.t === "select") {
    input = (
      <select {...common}>
        <option value="">Select…</option>
        {f.opts.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  } else if (f.t === "lookup") {
    input = <Lookup src={f.src} value={value} onChange={onChange} ctx={ctx} testid={id} initialLabel={ctx?.labels?.[f.k]} />;
  } else if (["textarea", "lines", "json"].includes(f.t)) {
    input = <textarea {...common} className={`ce-input ${f.t === "json" ? "ce-mono" : ""}`} placeholder={f.t === "json" ? '{ "key": "value" }' : f.t === "lines" ? "One entry per line" : ""} />;
  } else {
    const type = { date: "date", datetime: "datetime-local", number: "number" }[f.t] || "text";
    input = <input {...common} type={type} min={f.min} />;
  }
  const wide = ["textarea", "lines", "json"].includes(f.t);
  return (
    <div className={`ce-field ${error ? "error" : ""} ${wide ? "wide" : ""}`}>
      <label>{f.l}{f.req && <em>*</em>}</label>
      {input}
      {(error || f.hint) && <div className="ce-hint" data-testid={`${id}-hint`}>{error || f.hint}</div>}
    </div>
  );
}

export function validateFields(fields, vals) {
  const errs = {};
  for (const f of fields) {
    const v = vals[f.k];
    const empty = v == null || String(v).trim() === "";
    if (f.req && empty) { errs[f.k] = "This field is required"; continue; }
    if (empty) continue;
    if (f.minlen && String(v).trim().length < f.minlen) errs[f.k] = `Enter at least ${f.minlen} characters`;
    if (f.pattern && !new RegExp(f.pattern).test(String(v))) errs[f.k] = f.hint || "Invalid format";
    if (f.t === "number" && (isNaN(Number(v)) || (f.min != null && Number(v) < f.min))) errs[f.k] = f.min != null ? `Must be ${f.min} or more` : "Enter a number";
    if (f.t === "json") { try { JSON.parse(v); } catch (e) { errs[f.k] = "Enter valid JSON"; } }
  }
  return errs;
}

export function coerce(fields, vals) {
  const out = {};
  for (const f of fields) {
    const v = vals[f.k];
    if (v == null || v === "") continue;
    out[f.k] = f.t === "number" ? Number(v) : f.t === "json" ? JSON.parse(v) : v;
  }
  return out;
}

export function DynamicForm({ fields, values, setValues, errors = {}, ctx, prefix = "field" }) {
  return (
    <div className="ce-form-grid" data-testid={`${prefix}-form`}>
      {fields.map((f) => (
        <Field key={f.k} f={f} value={values[f.k]} error={errors[f.k]} ctx={ctx} testid={`${prefix}-${f.k}`}
          onChange={(v) => setValues((p) => ({ ...p, [f.k]: v }))} />
      ))}
    </div>
  );
}
