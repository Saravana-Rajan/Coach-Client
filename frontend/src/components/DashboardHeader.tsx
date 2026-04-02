import styles from "./DashboardHeader.module.css";

interface DashboardHeaderProps {
  title?: string;
  subtitle?: string;
}

export default function DashboardHeader({
  title,
  subtitle,
}: DashboardHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.titleBlock}>
        <h1 className={styles.title}>
          {title || (
            <>
              Coach
              <span style={{ color: "var(--pm-accent-gold)", fontWeight: 800 }}>
                Portal
              </span>
            </>
          )}
        </h1>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
    </header>
  );
}
