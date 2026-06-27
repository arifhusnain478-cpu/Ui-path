import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import BrandLogo from "../components/BrandLogo.jsx";
import { HeroVisualPlaceholder } from "../components/VisualPlaceholders.jsx";
import { APP_ROUTES } from "../config/constants.js";
import { useAuthStore } from "../store/authStore.js";

export default function Login() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const loading = useAuthStore((state) => state.loading);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const clearError = useAuthStore((state) => state.clearError);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    clearError();
  }, [clearError]);

  if (isAuthenticated) {
    return <Navigate to={APP_ROUTES.dashboard} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (loading) {
      return;
    }

    try {
      await login({ email, password });
      setPassword("");
      navigate(APP_ROUTES.dashboard, { replace: true });
    } catch {
      setPassword("");
    }
  }

  return (
    <main className="flex min-h-screen">
      {/* Left panel - Brand/Editorial */}
      <section className="hidden w-[55%] flex-col justify-between border-r border-[var(--qt-border)] bg-[var(--qt-surface)] p-10 lg:flex xl:p-14">
        <div>
          <BrandLogo
            variant="full"
            alt="QualiTrace AI"
            fallbackClassName="text-xl"
          />
        </div>

        <div className="max-w-lg">
          <p className="qt-eyebrow">Pharmaceutical Quality Governance</p>
          <h1 className="qt-display-heading mt-5">
            Quality review, governed by evidence.
          </h1>
          <p className="qt-copy mt-6 text-base">
            AI-assisted complaint investigation, regulatory evidence retrieval,
            and audit-ready case management for pharmaceutical quality teams.
          </p>
        </div>

        <div className="mt-auto">
          <HeroVisualPlaceholder />
        </div>
      </section>

      {/* Right panel - Login form */}
      <section className="flex w-full flex-col justify-center bg-[var(--qt-bg)] px-6 py-10 lg:w-[45%] lg:px-14 xl:px-20">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <BrandLogo
              variant="full"
              alt="QualiTrace AI"
              fallbackClassName="text-xl"
            />
          </div>

          <div>
            <p className="qt-eyebrow">Secure access</p>
            <h2 className="mt-3 text-2xl font-normal tracking-tight text-[var(--qt-text-primary)]">
              Sign in to QualiTrace
            </h2>
            <p className="qt-copy mt-3 text-sm">
              Access protected case workflows and reviewer decisions.
            </p>
          </div>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="qt-label">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                disabled={loading}
                onChange={(event) => setEmail(event.target.value)}
                className="qt-field mt-1.5 block px-3 py-2.5 text-sm disabled:cursor-not-allowed disabled:bg-[var(--qt-bg)]"
              />
            </div>

            <div>
              <label htmlFor="password" className="qt-label">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                disabled={loading}
                onChange={(event) => setPassword(event.target.value)}
                className="qt-field mt-1.5 block px-3 py-2.5 text-sm disabled:cursor-not-allowed disabled:bg-[var(--qt-bg)]"
              />
            </div>

            {error ? (
              <div
                role="alert"
                className="border-l-2 border-[var(--qt-critical)] bg-red-50 px-3 py-2.5 text-sm text-red-800"
              >
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="qt-action-primary w-full px-4 py-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}