import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="login-page">
        <div className="login-card">Checking session...</div>
      </div>
    );
  }

  if (user) {
    const redirectTo =
      (location.state as { from?: { pathname?: string } })?.from?.pathname ||
      "/";
    return <Navigate to={redirectTo} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemoAccount(demoUser: string, demoPass: string) {
    setUsername(demoUser);
    setPassword(demoPass);
    setError(null);
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">PrismFlow</div>
          <div className="login-subtitle">
            Real-Time Crypto Streaming Terminal
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}

          <label className="form-field">
            <span>Username</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. trader"
              autoComplete="username"
              required
            />
          </label>

          <label className="form-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </label>

          <button
            type="submit"
            className="btn primary login-submit"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="demo-accounts">
          <div className="demo-title">Quick-fill Demo Accounts</div>
          <div className="demo-buttons">
            <button
              type="button"
              className="btn"
              onClick={() => fillDemoAccount("trader", "crypto2026")}
            >
              Trader (`trader` / `crypto2026`)
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => fillDemoAccount("admin", "prismflow123")}
            >
              Admin (`admin` / `prismflow123`)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
