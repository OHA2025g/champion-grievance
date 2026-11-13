import { useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, errMsg, errFields, uid } from "@/lib/api";
import { useAuth, useMeta } from "@/context/AuthContext";
import { DynamicForm, validateFields, coerce } from "@/components/DynamicForm";
import { Notice } from "@/components/Common";
import { EvidencePanel } from "@/components/Evidence";

export const DRAFTS_KEY = "ce-offline-drafts";
export const readDrafts = () => JSON.parse(localStorage.getItem(DRAFTS_KEY) || "[]");
export const writeDrafts = (d) => localStorage.setItem(DRAFTS_KEY, JSON.stringify(d));

export function ActionForm({ record, action, onDone, onCancel, inline }) {
  const { user } = useAuth();
  const [values, setValues] = useState({});
  const [errors, setErrors] = useState({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [idem] = useState(uid());

  const submit = async () => {
    const v = validateFields(action.fields, values);
    setErrors(v);
    if (Object.keys(v).length) { setErr("Please correct the highlighted fields."); return; }
    setBusy(true);
    setErr("");
    const payload = { values: coerce(action.fields, values), expected_version: record.version };
    try {
      const { data } = await api.post(`/records/${record.id}/actions/${action.key}`, payload, { headers: { "Idempotency-Key": idem } });
      toast.success(`${action.label} recorded`, { description: `${record.ref} is now ${data.state.replace(/_/g, " ")}` });
      onDone && onDone(data);
    } catch (e) {
      if (!e.response && user?.active_role === "R06") {
        writeDrafts([...readDrafts(), { id: idem, record_id: record.id, ref: record.ref, key: action.key, label: action.label, payload, at: new Date().toISOString() }]);
        toast.message("Saved as offline draft", { description: "Sync it from Offline drafts when you are connected." });
        onDone && onDone(null);
      } else {
        setErrors(errFields(e));
        setErr(errMsg(e));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid={`action-form-${action.key}`}>
      {action.ev > 0 && (
        <div className="mb-4">
          <Notice tone="blue" title="Evidence required">This step needs at least {action.ev} clean evidence file(s) on {record.ref}.</Notice>
          <EvidencePanel record={record} compact />
        </div>
      )}
      {action.cust && <Notice tone="gray">This step is visible to the complainant and may send an update through their preferred channel.</Notice>}
      {action.fields.length ? <DynamicForm fields={action.fields} values={values} setValues={setValues} errors={errors} ctx={{ model_id: record.model_id }} prefix={`action-${action.key}`} /> : <div className="ce-muted">No additional information is required. Confirm to continue.</div>}
      {err && <div className="mt-4"><Notice tone="red" testid="action-error">{err}</Notice></div>}
      <div className="ce-actions">
        {onCancel && <button className="ce-btn" onClick={onCancel} data-testid="action-cancel">Cancel</button>}
        <button className={`ce-btn ${action.danger ? "danger" : "primary"}`} disabled={busy} onClick={submit} data-testid="action-submit">
          {busy && <Loader2 className="animate-spin" />}{action.label}
        </button>
      </div>
    </div>
  );
}

export function ActionDialog({ record, action, onClose, onDone }) {
  return (
    <Dialog open={!!action} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="action-dialog">
        {action && (
          <>
            <DialogHeader>
              <DialogTitle>{action.label}</DialogTitle>
              <DialogDescription>{record.ref} · {record.title}</DialogDescription>
            </DialogHeader>
            <ActionForm record={record} action={action} onCancel={onClose} onDone={(d) => { onClose(); onDone && onDone(d); }} />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function CreateForm({ type, sub, prefill = {}, labels, parentId, onCreated, submitLabel }) {
  const { wf } = useMeta();
  const spec = wf?.[type]?.create?.[sub];
  const [values, setValues] = useState(prefill);
  const [errors, setErrors] = useState({});
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (!spec) return <Notice tone="red">This form is not available.</Notice>;

  const submit = async () => {
    const v = validateFields(spec.fields, values);
    setErrors(v);
    if (Object.keys(v).length) { setErr("Please correct the highlighted fields."); return; }
    setBusy(true);
    setErr("");
    try {
      const { data } = await api.post(`/records/${type}/${sub}`, { values: coerce(spec.fields, values), parent_id: parentId });
      toast.success(`${spec.label} ${data.ref} created`);
      onCreated && onCreated(data);
    } catch (e) {
      setErrors(errFields(e));
      setErr(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid={`create-form-${type}-${sub}`}>
      <DynamicForm fields={spec.fields} values={values} setValues={setValues} errors={errors} ctx={{ model_id: values.model_id, labels }} prefix={`create-${type}`} />
      {err && <div className="mt-4"><Notice tone="red" testid="create-error">{err}</Notice></div>}
      <div className="ce-actions">
        <button className="ce-btn primary" disabled={busy} onClick={submit} data-testid="create-submit">{busy && <Loader2 className="animate-spin" />}{submitLabel || `Submit ${spec.label.toLowerCase()}`}</button>
      </div>
    </div>
  );
}

export function CreateDialog({ open, onClose, type, sub, prefill, labels, parentId, onCreated }) {
  const { wf } = useMeta();
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="create-dialog">
        <DialogHeader>
          <DialogTitle>{wf?.[type]?.create?.[sub]?.label || "Create record"}</DialogTitle>
          <DialogDescription>Saved to the {wf?.[type]?.label?.toLowerCase()} workflow with a full audit trail.</DialogDescription>
        </DialogHeader>
        {open && <CreateForm type={type} sub={sub} prefill={prefill} labels={labels} parentId={parentId} onCreated={(d) => { onClose(); onCreated && onCreated(d); }} />}
      </DialogContent>
    </Dialog>
  );
}
