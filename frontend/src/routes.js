import { Navigate, Route, Routes } from "react-router-dom";
import AuthPage from "./components/AuthPage";
import HistoryPage from "./components/HistoryPage";
import MainPage from "./components/MainPage";
import ProtectedRoute from "./components/ProtectedRoute";
import RoomPage from "./components/RoomPage";

export default function GameRoutes() {
  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<MainPage />} />
        <Route path="/room/:roomid" element={<RoomPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
