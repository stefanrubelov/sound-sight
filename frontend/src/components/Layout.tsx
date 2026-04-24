import { NavLink, Outlet } from "react-router-dom";
import styles from "./Layout.module.css";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/history", label: "History" },
  { to: "/rules", label: "Rules" },
  { to: "/devices", label: "Devices" },
  { to: "/settings", label: "Settings" },
  { to: "/onboarding", label: "Onboarding" },
  { to: "/reports", label: "Reports" },
];

export function Layout() {
  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>
        Skip to main content
      </a>

      <header className={styles.header} role="banner">
        <span className={styles.logo} aria-label="SoundSight home">
          SoundSight
        </span>
        <AccessibilityControls />
      </header>

      <div className={styles.body}>
        <nav className={styles.nav} aria-label="Primary navigation">
          <ul role="list">
            {NAV_ITEMS.map(({ to, label, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    [styles.navLink, isActive ? styles.active : ""]
                      .join(" ")
                      .trim()
                  }
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main id="main" className={styles.main} tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function AccessibilityControls() {
  function toggleHighContrast() {
    const root = document.documentElement;
    root.dataset.theme =
      root.dataset.theme === "high-contrast" ? "" : "high-contrast";
  }

  function toggleLargeText() {
    const root = document.documentElement;
    root.dataset.size = root.dataset.size === "large" ? "" : "large";
  }

  return (
    <div
      className={styles.a11yControls}
      role="group"
      aria-label="Accessibility controls"
    >
      <button
        type="button"
        onClick={toggleHighContrast}
        aria-pressed="false"
        className={styles.a11yBtn}
      >
        High contrast
      </button>
      <button
        type="button"
        onClick={toggleLargeText}
        aria-pressed="false"
        className={styles.a11yBtn}
      >
        Large text
      </button>
    </div>
  );
}
