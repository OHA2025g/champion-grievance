import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ShieldCheck, Workflow, Lock, Loader2, ArrowRight } from "lucide-react";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { api, errMsg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Notice } from "@/components/Common";

function Left() {
  return (
    <div className="ce-login-left" data-testid="login-hero">
      <div className="ce-brand" style={{ padding: 0 }}>CHAMPION<small>SERVICE DESK</small></div>
      <div className="ce-login-copy">
        <div className="ce-eyebrow" style={{ color: "#84a8f3" }}>Champion Electricals</div>
        <h1>One accountable record for every service concern.</h1>
        <p>Complaints, service visits, warranty decisions, settlements, safety incidents and appeals - each with a named owner, a live service level and a complete audit trail.</p>
        <div className="mt-8 space-y-4 text-[13px] text-[#c1cce0]">
          <div className="flex gap-3"><ShieldCheck size={18} className="text-[#7eafff]" />Role-based access enforced for 21 distinct roles</div>
          <div className="flex gap-3"><Workflow size={18} className="text-[#7eafff]" />Linked jobs, approvals and claims that block premature closure</div>
          <div className="flex gap-3"><Lock size={18} className="text-[#7eafff]" />Safety concerns escalate immediately to specialists</div>
        </div>
      </div>
    </div>
  );
}

function DevGrid() {
  const [cfg, setCfg] = useState(null);
  const { devLogin } = useAuth();
  const nav = useNavigate();
  useEffect(() => { api.get("/public/config").then((r) => setCfg(r.data)).catch(() => {}); }, []);
  if (!cfg?.dev_switcher) return null;
  return (
    <div className="mt-8" data-testid="dev-switcher-panel">
      <div className="ce-divider">DEVELOPMENT ROLE SWITCHER</div>
      <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-2 mb-3">Dev mode only - signs in as a seeded demo account for the selected role. Disabled when DEV_MODE is off.</div>
      <div className="grid grid-cols-3 gap-1.5">
        {Object.entries(cfg.roles).map(([k, v]) => (
          <button key={k} className="ce-btn sm justify-start" title={v} onClick={async () => { try { await devLogin(k); nav("/app"); } catch (e) { toast.error(errMsg(e)); } }} data-testid={`dev-login-${k}`}>
            <b className="ce-mono">{k}</b><span className="truncate text-[10.5px] font-normal">{v.split(" /")[0]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try { await login(email, pw); nav("/app"); } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };
  const google = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/app";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <div className="ce-login" data-testid="login-page">
      <Left />
      <div className="ce-login-right">
        <form className="ce-login-form" onSubmit={submit}>
          <div className="ce-eyebrow">CE-001 · Secure access</div>
          <h1 className="ce-h1">Welcome to Champion Service</h1>
          <div className="ce-sub">Sign in with your provisioned work account.</div>
          <div className="ce-field mt-6"><label>Work email</label><input className="ce-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="login-email" /></div>
          <div className="ce-field mt-4"><label>Password</label><input className="ce-input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} required data-testid="login-password" /></div>
          {err && <div className="mt-4"><Notice tone="red" testid="login-error">{err}</Notice></div>}
          <button className="ce-btn primary w-full justify-center mt-5" style={{ padding: 13 }} disabled={busy} data-testid="login-submit">{busy ? <Loader2 className="animate-spin" /> : <ArrowRight />}Continue securely</button>
          <div className="ce-divider">OR</div>
          <button type="button" className="ce-btn w-full justify-center" style={{ padding: 12 }} onClick={google} data-testid="google-login-btn">
            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7z" /><path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z" /><path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6h-4a12 12 0 0 0 0 10.8l4-3.1z" /><path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z" /></svg>
            Continue with Google
          </button>
          <div className="flex justify-between mt-5 text-[12px]">
            <Link to="/otp" className="ce-link" data-testid="otp-link">Customer? Sign in with a one-time code</Link>
            <Link to="/recover" className="ce-link" data-testid="recover-link">Recover staff access</Link>
          </div>
          <DevGrid />
        </form>
      </div>
    </div>
  );
}

export function Otp() {
  const { reload } = useAuth();
  const nav = useNavigate();
  const [ident, setIdent] = useState("");
  const [sent, setSent] = useState(null);
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const request = async (e) => {
    e?.preventDefault();
    setErr("");
    try { const { data } = await api.post("/auth/otp/request", { identifier: ident }); setSent(data); } catch (x) { setErr(errMsg(x)); }
  };
  const verify = async () => {
    setErr("");
    try { await api.post("/auth/otp/verify", { identifier: ident, code }); await reload(); nav("/app"); } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <div className="ce-login" data-testid="otp-page">
      <Left />
      <div className="ce-login-right">
        <div className="ce-login-form">
          <div className="ce-eyebrow">CE-002 · Customer verification</div>
          <h1 className="ce-h1">Verify your contact</h1>
          <div className="ce-sub">Enter the email or mobile number registered with your complaint.</div>
          <form onSubmit={request} className="ce-field mt-6"><label>Email or mobile number</label><input className="ce-input" value={ident} onChange={(e) => setIdent(e.target.value)} required data-testid="otp-identifier" />
            {!sent && <button className="ce-btn primary w-full justify-center mt-4" data-testid="otp-request">Send verification code</button>}
          </form>
          {sent && (
            <div className="mt-5" data-testid="otp-sent">
              <Notice tone="blue">{sent.message}</Notice>
              {sent.dev_code && <Notice testid="otp-dev-code" title="DEV MODE">{sent.dev_note} Code: <b className="ce-mono">{sent.dev_code}</b></Notice>}
              <InputOTP maxLength={6} value={code} onChange={setCode} data-testid="otp-input"><InputOTPGroup>{[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} />)}</InputOTPGroup></InputOTP>
              <button className="ce-btn primary w-full justify-center mt-5" disabled={code.length !== 6} onClick={verify} data-testid="otp-verify">Verify and continue</button>
              <button className="ce-link mt-3 block" onClick={request} data-testid="otp-resend">Resend code</button>
            </div>
          )}
          {err && <div className="mt-4"><Notice tone="red" testid="otp-error">{err}</Notice></div>}
          <Link to="/login" className="ce-link mt-6 block">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}

export function Recover() {
  const [email, setEmail] = useState("");
  const [ref, setRef] = useState("");
  const [res, setRes] = useState(null);
  const [token, setToken] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);
  const request = async (e) => {
    e.preventDefault();
    setErr("");
    try { const { data } = await api.post("/auth/recover", { email, support_reference: ref }); setRes(data); if (data.dev_token) setToken(data.dev_token); } catch (x) { setErr(errMsg(x)); }
  };
  const reset = async () => {
    setErr("");
    try { await api.post("/auth/reset", { token, password: pw }); setOk(true); } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <div className="ce-login" data-testid="recover-page">
      <Left />
      <div className="ce-login-right">
        <div className="ce-login-form">
          <div className="ce-eyebrow">CE-003 · Staff access</div>
          <h1 className="ce-h1">Recover staff access</h1>
          <div className="ce-sub">Recovery instructions are sent only to a registered work email.</div>
          {!res && (
            <form onSubmit={request}>
              <div className="ce-field mt-6"><label>Work email</label><input className="ce-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="recover-email" /></div>
              <div className="ce-field mt-4"><label>Support reference (optional)</label><input className="ce-input" value={ref} onChange={(e) => setRef(e.target.value)} data-testid="recover-reference" /></div>
              <button className="ce-btn primary w-full justify-center mt-5" data-testid="recover-submit">Send recovery instructions</button>
            </form>
          )}
          {res && !ok && (
            <div className="mt-5" data-testid="recover-sent">
              <Notice tone="blue">{res.message}</Notice>
              {res.dev_token && <Notice title="DEV MODE">Email was not delivered by a real provider, so the one-time token has been pre-filled.</Notice>}
              <div className="ce-field mt-3"><label>Recovery token</label><input className="ce-input ce-mono" value={token} onChange={(e) => setToken(e.target.value)} data-testid="recover-token" /></div>
              <div className="ce-field mt-3"><label>New password</label><input className="ce-input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} data-testid="recover-new-password" /><div className="ce-hint">At least 10 characters with upper and lower case letters and a digit.</div></div>
              <button className="ce-btn primary w-full justify-center mt-4" onClick={reset} data-testid="recover-reset">Set new password</button>
            </div>
          )}
          {ok && <Notice tone="green" testid="recover-done" title="Password updated">You can now sign in with your new password.</Notice>}
          {err && <div className="mt-4"><Notice tone="red" testid="recover-error">{err}</Notice></div>}
          <Link to="/login" className="ce-link mt-6 block" data-testid="back-to-login">Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}

export function AuthCallback() {
  const { reload } = useAuth();
  const nav = useNavigate();
  const [err, setErr] = useState("");
  const done = useRef(false);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const sid = new URLSearchParams(window.location.hash.slice(1)).get("session_id");
    api.post("/auth/google/session", { session_id: sid })
      .then(async () => { window.history.replaceState(null, "", window.location.pathname); await reload(); nav("/app", { replace: true }); })
      .catch((e) => { window.history.replaceState(null, "", "/login"); setErr(errMsg(e)); });
  }, [reload, nav]);
  return (
    <div className="ce-status-page" data-testid="auth-callback">
      {err ? <><Notice tone="red" title="Google sign-in failed">{err}</Notice><Link className="ce-link" to="/login">Back to sign in</Link></> : <><Loader2 className="animate-spin mx-auto text-blue-600" /><div className="ce-muted mt-3">Verifying your Google account…</div></>}
    </div>
  );
}
