import { useEffect } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import { APP_ROUTES } from "./config/constants.js";
import AuditTrail from "./pages/AuditTrail.jsx";
import CaseDetail from "./pages/CaseDetail.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import HumanTask from "./pages/HumanTask.jsx";
import Login from "./pages/Login.jsx";
import NewComplaint from "./pages/NewComplaint.jsx";
import { useAuthStore } from "./store/authStore.js";

function AuthenticatedLayout() {
  return (
    <>
      <Navbar />
      <Outlet />
    </>
  );
}

export default function App() {
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const hydrateFromStorage = useAuthStore((state) => state.hydrateFromStorage);

  useEffect(() => {
    hydrateFromStorage();
  }, [hydrateFromStorage]);

  if (!isHydrated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f4f2ed] px-6">
        <p className="qt-panel px-5 py-3 text-sm font-bold text-slate-600">
          Loading QualiTrace AI...
        </p>
      </main>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to={APP_ROUTES.dashboard} replace />} />
      <Route path={APP_ROUTES.login} element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AuthenticatedLayout />}>
          <Route path={APP_ROUTES.dashboard} element={<Dashboard />} />
          <Route path={APP_ROUTES.new_complaint} element={<NewComplaint />} />
          <Route path="/cases/:case_id" element={<CaseDetail />} />
          <Route
            path="/cases/:case_id/tasks/:task_id"
            element={<HumanTask />}
          />
          <Route path="/cases/:case_id/audit" element={<AuditTrail />} />
        </Route>
      </Route>
    </Routes>
  );
}
