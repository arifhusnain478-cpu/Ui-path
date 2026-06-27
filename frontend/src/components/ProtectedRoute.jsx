import { Navigate, Outlet, useLocation } from "react-router-dom";
import { APP_ROUTES } from "../config/constants.js";
import { useAuthStore } from "../store/authStore.js";

export default function ProtectedRoute() {
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);

  if (!isHydrated) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to={APP_ROUTES.login} replace state={{ from: location }} />;
  }

  return <Outlet />;
}
