import { Link, useNavigate, useLocation } from "react-router-dom";
import BrandLogo from "./BrandLogo.jsx";
import { APP_ROUTES } from "../config/constants.js";
import { useAuthStore } from "../store/authStore.js";
import { formatRoleLabel } from "../utils/display.js";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const display_name = user?.username || user?.user_id || "User";
  const mock_enabled = import.meta.env.VITE_USE_MOCK_API === "true";

  function handleLogout() {
    logout();
    navigate(APP_ROUTES.login, { replace: true });
  }

  const is_dashboard = location.pathname === APP_ROUTES.dashboard;
  const is_new_complaint = location.pathname === APP_ROUTES.new_complaint;

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--qt-border)] bg-[var(--qt-surface)]">
      <nav className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-5">
        <div className="flex items-center gap-8">
          <Link
            to={APP_ROUTES.dashboard}
            aria-label="QualiTrace AI dashboard"
            className="flex items-center gap-2.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2"
          >
            <BrandLogo
              variant="short"
              alt=""
              className="h-8 w-8 shrink-0"
              fallbackClassName="text-base"
            />
            <span className="hidden text-sm font-medium tracking-tight text-[var(--qt-text-primary)] sm:inline">
              QualiTrace
            </span>
          </Link>

          <div className="hidden items-center gap-6 sm:flex">
            <NavLink to={APP_ROUTES.dashboard} active={is_dashboard}>
              Dashboard
            </NavLink>
            <NavLink to={APP_ROUTES.new_complaint} active={is_new_complaint}>
              New Complaint
            </NavLink>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {mock_enabled ? (
            <span className="hidden text-xs font-medium text-[var(--qt-text-muted)] sm:inline">
              Mock
            </span>
          ) : null}

          <div className="flex items-center gap-2 text-sm">
            <span className="max-w-28 truncate font-medium text-[var(--qt-text-primary)] sm:max-w-40">
              {display_name}
            </span>
            {user?.role ? (
              <span className="hidden text-xs text-[var(--qt-text-muted)] sm:inline">
                {formatRoleLabel(user.role)}
              </span>
            ) : null}
          </div>

          <div className="h-4 w-px bg-[var(--qt-border)]" />

          <button
            type="button"
            onClick={handleLogout}
            className="text-sm font-medium text-[var(--qt-text-secondary)] transition-colors hover:text-[var(--qt-text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2"
          >
            Logout
          </button>
        </div>
      </nav>
    </header>
  );
}

function NavLink({ to, active, children }) {
  return (
    <Link
      to={to}
      className={`relative py-1 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--qt-text-primary)] focus-visible:ring-offset-2 ${
        active
          ? "text-[var(--qt-text-primary)]"
          : "text-[var(--qt-text-secondary)] hover:text-[var(--qt-text-primary)]"
      }`}
    >
      {children}
      {active ? (
        <span className="absolute -bottom-[17px] left-0 right-0 h-px bg-[var(--qt-text-primary)]" />
      ) : null}
    </Link>
  );
}