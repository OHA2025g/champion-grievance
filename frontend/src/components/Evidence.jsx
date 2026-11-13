import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { UploadCloud, FileText, Download, Loader2 } from "lucide-react";
import { api, errMsg, downloadFile } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Badge, Empty } from "@/components/Common";
import { fmtDT } from "@/lib/fmt";

const CATS = ["Supporting evidence", "Product photo", "Invoice or warranty card", "Serial label", "Service report", "Test readings", "Completion evidence", "Correspondence"];
const SCAN = { clean: "green", quarantined: "red", quarantined_replacement_requested: "amber" };

export function EvidenceList({ items, onChanged }) {
  if (!items?.length) return <Empty title="No evidence yet">Uploaded files are virus-checked and stored with the record.</Empty>;
  return (
    <div data-testid="evidence-list">
      {items.map((e, i) => (
        <div className="ce-file" key={e.id} data-testid={`evidence-item-${i}`}>
          <span className="ce-file-icon"><FileText size={18} /></span>
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-slate-700 truncate">{e.filename}</div>
            <div className="text-[11px] text-slate-500">{e.category} · {Math.max(1, Math.round(e.size / 1024))} KB · {e.uploaded_by_name} · {fmtDT(e.at)}{e.visibility === "internal" ? " · Internal only" : ""}</div>
            {e.scan_state !== "clean" && <div className="text-[11px] text-red-600">{e.scan_note}</div>}
          </div>
          <Badge tone={SCAN[e.scan_state] || "gray"}>{e.scan_state === "clean" ? "Scan clean" : "Quarantined"}</Badge>
          {e.scan_state === "clean" && (
            <button className="ce-btn sm" onClick={() => downloadFile(`/evidence/${e.id}/download`, e.filename).catch((x) => toast.error(errMsg(x)))} data-testid={`evidence-download-${i}`}><Download /></button>
          )}
        </div>
      ))}
    </div>
  );
}

export function EvidencePanel({ record, items: given, onChanged, compact }) {
  const { user } = useAuth();
  const [items, setItems] = useState(given || []);
  const [cat, setCat] = useState(CATS[0]);
  const [vis, setVis] = useState("shared");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const input = useRef(null);
  const external = ["R01", "R02", "R03"].includes(user?.active_role);

  const load = useCallback(async () => {
    const { data } = await api.get(`/records/${record.id}`);
    setItems(data.evidence || []);
  }, [record.id]);

  useEffect(() => {
    if (given) setItems(given); else load().catch(() => {});
  }, [given, load]);

  const upload = async (files) => {
    if (!files?.length) return;
    setBusy(true);
    for (const f of files) {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("category", cat);
      fd.append("visibility", vis);
      try {
        const { data } = await api.post(`/records/${record.id}/evidence`, fd, { headers: { "Content-Type": "multipart/form-data" } });
        if (data.scan_state === "clean") toast.success(`${f.name} uploaded`); else toast.error(`${f.name} quarantined`, { description: data.scan_note });
      } catch (e) {
        toast.error(errMsg(e));
      }
    }
    setBusy(false);
    await load();
    onChanged && onChanged();
  };

  return (
    <div data-testid="evidence-panel">
      <div className="flex gap-3 mb-3 flex-wrap">
        <select className="ce-input" style={{ maxWidth: 240 }} value={cat} onChange={(e) => setCat(e.target.value)} data-testid="evidence-category">{CATS.map((c) => <option key={c}>{c}</option>)}</select>
        {!external && (
          <select className="ce-input" style={{ maxWidth: 200 }} value={vis} onChange={(e) => setVis(e.target.value)} data-testid="evidence-visibility">
            <option value="shared">Shared with complainant</option><option value="internal">Internal only</option>
          </select>
        )}
      </div>
      <div className={`ce-upload ${drag ? "drag" : ""}`} onClick={() => input.current?.click()} data-testid="evidence-dropzone"
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }}>
        {busy ? <Loader2 className="animate-spin mx-auto text-blue-600" /> : <UploadCloud className="mx-auto text-blue-500" size={compact ? 26 : 34} />}
        <div className="ce-h2 mt-2">{busy ? "Uploading and scanning…" : "Drop files or click to upload"}</div>
        <div className="ce-muted">JPG, PNG, PDF, MP4, TXT, CSV, DOCX, XLSX · max 10 MB each · every file is security scanned</div>
        <input ref={input} type="file" multiple hidden onChange={(e) => upload(e.target.files)} data-testid="evidence-file-input" />
      </div>
      <div className="mt-4"><EvidenceList items={items} /></div>
    </div>
  );
}
