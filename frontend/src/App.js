import { Component } from "react";
import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth, useMeta } from "@/context/AuthContext";
import Shell from "@/components/Shell";
import { Login, Otp, Recover, AuthCallback } from "@/pages/Auth";
import ScreenHost from "@/screens/ScreenHost";
import { RecordPage, SearchPage } from "@/screens/Records";
import { Loading } from "@/components/Common";

class ErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="ce-status-page" data-testid="error-boundary">
        <h2 className="text-2xl font-semibold text-slate-800">Something went wrong on this screen</h2>
        <p className="ce-sub mt-3">Your saved work is safe. Reload to continue.</p>
        <button className="ce-btn primary mt-5" onClick={() => window.location.reload()} data-testid="error-reload-btn">Reload</button>
      </div>
    );
  }
}

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-10"><Loading /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Home() {
  const m = useMeta();
  return <Navigate to={`/app/s/${m.roleInfo?.home || "CE-004"}`} replace />;
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth();
  if (ready && user) return <Navigate to="/app" replace />;
  return children;
}

function AppRoutes() {
  const loc = useLocation();
  if (loc.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/otp" element={<PublicOnly><Otp /></PublicOnly>} />
      <Route path="/recover" element={<Recover />} />
      <Route path="/app" element={<Protected><Shell /></Protected>}>
        <Route index element={<Home />} />
        <Route path="s/:sid" element={<ScreenHost />} />
        <Route path="s/:sid/:rid" element={<ScreenHost />} />
        <Route path="r/:rid" element={<RecordPage />} />
        <Route path="search" element={<SearchPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" richColors closeButton />
        <ErrorBoundary><AppRoutes /></ErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  );
}
