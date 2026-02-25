import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./UsernameProvider";

export default function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
