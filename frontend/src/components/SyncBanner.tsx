import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useSync } from '../context/SyncContext'
import styles from './SyncBanner.module.css'

export default function SyncBanner() {
  const { isAdmin } = useAuth()
  const { showNotification, syncing, syncResult, pullAndSync, dismissNotification, schemaChanged, schemaChanges, notificationMessage } = useSync()
  const [showSuccess, setShowSuccess] = useState(false)
  const location = useLocation()

  // Auto-show and auto-hide success banner
  useEffect(() => {
    if (syncResult?.status === 'completed') {
      setShowSuccess(true)
      const timer = setTimeout(() => setShowSuccess(false), 5000)
      return () => clearTimeout(timer)
    }
    setShowSuccess(false)
  }, [syncResult])

  // Dismiss success banner on navigation
  useEffect(() => {
    setShowSuccess(false)
  }, [location.pathname])

  if (!isAdmin) return null

  // Syncing state
  if (syncing) {
    return (
      <div className={`${styles.banner} ${styles.bannerSyncing}`}>
        <div className={styles.messageWrap}>
          <span>Syncing...</span>
        </div>
        <div className={styles.actions}>
          <button className={styles.syncBtn} disabled>
            Sync Now
          </button>
        </div>
      </div>
    )
  }

  // Success state
  if (showSuccess && syncResult?.status === 'completed') {
    return (
      <div className={`${styles.banner} ${styles.bannerSuccess}`}>
        <div className={styles.messageWrap}>
          <span>Synced! {syncResult.changes_detected} changes detected</span>
        </div>
      </div>
    )
  }

  // Schema change detected
  if (schemaChanged && schemaChanges.length > 0) {
    const summary = schemaChanges
      .map(c => `${c.field}: ${c.expected_type} → ${c.actual_type}`)
      .join(', ')
    return (
      <div className={`${styles.banner} ${styles.bannerSchema}`}>
        <div className={styles.messageWrap}>
          <svg
            className={styles.warningIcon}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <span>Salesforce schema changed — {summary}</span>
        </div>
        <div className={styles.actions}>
          <button className={styles.syncBtn} onClick={pullAndSync}>
            Sync & Auto-Migrate
          </button>
          <button
            className={styles.dismissBtn}
            onClick={dismissNotification}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      </div>
    )
  }

  // Out of sync state (data change)
  if (showNotification) {
    return (
      <div className={`${styles.banner} ${styles.bannerOutOfSync}`}>
        <div className={styles.messageWrap}>
          <svg
            className={styles.warningIcon}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span>{notificationMessage || 'Salesforce data has changed — your app is out of sync'}</span>
        </div>
        <div className={styles.actions}>
          <button className={styles.syncBtn} onClick={pullAndSync}>
            Sync Now
          </button>
          <button
            className={styles.dismissBtn}
            onClick={dismissNotification}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      </div>
    )
  }

  return null
}
