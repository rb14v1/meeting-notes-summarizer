import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-title">Meeting Notes &amp; Action Items</div>
        <nav className="app-nav">
          <NavLink to="/" end>Meetings</NavLink>
        </nav>
        <div className="app-header-user">
          <span>{user?.full_name || user?.email} ({user?.role})</span>
          <button onClick={logout}>Log out</button>
        </div>
      </header>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
