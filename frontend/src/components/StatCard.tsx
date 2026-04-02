import styles from './StatCard.module.css';

export interface StatCardData {
  icon: string | React.ReactNode;
  title: string;
  value: number | string;
  subtitle?: string;
  color?: string;
  bg?: string;
}

interface StatCardProps {
  data?: StatCardData;
  title?: string;
  value?: number | string;
  icon?: React.ReactNode;
}

export default function StatCard(props: StatCardProps) {
  // Support both { data } and direct { title, value, icon } patterns
  const title = props.data?.title ?? props.title ?? '';
  const value = props.data?.value ?? props.value ?? '';
  const color = props.data?.color ?? 'var(--pm-accent-primary)';
  const bg = props.data?.bg ?? 'var(--pm-accent-primary-bg)';
  const subtitle = props.data?.subtitle;

  // Icon can be a ReactNode (direct) or a string key (via data)
  const icon = props.icon ?? props.data?.icon;
  const isReactIcon = typeof icon !== 'string';

  return (
    <div className={styles.card}>
      <div className={styles.topRow}>
        <div className={styles.iconTitle}>
          <div
            className={styles.iconCircle}
            style={{ background: bg, color: color }}
          >
            {isReactIcon ? icon : null}
          </div>
          <p className={styles.title}>{title}</p>
        </div>
      </div>
      <div className={styles.valueRow}>
        <p className={styles.value} style={{ color }}>
          {value}
        </p>
        {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      </div>
    </div>
  );
}
