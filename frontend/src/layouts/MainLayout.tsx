import { Outlet } from "react-router-dom";

import Header from "../components/Header";
import Sidebar from "../components/Sidebar";

export default function MainLayout() {
  return (
    <div className="page-shell">
      <Sidebar />
      <main className="main-area">
        <Header />
        <section className="content">
          <Outlet />
        </section>
      </main>
    </div>
  );
}