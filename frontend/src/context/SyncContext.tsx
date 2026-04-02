import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from 'react'
import http from '../api'
import { useAuth } from './AuthContext'

interface SyncResult {
  changes_detected: number
  status: 'completed' | 'failed'
  error?: string
}

interface SchemaChange {
  object: string
  field: string
  expected_type: string
  actual_type: string
}

interface SyncContextType {
  outOfSync: boolean
  syncing: boolean
  lastSynced: string | null
  syncResult: SyncResult | null
  showNotification: boolean
  schemaChanged: boolean
  schemaChanges: SchemaChange[]
  notificationMessage: string
  pullAndSync: () => Promise<void>
  dismissNotification: () => void
}

const SyncContext = createContext<SyncContextType | null>(null)

export function SyncProvider({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth()
  const [outOfSync, setOutOfSync] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [lastSynced, setLastSynced] = useState<string | null>(null)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [schemaChanged, setSchemaChanged] = useState(false)
  const [schemaChanges, setSchemaChanges] = useState<SchemaChange[]>([])
  const [notificationMessage, setNotificationMessage] = useState('')
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const checkStatus = useCallback(async () => {
    try {
      const res = await http.get('/sf-connector/status/')
      const isOutOfSync = res.data.out_of_sync === true
      setOutOfSync(isOutOfSync)
      if (res.data.last_synced) {
        setLastSynced(res.data.last_synced)
      }
      if (isOutOfSync && res.data.message) {
        setNotificationMessage(res.data.message)
      }
    } catch {
      // silently ignore status check failures
    }

    // Also check for schema changes from real Salesforce
    try {
      const schemaRes = await http.get('/sf-connector/schema-check/')
      if (schemaRes.data.schema_changed) {
        setSchemaChanged(true)
        setSchemaChanges(schemaRes.data.changes || [])
      } else {
        setSchemaChanged(false)
        setSchemaChanges([])
      }
    } catch {
      // SF connection might not be configured — ignore silently
    }
  }, [])

  // Poll every 15 seconds when user is admin
  useEffect(() => {
    if (!isAdmin) return

    checkStatus()
    // Poll every 30s as safety net — real-time detection comes via SF webhook
    intervalRef.current = setInterval(checkStatus, 30000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isAdmin, checkStatus])

  // Reset dismissed when outOfSync changes to true
  useEffect(() => {
    if (outOfSync) {
      setDismissed(false)
    }
  }, [outOfSync])

  const pullAndSync = useCallback(async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await http.post('/sf-connector/pull-and-sync/')
      const result: SyncResult = {
        changes_detected: res.data.sync?.changes_detected ?? res.data.changes_detected ?? 0,
        status: 'completed',
      }
      setSyncResult(result)
      setOutOfSync(false)
      setSchemaChanged(false)
      setSchemaChanges([])
      setLastSynced(new Date().toISOString())
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { error?: string } }; message?: string }
      setSyncResult({
        changes_detected: 0,
        status: 'failed',
        error: axiosErr.response?.data?.error || axiosErr.message || 'Sync failed',
      })
    } finally {
      setSyncing(false)
    }
  }, [])

  const dismissNotification = useCallback(() => {
    setDismissed(true)
    setSchemaChanged(false)
    setSchemaChanges([])
  }, [])

  const showNotification = outOfSync && !dismissed && !syncing

  return (
    <SyncContext.Provider
      value={{
        outOfSync,
        syncing,
        lastSynced,
        syncResult,
        showNotification,
        schemaChanged,
        schemaChanges,
        notificationMessage,
        pullAndSync,
        dismissNotification,
      }}
    >
      {children}
    </SyncContext.Provider>
  )
}

export function useSync() {
  const ctx = useContext(SyncContext)
  if (!ctx) throw new Error('useSync must be used within SyncProvider')
  return ctx
}
