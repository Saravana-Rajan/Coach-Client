import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';
import { useSync } from '../context/SyncContext';
import StatCard from '../components/StatCard';
import styles from './AdminDashboard.module.css';

/* ── Types ── */
interface SyncLogEntry {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: 'in_progress' | 'completed' | 'failed';
  changes_detected: number;
  error_message: string;
}

/* ── PNG Icon imports for StatCards ── */
import iconCloudAlt from '../assets/icons/cloud_alt.png';
import iconSuccess from '../assets/icons/success.png';
import iconGrowth from '../assets/icons/growth.png';

/* ── Helpers ── */
function getBadgeClass(status: SyncLogEntry['status']): string {
  switch (status) {
    case 'completed':
      return styles.badgeCompleted;
    case 'failed':
      return styles.badgeFailed;
    case 'in_progress':
      return styles.badgeInProgress;
    default:
      return '';
  }
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
}

function formatDuration(start: string, end: string | null): string {
  if (!end) return '--';
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/* ── Component ── */
export default function AdminDashboard() {
  const { syncResult, pullAndSync } = useSync();
  const [syncHistory, setSyncHistory] = useState<SyncLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get('/sync/history/');
      setSyncHistory(res.data);
    } catch {
      setSyncHistory([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, syncResult]);

  const triggerSync = async () => {
    setSyncing(true);
    setMessage('');
    try {
      await pullAndSync();
      // pullAndSync updates SyncContext — get changes from latest sync history
      fetchHistory();
      setMessage('Sync completed');
      setMessageType('success');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: string } }; message?: string };
      setMessage('Sync failed: ' + (axiosErr.response?.data?.error || axiosErr.message || 'Unknown error'));
      setMessageType('error');
    } finally {
      setSyncing(false);
    }
  };

  /* ── Derived stats ── */
  const totalSyncs = syncHistory.length;
  const lastSync = syncHistory.length > 0 ? syncHistory[0] : null;
  const lastSyncStatus = lastSync
    ? lastSync.status.replace('_', ' ').replace(/bw/g, (c) => c.toUpperCase())
    : 'N/A';
  const totalChanges = syncHistory.reduce((sum, s) => sum + s.changes_detected, 0);

  /* ── Render ── */
  if (loading) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinnerOuter} />
          <span className={styles.loadingText}>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      {/* ── Stat Cards ── */}
      <div className={styles.statsRow}>
        <StatCard
          title="Total Syncs"
          value={totalSyncs}
          icon={<img src={iconCloudAlt} alt="" width={20} height={20} />}
        />
        <StatCard
          title="Last Sync Status"
          value={lastSyncStatus}
          icon={<img src={iconSuccess} alt="" width={20} height={20} />}
        />
        <StatCard
          title="Total Changes Detected"
          value={totalChanges}
          icon={<img src={iconGrowth} alt="" width={20} height={20} />}
        />
      </div>

      {/* ── Toolbar: Sync Controls ── */}
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <h2 className={styles.sectionTitle}>Sync History</h2>
        </div>
        <div className={styles.toolbarRight}>
          {message && (
            <span
              className={`${styles.statusMessage} ${
                messageType === 'success' ? styles.statusSuccess : styles.statusError
              }`}
            >
              {message}
            </span>
          )}
          <button
            className={styles.syncBtn}
            onClick={triggerSync}
            disabled={syncing}
          >
            {syncing ? 'Syncing...' : 'Trigger Sync'}
          </button>
        </div>
      </div>

      {/* ── Sync History Table ── */}
      <div className={styles.tableWrap}>
        {syncHistory.length === 0 ? (
          <div className={styles.empty}>
            No sync history yet. Trigger your first sync above.
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>ID</th>
                <th className={styles.th}>Started</th>
                <th className={styles.th}>Duration</th>
                <th className={styles.th}>Status</th>
                <th className={styles.th}>Changes</th>
                <th className={styles.th}>Error</th>
              </tr>
            </thead>
            <tbody>
              {syncHistory.map((sync) => (
                <tr key={sync.id} className={styles.tr}>
                  <td className={styles.td}>#{sync.id}</td>
                  <td className={styles.td}>{formatDateTime(sync.started_at)}</td>
                  <td className={styles.td}>
                    {formatDuration(sync.started_at, sync.completed_at)}
                  </td>
                  <td className={styles.td}>
                    <span className={`${styles.badge} ${getBadgeClass(sync.status)}`}>
                      {sync.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className={styles.td}>{sync.changes_detected}</td>
                  <td className={styles.td} title={sync.error_message}>
                    {sync.error_message || '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
