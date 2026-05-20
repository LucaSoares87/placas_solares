import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import MainLayout from "./layouts/MainLayout";
import Alerts from "./pages/Alerts";
import Dashboard from "./pages/Dashboard";
import Export from "./pages/Export";
import Login from "./pages/Login";
import Map from "./pages/Map";
import Ranking from "./pages/Ranking";
import Validation from "./pages/Validation";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="ranking" element={<Ranking />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="map" element={<Map />} />
          <Route path="validation" element={<Validation />} />
          <Route path="export" element={<Export />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}