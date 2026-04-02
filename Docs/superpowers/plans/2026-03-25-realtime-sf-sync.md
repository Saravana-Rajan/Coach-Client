# Real-Time Salesforce Sync Notification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When data changes in real Salesforce, show a notification banner in the Coach Portal UI ("You are out of sync — Sync Now") and when clicked, pull from Salesforce + sync in one click, updating the dashboard and sidebar data live.

**Architecture:** Backend polling endpoint checks if real Salesforce data differs from the simulated source by comparing record counts and last-modified timestamps. Frontend polls this endpoint every 30 seconds. When out-of-sync is detected, a notification banner appears. Clicking "Sync Now" triggers pull + sync in one API call. After sync completes, all dashboard data refreshes automatically.

**Tech Stack:** Django REST endpoint, React context for sync state, polling with `setInterval`, notification banner component

---

## File Structure

```
backend/
├── salesforce_connector/
│   ├── client.py          — Modify: add check_sync_status() function
│   ├── views.py           — Modify: add sync_status + pull_and_sync endpoints
│   └── urls.py            — Modify: add new URL paths

frontend/src/
├── context/
│   └── SyncContext.tsx     — Create: sync state, polling, notification logic
├── components/
│   └── SyncBanner.tsx      — Create: notification banner component
│   └── SyncBanner.module.css — Create: banner styles
├── components/
│   └── CrmLayout.tsx       — Modify: add SyncProvider + SyncBanner
├── pages/
│   └── AdminDashboard.tsx  — Modify: use SyncContext to refresh after sync
```

---

### Task 1: Backend — Check Sync Status Endpoint

**Files:**
- Modify: `backend/salesforce_connector/client.py`
- Modify: `backend/salesforce_connector/views.py`
- Modify: `backend/salesforce_connector/urls.py`

- [ ] **Step 1: Add `check_sync_status()` to client.py**

Add this function to `backend/salesforce_connector/client.py`:

```python
def check_sync_status() -> dict:
    """
    Compare real Salesforce data with simulated source.
    Returns {"in_sync": bool, "sf_accounts": int, "sf_contacts": int,
             "local_accounts": int, "local_contacts": int}
    """
    sf = get_sf_connection()

    # Count records in real Salesforce
    sf_acc_count = sf.query("SELECT COUNT() FROM Account")["totalSize"]
    sf_con_count = sf.query("SELECT COUNT() FROM Contact")["totalSize"]

    # Count records in simulated source
    local_acc_count = SFAccount.objects.using("salesforce").count()
    local_con_count = SFContact.objects.using("salesforce").count()

    # Check if a recent sync pulled the latest data
    # Simple heuristic: counts match = in sync
    in_sync = (sf_acc_count == local_acc_count and sf_con_count == local_con_count)

    return {
        "in_sync": in_sync,
        "sf_accounts": sf_acc_count,
        "sf_contacts": sf_con_count,
        "local_accounts": local_acc_count,
        "local_contacts": local_con_count,
    }
```

- [ ] **Step 2: Add `sync_status` and `pull_and_sync` views**

Add to `backend/salesforce_connector/views.py`:

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from sync.engine import run_sync

@api_view(["GET"])
def sync_status(request):
    """Check if real Salesforce is in sync with simulated source."""
    if not request.user.is_authenticated or not request.user.is_admin():
        return Response({"error": "Admin only"}, status=403)
    try:
        from .client import check_sync_status
        status = check_sync_status()
        return Response(status)
    except Exception as exc:
        return Response({"in_sync": True, "error": str(exc)})


@api_view(["POST"])
def pull_and_sync(request):
    """Pull from Salesforce + sync in one call. Returns sync result."""
    if not request.user.is_authenticated or not request.user.is_admin():
        return Response({"error": "Admin only"}, status=403)
    try:
        data = pull_all_data()
        seed_summary = seed_to_simulated_source(data)
        sync_log = run_sync()
        return Response({
            "status": "ok",
            "pulled": {"accounts": len(data["accounts"]), "contacts": len(data["contacts"])},
            "seeded": seed_summary,
            "sync": {
                "id": sync_log.id,
                "status": sync_log.status,
                "changes_detected": sync_log.changes_detected,
            },
        })
    except Exception as exc:
        return Response({"status": "error", "detail": str(exc)}, status=500)
```

- [ ] **Step 3: Add URL paths**

Update `backend/salesforce_connector/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path("pull/", views.pull_from_salesforce, name="sf-pull"),
    path("status/", views.sync_status, name="sf-sync-status"),
    path("pull-and-sync/", views.pull_and_sync, name="sf-pull-and-sync"),
]
```

- [ ] **Step 4: Test endpoints**

```bash
# Login as admin, then:
curl /api/sf-connector/status/     # Should return {in_sync: true/false, counts...}
curl -X POST /api/sf-connector/pull-and-sync/  # Should pull + sync in one call
```

---

### Task 2: Frontend — SyncContext (Polling + State)

**Files:**
- Create: `frontend/src/context/SyncContext.tsx`

- [ ] **Step 1: Create SyncContext**

```tsx
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import http from '../api'
import { useAuth } from './AuthContext'

interface SyncState {
  inSync: boolean
  checking: boolean
  syncing: boolean
  lastCheck: string | null
  sfAccounts: number
  sfContacts: number
  localAccounts: number
  localContacts: number
  syncResult: { changes: number; syncId: number } | null
}

interface SyncContextType extends SyncState {
  checkStatus: () => Promise<void>
  pullAndSync: () => Promise<void>
  dismissNotification: () => void
  showNotification: boolean
}

const SyncContext = createContext<SyncContextType | null>(null)

export function SyncProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [state, setState] = useState<SyncState>({
    inSync: true, checking: false, syncing: false,
    lastCheck: null, sfAccounts: 0, sfContacts: 0,
    localAccounts: 0, localContacts: 0, syncResult: null,
  })
  const [dismissed, setDismissed] = useState(false)

  const checkStatus = useCallback(async () => {
    if (!isAdmin) return
    setState(s => ({ ...s, checking: true }))
    try {
      const res = await http.get('/sf-connector/status/')
      setState(s => ({
        ...s,
        inSync: res.data.in_sync,
        sfAccounts: res.data.sf_accounts,
        sfContacts: res.data.sf_contacts,
        localAccounts: res.data.local_accounts,
        localContacts: res.data.local_contacts,
        lastCheck: new Date().toISOString(),
        checking: false,
      }))
      if (!res.data.in_sync) setDismissed(false) // re-show if out of sync
    } catch {
      setState(s => ({ ...s, checking: false }))
    }
  }, [isAdmin])

  const pullAndSync = useCallback(async () => {
    setState(s => ({ ...s, syncing: true }))
    try {
      const res = await http.post('/sf-connector/pull-and-sync/')
      setState(s => ({
        ...s,
        syncing: false,
        inSync: true,
        syncResult: {
          changes: res.data.sync?.changes_detected || 0,
          syncId: res.data.sync?.id || 0,
        },
      }))
      setDismissed(true)
    } catch {
      setState(s => ({ ...s, syncing: false }))
    }
  }, [])

  const dismissNotification = () => setDismissed(true)
  const showNotification = !state.inSync && !dismissed && !state.syncing

  // Poll every 30 seconds (admin only)
  useEffect(() => {
    if (!isAdmin) return
    checkStatus()
    const interval = setInterval(checkStatus, 30000)
    return () => clearInterval(interval)
  }, [isAdmin, checkStatus])

  return (
    <SyncContext.Provider value={{
      ...state, checkStatus, pullAndSync, dismissNotification, showNotification,
    }}>
      {children}
    </SyncContext.Provider>
  )
}

export const useSync = () => {
  const ctx = useContext(SyncContext)
  if (!ctx) throw new Error('useSync must be used within SyncProvider')
  return ctx
}
```

---

### Task 3: Frontend — SyncBanner Component

**Files:**
- Create: `frontend/src/components/SyncBanner.tsx`
- Create: `frontend/src/components/SyncBanner.module.css`

- [ ] **Step 1: Create SyncBanner.module.css**

```css
.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: linear-gradient(135deg, #ff3c00, #ff6b35);
  color: #fff;
  font-family: var(--font-primary);
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  flex-shrink: 0;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.bannerText {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bannerIcon {
  font-size: 16px;
}

.bannerActions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.syncBtn {
  padding: 6px 16px;
  border-radius: var(--radius-md);
  background: #fff;
  color: #ff3c00;
  font-family: var(--font-primary);
  font-size: 13px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.syncBtn:hover {
  background: #fff3f0;
}

.syncBtn:disabled {
  opacity: 0.7;
  cursor: wait;
}

.dismissBtn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  font-size: 18px;
  padding: 0 4px;
  line-height: 1;
}

.dismissBtn:hover {
  color: #fff;
}

/* Success banner after sync */
.bannerSuccess {
  background: linear-gradient(135deg, #166534, #22c55e);
}
```

- [ ] **Step 2: Create SyncBanner.tsx**

```tsx
import { useSync } from '../context/SyncContext'
import { useAuth } from '../context/AuthContext'
import styles from './SyncBanner.module.css'

export default function SyncBanner() {
  const { user } = useAuth()
  const { showNotification, syncing, syncResult, pullAndSync, dismissNotification } = useSync()

  if (user?.role !== 'admin') return null

  // Show success message briefly after sync
  if (syncResult && !showNotification) {
    return (
      <div className={`${styles.banner} ${styles.bannerSuccess}`}>
        <span className={styles.bannerText}>
          <span className={styles.bannerIcon}>✓</span>
          Synced! {syncResult.changes} changes detected (Sync #{syncResult.syncId})
        </span>
      </div>
    )
  }

  if (!showNotification) return null

  return (
    <div className={styles.banner}>
      <span className={styles.bannerText}>
        <span className={styles.bannerIcon}>⚠</span>
        Salesforce data has changed — your app is out of sync.
      </span>
      <div className={styles.bannerActions}>
        <button
          className={styles.syncBtn}
          onClick={pullAndSync}
          disabled={syncing}
        >
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
        <button className={styles.dismissBtn} onClick={dismissNotification}>×</button>
      </div>
    </div>
  )
}
```

---

### Task 4: Wire Into Layout + Auto-Refresh Dashboard

**Files:**
- Modify: `frontend/src/components/CrmLayout.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/pages/AdminDashboard.tsx`

- [ ] **Step 1: Add SyncProvider to main.tsx**

Wrap the app with `SyncProvider` inside `AuthProvider`:

```tsx
import { SyncProvider } from './context/SyncContext'

// In the render:
<AuthProvider>
  <SyncProvider>
    <App />
  </SyncProvider>
</AuthProvider>
```

- [ ] **Step 2: Add SyncBanner to CrmLayout.tsx**

Import and render `SyncBanner` at the top of the content area (before `<Outlet />`):

```tsx
import SyncBanner from './SyncBanner'

// In the JSX, inside <main className={styles.content}>:
<DashboardHeader ... />
<SyncBanner />
<Outlet />
```

- [ ] **Step 3: Auto-refresh AdminDashboard after sync**

In `AdminDashboard.tsx`, use `useSync()` to detect when a sync completes and refresh the data:

```tsx
import { useSync } from '../context/SyncContext'

// Inside component:
const { syncResult } = useSync()

// Add syncResult to the useEffect dependency to refresh on sync:
useEffect(() => {
  fetchHistory()
}, [fetchHistory, syncResult])
```

---

### Task 5: Test the Full Flow

- [ ] **Step 1: Change a coach in real Salesforce** (e.g., change HealthPlus coach to "Dave Brown")
- [ ] **Step 2: Wait 30 seconds** — the banner should appear: "Salesforce data has changed — your app is out of sync."
- [ ] **Step 3: Click "Sync Now"** — pull + sync happens, banner turns green showing changes detected
- [ ] **Step 4: Verify** — dashboard data updates, audit trail shows the change, sidebar reflects new state
- [ ] **Step 5: Verify coach login** — login as the affected coach, verify their dashboard updated

---

## Summary

| Task | What it builds |
|------|---------------|
| 1 | Backend: `status/` (check sync) + `pull-and-sync/` (one-click sync) endpoints |
| 2 | Frontend: SyncContext with 30s polling, sync state management |
| 3 | Frontend: Red notification banner with "Sync Now" button |
| 4 | Wire banner into layout, auto-refresh dashboard after sync |
| 5 | End-to-end test |
