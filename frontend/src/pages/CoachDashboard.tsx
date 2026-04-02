import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import StatCard from '../components/StatCard';
import type { StatCardData } from '../components/StatCard';
import styles from './CoachDashboard.module.css';

/* ── PNG Icon imports for StatCards ── */
import iconBusinessDev from '../assets/icons/businessdevelopment.png';
import iconTeam from '../assets/icons/team.png';

/* ── Types matching backend DashboardSerializer ── */

interface Contact {
  id: number;
  sf_id: string;
  name: string;
  title: string;
  phone: string;
  email: string;
  account_id: number;
  coach_id: number;
  coach_name: string;
}

interface Account {
  id: number;
  sf_id: string;
  name: string;
  industry: string;
  website: string;
  coaching_start_date: string;
  coach_id: number;
  coach_name: string;
  contacts: Contact[];
}

interface Coach {
  id: number;
  sf_id: string;
  name: string;
  email: string;
  active_clients: number;
  is_active: boolean;
}

interface DashboardEntry {
  coach: Coach;
  accounts: Account[];
  total_accounts: number;
  total_clients: number;
}

/* ── Custom chart tooltip ── */

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} className={styles.tooltipRow}>
          <span
            className={styles.tooltipDot}
            style={{ background: p.color || p.fill }}
          />
          <span>
            {p.name}: {p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Build bar-chart data: clients per account ── */

function buildChartData(accounts: Account[]) {
  return accounts.map((a) => ({
    name: a.name.length > 18 ? a.name.slice(0, 16) + '...' : a.name,
    Clients: a.contacts.length,
  }));
}

/* ── Bar gradient colors ── */

const BAR_COLORS = {
  gridStroke: 'var(--pm-border-light)',
  axisTick: 'var(--pm-text-muted)',
  gradientStart: '#9E8544',
  gradientEnd: '#8B7339',
  cursorFill: 'rgba(158, 133, 68, 0.04)',
};

export default function CoachDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardEntry[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get('/coaching/dashboard/')
      .then((res) => {
        // Admin gets an array; coach gets a single object
        const payload = Array.isArray(res.data) ? res.data : [res.data];
        setData(payload);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const isAdmin = user?.role === 'admin';
  const userName = user?.name?.split(' ')[0] || 'there';

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinnerOuter} />
        <span className={styles.loadingText}>Loading dashboard...</span>
      </div>
    );
  }

  /* ── Empty / error state ── */
  if (!data || data.length === 0) {
    return (
      <div className={styles.emptyState}>
        No data available. Run a sync first.
      </div>
    );
  }

  /* ── Aggregate totals (for admin: across all coaches; for coach: their own) ── */
  const grandTotalAccounts = data.reduce((s, d) => s + d.total_accounts, 0);
  const grandTotalClients = data.reduce((s, d) => s + d.total_clients, 0);

  /* ── Aggregate chart data across all visible coaches ── */
  const allAccounts = data.flatMap((d) => d.accounts);
  const chartData = buildChartData(allAccounts);

  const statCards: StatCardData[] = [
    {
      icon: <img src={iconBusinessDev} alt="" width={20} height={20} />,
      title: 'Total Accounts',
      value: grandTotalAccounts,
      subtitle: isAdmin ? `across ${data.length} coaches` : undefined,
      color: '#9E8544',
      bg: 'rgba(158, 133, 68, 0.1)',
    },
    {
      icon: <img src={iconTeam} alt="" width={20} height={20} />,
      title: 'Total Clients',
      value: grandTotalClients,
      subtitle: isAdmin ? 'all active contacts' : undefined,
      color: '#10B981',
      bg: 'rgba(16, 185, 129, 0.1)',
    },
  ];

  return (
    <div className={styles.dashboard}>
      {/* ── Welcome Header ── */}
      <div className={styles.welcomeRow}>
        <div className={styles.welcomeBlock}>
          <h1 className={styles.welcomeTitle}>
            {isAdmin ? 'All Coaches Overview' : `Welcome back, ${userName}`}
          </h1>
          <p className={styles.welcomeSubtitle}>
            {isAdmin
              ? `${data.length} active coach${data.length !== 1 ? 'es' : ''} with ${grandTotalAccounts} accounts`
              : `${grandTotalAccounts} accounts, ${grandTotalClients} clients`}
          </p>
        </div>
      </div>

      {/* ── Stat Cards ── */}
      <div className={styles.statsGrid}>
        {statCards.map((s, i) => (
          <StatCard key={i} data={s} />
        ))}
      </div>

      {/* ── Clients per Account Bar Chart ── */}
      {chartData.length > 0 && (
        <div className={styles.chartsRow}>
          <div className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <div className={styles.cardTitle}>Clients per Account</div>
                <div className={styles.cardSubtitle}>
                  {allAccounts.length} account{allAccounts.length !== 1 ? 's' : ''} &middot;{' '}
                  {grandTotalClients} total clients
                </div>
              </div>
            </div>

            <div className={styles.chartWrapper}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="barCoach" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={BAR_COLORS.gradientStart} stopOpacity={1} />
                      <stop offset="100%" stopColor={BAR_COLORS.gradientEnd} stopOpacity={0.8} />
                    </linearGradient>
                  </defs>

                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke={BAR_COLORS.gridStroke}
                    vertical={false}
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: BAR_COLORS.axisTick, fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: BAR_COLORS.axisTick, fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    content={<ChartTooltip />}
                    cursor={{ fill: BAR_COLORS.cursorFill }}
                  />
                  <Bar
                    dataKey="Clients"
                    name="Clients"
                    fill="url(#barCoach)"
                    radius={[4, 4, 0, 0]}
                    barSize={32}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Coach Sections with Account Cards ── */}
      {data.map((entry) => (
        <div key={entry.coach.id} className={styles.coachSection}>
          {/* Coach header (shown always for admin, simplified for coach) */}
          <div className={styles.coachHeader}>
            <div>
              <h2 className={styles.coachName}>{entry.coach.name}</h2>
              {isAdmin && (
                <p className={styles.coachEmail}>{entry.coach.email}</p>
              )}
            </div>
            <div className={styles.coachMeta}>
              <span className={styles.coachMetaItem}>
                Accounts: <span className={styles.coachMetaValue}>{entry.total_accounts}</span>
              </span>
              <span className={styles.coachMetaItem}>
                Clients: <span className={styles.coachMetaValue}>{entry.total_clients}</span>
              </span>
            </div>
          </div>

          {/* Account Cards */}
          {entry.accounts.length === 0 ? (
            <div className={styles.emptyState}>No accounts assigned</div>
          ) : (
            <div className={styles.accountsGrid}>
              {entry.accounts.map((account) => (
                <div key={account.id} className={styles.accountCard}>
                  <div className={styles.accountCardHeader}>
                    <h3 className={styles.accountName}>{account.name}</h3>
                    <span className={styles.industryBadge}>{account.industry}</span>
                  </div>

                  {account.website && (
                    <div className={styles.accountMeta}>{account.website}</div>
                  )}

                  {account.contacts.length === 0 ? (
                    <div className={styles.accountMeta}>No contacts</div>
                  ) : (
                    <div className={styles.contactsList}>
                      {account.contacts.map((contact) => (
                        <div key={contact.id} className={styles.contactItem}>
                          <span className={styles.contactName}>{contact.name}</span>
                          <span className={styles.contactTitle}>{contact.title}</span>
                          <span className={styles.contactEmail}>{contact.email}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
