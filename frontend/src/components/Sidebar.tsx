import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import styles from "./Sidebar.module.css";

/* ── PNG Icon imports ── */
import iconDashboard from "../assets/Logo/icons/Dashboard.png";
import iconAudit from "../assets/Logo/icons/Audit Logs.png";
import iconBriefs from "../assets/Logo/icons/Reports.png";
import iconSource from "../assets/Logo/icons/SalesforceData.png";
import iconSettings from "../assets/Logo/icons/Active.png";
import iconTools from "../assets/Logo/icons/TotalTools.png";
import LogoSvg from "../assets/Logo/Logo.svg";

/* ── SVG Icon components ── */

function DoubleChevron({ direction }: { direction: "left" | "right" }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {direction === "right" ? (
        <>
          <polyline points="7 18 13 12 7 6" />
          <polyline points="13 18 19 12 13 6" />
        </>
      ) : (
        <>
          <polyline points="17 18 11 12 17 6" />
          <polyline points="11 18 5 12 11 6" />
        </>
      )}
    </svg>
  );
}

function SunIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16 17l5-5-5-5M21 12H9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ── Nav slot builder ── */

interface NavSlot {
  id: string;
  iconSrc?: string;
  iconSvg?: React.ReactNode;
  label: string;
  adminOnly?: boolean;
}

const NAV_SLOTS: NavSlot[] = [
  { id: "dashboard", iconSrc: iconDashboard, label: "Dashboard" },
  { id: "audit", iconSrc: iconAudit, label: "Audit Logs", adminOnly: true },
  { id: "briefs", iconSrc: iconBriefs, label: "Transition Briefs" },
  { id: "source", iconSrc: iconSource, label: "Salesforce Data", adminOnly: true },
  { id: "manage", iconSrc: iconSettings, label: "Admin Management", adminOnly: true },
  { id: "schema", iconSrc: iconTools, label: "Schema Changes", adminOnly: true },
];

/* ── Component ── */

interface SidebarProps {
  activeItem: string;
  onActiveChange: (id: string) => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export default function Sidebar({
  activeItem,
  onActiveChange,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();

  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem("coach_sidebar_collapsed") === "true"
  );
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  const isAdmin = user?.role === "admin";
  const visibleSlots = NAV_SLOTS.filter(
    (slot) => !slot.adminOnly || isAdmin
  );

  const toggleCollapse = () =>
    setCollapsed((v) => {
      localStorage.setItem("coach_sidebar_collapsed", String(!v));
      return !v;
    });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(e.target as Node)
      ) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleLogout = async () => {
    setShowProfileMenu(false);
    onMobileClose?.();
    await logout();
    navigate("/login");
  };

  return (
    <>
      {mobileOpen && <div className={styles.overlay} onClick={onMobileClose} />}

      <aside
        className={`${styles.sidebar} ${collapsed ? styles.sidebarCollapsed : ""} ${mobileOpen ? styles.sidebarMobileOpen : ""}`}
      >
        {/* ── Logo row with collapse toggle ── */}
        <div className={styles.logoRow}>
          <span className={styles.logoText}>
            {collapsed ? (
              <svg width="28" height="28" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M39.1481 43.392C41.974 38.7988 43.6921 32.6868 43.6921 25.9988C43.6921 19.3108 41.9691 13.2111 39.1481 8.60555C41.557 10.4244 43.5621 12.7235 45.0366 15.3573C46.5111 17.991 47.4229 20.9022 47.7143 23.9065H51.9137C51.3734 17.2142 48.265 10.9905 43.2395 6.53829C38.2139 2.08611 31.6608 -0.249272 24.9522 0.0211106C18.2437 0.291493 11.8998 3.14667 7.24883 7.98886C2.59787 12.831 0.000488281 19.2848 0.000488281 25.9988C0.000488281 32.7128 2.59787 39.1665 7.24883 44.0087C11.8998 48.8509 18.2437 51.7061 24.9522 51.9765C31.6608 52.2468 38.2139 49.9115 43.2395 45.4593C48.265 41.0071 51.3734 34.7833 51.9137 28.0911H47.7143C47.4229 31.0954 46.5111 34.0065 45.0366 36.6403C43.5621 39.2741 41.557 41.5731 39.1481 43.392ZM21.3315 23.9065C21.4768 18.9219 22.1365 14.1908 23.2245 10.4074C24.2485 6.8554 25.3758 5.10525 25.9986 4.43079C26.6214 5.10525 27.7488 6.8554 28.7728 10.4074C30.0035 14.7176 30.6977 20.2536 30.6977 25.9988C30.6977 31.744 30.0134 37.28 28.7728 41.5902C27.7488 45.1422 26.6214 46.8923 25.9986 47.5668C25.3758 46.8923 24.2485 45.1422 23.2245 41.5902C22.1365 37.8068 21.4768 33.0757 21.3315 28.0911H26.0085V23.9065H21.3315ZM20.1549 6.41479C18.4614 10.752 17.334 16.9428 17.1445 23.9065H12.5463C13.0386 16.3052 16.0392 9.70833 20.1549 6.41479ZM17.1445 28.0911C17.334 35.0548 18.4614 41.2455 20.1549 45.5828C16.0392 42.2892 13.0386 35.6923 12.5463 28.0911H17.1445ZM31.8398 45.5902C33.7032 40.8222 34.8823 33.8142 34.8823 25.9988C34.8823 18.1834 33.7032 11.1754 31.8398 6.4074C36.3321 9.99879 39.5075 17.5262 39.5075 25.9988C39.5075 34.4714 36.3321 41.9988 31.8398 45.5902ZM4.17708 25.9988C4.17725 22.6266 4.95987 19.3003 6.46336 16.2818C7.96685 13.2633 10.1502 10.6348 12.8417 8.6031C10.0183 13.2111 8.2977 19.3108 8.2977 25.9988C8.2977 32.6868 10.0208 38.7865 12.8417 43.3945C10.1502 41.3628 7.96685 38.7342 6.46336 35.7157C4.95987 32.6972 4.17725 29.371 4.17708 25.9988Z" fill="#DA291C"/>
              </svg>
            ) : (
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <svg width="26" height="26" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M39.1481 43.392C41.974 38.7988 43.6921 32.6868 43.6921 25.9988C43.6921 19.3108 41.9691 13.2111 39.1481 8.60555C41.557 10.4244 43.5621 12.7235 45.0366 15.3573C46.5111 17.991 47.4229 20.9022 47.7143 23.9065H51.9137C51.3734 17.2142 48.265 10.9905 43.2395 6.53829C38.2139 2.08611 31.6608 -0.249272 24.9522 0.0211106C18.2437 0.291493 11.8998 3.14667 7.24883 7.98886C2.59787 12.831 0.000488281 19.2848 0.000488281 25.9988C0.000488281 32.7128 2.59787 39.1665 7.24883 44.0087C11.8998 48.8509 18.2437 51.7061 24.9522 51.9765C31.6608 52.2468 38.2139 49.9115 43.2395 45.4593C48.265 41.0071 51.3734 34.7833 51.9137 28.0911H47.7143C47.4229 31.0954 46.5111 34.0065 45.0366 36.6403C43.5621 39.2741 41.557 41.5731 39.1481 43.392ZM21.3315 23.9065C21.4768 18.9219 22.1365 14.1908 23.2245 10.4074C24.2485 6.8554 25.3758 5.10525 25.9986 4.43079C26.6214 5.10525 27.7488 6.8554 28.7728 10.4074C30.0035 14.7176 30.6977 20.2536 30.6977 25.9988C30.6977 31.744 30.0134 37.28 28.7728 41.5902C27.7488 45.1422 26.6214 46.8923 25.9986 47.5668C25.3758 46.8923 24.2485 45.1422 23.2245 41.5902C22.1365 37.8068 21.4768 33.0757 21.3315 28.0911H26.0085V23.9065H21.3315ZM20.1549 6.41479C18.4614 10.752 17.334 16.9428 17.1445 23.9065H12.5463C13.0386 16.3052 16.0392 9.70833 20.1549 6.41479ZM17.1445 28.0911C17.334 35.0548 18.4614 41.2455 20.1549 45.5828C16.0392 42.2892 13.0386 35.6923 12.5463 28.0911H17.1445ZM31.8398 45.5902C33.7032 40.8222 34.8823 33.8142 34.8823 25.9988C34.8823 18.1834 33.7032 11.1754 31.8398 6.4074C36.3321 9.99879 39.5075 17.5262 39.5075 25.9988C39.5075 34.4714 36.3321 41.9988 31.8398 45.5902ZM4.17708 25.9988C4.17725 22.6266 4.95987 19.3003 6.46336 16.2818C7.96685 13.2633 10.1502 10.6348 12.8417 8.6031C10.0183 13.2111 8.2977 19.3108 8.2977 25.9988C8.2977 32.6868 10.0208 38.7865 12.8417 43.3945C10.1502 41.3628 7.96685 38.7342 6.46336 35.7157C4.95987 32.6972 4.17725 29.371 4.17708 25.9988Z" fill="#DA291C"/>
                </svg>
                <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em" }}>Coach <span style={{ color: "var(--pm-accent-primary)" }}>IQ</span></span>
              </span>
            )}
          </span>
          <button
            className={styles.collapseBtn}
            onClick={toggleCollapse}
            type="button"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <DoubleChevron direction={collapsed ? "right" : "left"} />
          </button>
        </div>

        {/* ── Navigation ── */}
        <nav className={styles.nav}>
          {visibleSlots.map((slot) => (
            <button
              key={slot.id}
              className={`${styles.navItem} ${activeItem === slot.id ? styles.navItemActive : ""}`}
              onClick={() => {
                onActiveChange(slot.id);
                onMobileClose?.();
              }}
              type="button"
              aria-label={slot.label}
              title={slot.label}
              data-tooltip={collapsed ? slot.label : undefined}
            >
              <img src={slot.iconSrc} alt="" className={styles.navIcon} />
              {!collapsed && <span className={styles.navLabel}>{slot.label}</span>}
            </button>
          ))}
        </nav>

        {/* ── Bottom: theme toggle + user ── */}
        <div className={styles.bottom} ref={profileMenuRef}>
          <button
            className={styles.themeBtn}
            onClick={toggleTheme}
            type="button"
            title={isDark ? "Light Mode" : "Dark Mode"}
            data-tooltip={collapsed ? (isDark ? "Light Mode" : "Dark Mode") : undefined}
          >
            <span className={styles.themeBtnIcon}>
              {isDark ? <SunIcon /> : <MoonIcon />}
            </span>
            {!collapsed && <span>{isDark ? "Light Mode" : "Dark Mode"}</span>}
          </button>

          <button
            className={styles.userBtn}
            onClick={() => setShowProfileMenu((v) => !v)}
            type="button"
          >
            <span className={styles.avatar}>
              {(user?.username || "U").slice(0, 2).toUpperCase()}
            </span>
            {!collapsed && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1px", minWidth: 0 }}>
                <span className={styles.userName}>{user?.username || "User"}</span>
                <span style={{ fontSize: "11px", color: "var(--pm-text-muted)", textTransform: "capitalize" }}>{user?.role || "coach"}</span>
              </div>
            )}
            {!collapsed && (
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={styles.userChevron}
              >
                <polyline points="6 15 12 9 18 15" />
              </svg>
            )}
            <span className={styles.onlineDot} />
          </button>

          {showProfileMenu && (
            <div className={styles.profileMenu}>
              <div className={styles.profileDivider} />
              <button
                className={styles.profileItem}
                type="button"
                onClick={() => {
                  setShowProfileMenu(false);
                  onMobileClose?.();
                }}
              >
                <ProfileIcon />
                <span>My Profile</span>
              </button>
              <button
                className={`${styles.profileItem} ${styles.profileItemDanger}`}
                type="button"
                onClick={handleLogout}
              >
                <LogoutIcon />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
