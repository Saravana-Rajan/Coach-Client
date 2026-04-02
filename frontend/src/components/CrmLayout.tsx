import { useState, useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Sidebar from "./Sidebar";
import DashboardHeader from "./DashboardHeader";
import SyncBanner from "./SyncBanner";
import styles from "./CrmLayout.module.css";

const routeToNavId: Record<string, string> = {
  "/": "dashboard",
  "/dashboard": "dashboard",
  "/audit": "audit",
  "/briefs": "briefs",
  "/source": "source",
  "/manage": "manage",
  "/schema": "schema",
};

function resolveNavId(pathname: string): string {
  if (routeToNavId[pathname]) return routeToNavId[pathname];
  if (pathname.startsWith("/briefs/")) return "briefs";
  if (pathname.startsWith("/audit/")) return "audit";
  if (pathname.startsWith("/manage")) return "manage";
  if (pathname.startsWith("/schema")) return "schema";
  return "dashboard";
}

const routeToPageInfo: Record<string, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Overview of your coaching assignments and activity.",
  },
  audit: {
    title: "Audit Trail",
    subtitle: "Track all reassignment changes across the system.",
  },
  briefs: {
    title: "Transition Briefs",
    subtitle: "AI-generated handoff documents for reassignments.",
  },
  source: {
    title: "Source Editor",
    subtitle: "Manage simulated Salesforce source data.",
  },
  manage: {
    title: "Admin Management",
    subtitle: "Add, edit, delete coaches, accounts, and contacts. Bulk operations.",
  },
  schema: {
    title: "Schema Changes",
    subtitle: "Monitor and manage schema differences between Salesforce and local database.",
  },
};

export default function CrmLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const activeItem = resolveNavId(location.pathname);
  const pageInfo = routeToPageInfo[activeItem];

  const handleNavChange = (id: string) => {
    const routes: Record<string, string> = {
      dashboard: user?.role === "admin" ? "/admin" : "/",
      audit: "/audit",
      briefs: "/briefs",
      source: "/source",
      manage: "/manage",
      schema: "/schema",
    };
    navigate(routes[id] || "/");
  };

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <div className={styles.pageWrapper}>
      <button
        className={styles.hamburger}
        onClick={() => setMobileOpen((v) => !v)}
        type="button"
        aria-label={mobileOpen ? "Close menu" : "Open menu"}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      <div className={styles.layout}>
        <Sidebar
          activeItem={activeItem}
          onActiveChange={handleNavChange}
          mobileOpen={mobileOpen}
          onMobileClose={() => setMobileOpen(false)}
        />
        <main className={styles.content}>
          <DashboardHeader
            title={pageInfo?.title}
            subtitle={pageInfo?.subtitle}
          />
          <SyncBanner />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
