import { useState, useMemo, useEffect, useCallback, useRef } from 'react'
import styles from './AuditTrailPage.module.css'

/* ────────────────────────────────────────────
   Types
   ──────────────────────────────────────────── */
interface AuditRecord {
  id: number
  detected_at: string
  change_type: string
  entity_type: string
  entity_name: string
  entity_sf_id: string
  before_state: Record<string, unknown> | null
  after_state: Record<string, unknown> | null
  coach_name: string
  account_name: string
  sync_id: number
}

/* ────────────────────────────────────────────
   Badge helper
   ──────────────────────────────────────────── */
function getBadgeClass(changeType: string): string {
  if (changeType.includes('reassigned')) return styles.badgeReassigned
  if (changeType.includes('added')) return styles.badgeAdded
  if (changeType.includes('removed')) return styles.badgeRemoved
  if (changeType.includes('updated')) return styles.badgeUpdated
  return styles.badgeDeactivated
}

const CHANGE_TYPE_OPTIONS: string[] = [
  'coach_added', 'coach_removed', 'coach_updated',
  'account_added', 'account_removed', 'account_reassigned',
  'contact_added', 'contact_removed', 'contact_reassigned',
  'assignment_added', 'assignment_removed',
]

/* ────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────── */
function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function formatState(state: Record<string, unknown> | null): string {
  if (!state) return '—'
  const keys = Object.keys(state)
  if (keys.length === 0) return '—'
  if (keys.length === 1) {
    if (keys[0] === 'coach') return String(state.coach)
    if (keys[0] === 'status') return String(state.status)
    return `${keys[0]}: ${String(state[keys[0]])}`
  }
  return keys.map(k => `${k}: ${String(state[k])}`).join('\n')
}

/* ────────────────────────────────────────────
   Component
   ──────────────────────────────────────────── */
export default function AuditTrailPage() {
  /* ── Data state ── */
  const [records, setRecords] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(true)

  /* ── Search state ── */
  const [search, setSearch] = useState('')
  const [searchDebounced, setSearchDebounced] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(search), 300)
    return () => clearTimeout(t)
  }, [search])

  /* ── Filter state ── */
  const [changeTypeFilter, setChangeTypeFilter] = useState<string>('')
  const [showFilters, setShowFilters] = useState(false)
  const [filterView, setFilterView] = useState<'menu' | 'coach' | 'account'>('menu')
  const [coachFilter, setCoachFilter] = useState('')
  const [accountFilter, setAccountFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  /* ── Pagination state ── */
  const [currentPage, setCurrentPage] = useState(1)
  const [rowsPerPage, setRowsPerPage] = useState(20)

  /* ── Fetch audit records from API ── */
  const fetchRecords = useCallback(async () => {
    setLoading(true)
    try {
      const { default: http } = await import('../api')
      const res = await http.get('/sync/audit/')
      setRecords(res.data.results ?? res.data)
    } catch (err) {
      console.error('Error loading audit trail:', err)
      setRecords([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRecords()
  }, [fetchRecords])

  /* ── Filtered records ── */
  const filtered = useMemo(() => {
    let result = records

    // Search: matches entity_name or coach_name
    if (searchDebounced.trim()) {
      const q = searchDebounced.trim().toLowerCase()
      result = result.filter(r =>
        (r.entity_name || '').toLowerCase().includes(q) ||
        (r.coach_name || '').toLowerCase().includes(q)
      )
    }

    if (changeTypeFilter) {
      result = result.filter(r => r.change_type === changeTypeFilter)
    }
    if (coachFilter.trim()) {
      const q = coachFilter.trim().toLowerCase()
      result = result.filter(r => (r.coach_name || '').toLowerCase().includes(q))
    }
    if (accountFilter.trim()) {
      const q = accountFilter.trim().toLowerCase()
      result = result.filter(r => (r.account_name || '').toLowerCase().includes(q))
    }
    if (dateFrom) {
      const from = new Date(dateFrom)
      from.setHours(0, 0, 0, 0)
      result = result.filter(r => new Date(r.detected_at) >= from)
    }
    if (dateTo) {
      const to = new Date(dateTo)
      to.setHours(23, 59, 59, 999)
      result = result.filter(r => new Date(r.detected_at) <= to)
    }

    return result
  }, [records, searchDebounced, changeTypeFilter, coachFilter, accountFilter, dateFrom, dateTo])

  /* ── Reset page when filters change ── */
  useEffect(() => {
    setCurrentPage(1)
  }, [searchDebounced, changeTypeFilter, coachFilter, accountFilter, dateFrom, dateTo])

  /* ── Pagination derived values ── */
  const totalPages = Math.ceil(filtered.length / rowsPerPage) || 1
  const paginatedRecords = filtered.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  )

  /* ── Clear all filters ── */
  const clearFilters = () => {
    setCoachFilter('')
    setAccountFilter('')
    setDateFrom('')
    setDateTo('')
  }

  const hasExpandedFilters =
    coachFilter !== '' ||
    accountFilter !== '' ||
    dateFrom !== '' ||
    dateTo !== ''

  const activeFilterCount =
    (coachFilter ? 1 : 0) +
    (accountFilter ? 1 : 0) +
    (dateFrom ? 1 : 0) +
    (dateTo ? 1 : 0)

  /* ── Click-outside handler for filter panel ── */
  const filterPanelRef = useRef<HTMLDivElement>(null)
  const filterBtnRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!showFilters) return
    function handleClickOutside(e: MouseEvent) {
      if (
        filterPanelRef.current && !filterPanelRef.current.contains(e.target as Node) &&
        filterBtnRef.current && !filterBtnRef.current.contains(e.target as Node)
      ) {
        setShowFilters(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showFilters])

  /* ── Render ── */
  if (loading) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner} />
          <span className={styles.loadingText}>Loading audit records...</span>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.wrapper}>
      {/* ── Toolbar ── */}
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <div className={styles.searchWrap}>
            <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="M16.5 16.5L20 20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              className={styles.searchInput}
              type="text"
              placeholder="Search entity, coach..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button className={styles.clearSearch} onClick={() => setSearch('')} type="button">
                &times;
              </button>
            )}
          </div>
        </div>

        <div className={styles.toolbarRight}>
          {/* Change Type dropdown */}
          <select
            className={styles.filterSelect}
            value={changeTypeFilter}
            onChange={e => setChangeTypeFilter(e.target.value)}
          >
            <option value="">All Types</option>
            {CHANGE_TYPE_OPTIONS.map(t => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>

          {/* Filter toggle button */}
          <button
            ref={filterBtnRef}
            type="button"
            className={`${styles.toolBtn} ${showFilters ? styles.toolBtnActive : ''}`}
            onClick={() => setShowFilters(v => !v)}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
            </svg>
            <span>Filter</span>
            {activeFilterCount > 0 && (
              <span className={styles.filterBadge}>{activeFilterCount}</span>
            )}
          </button>

          {/* ── Filter dropdown panel ── */}
          {showFilters && (
            <div className={styles.filterPanel} ref={filterPanelRef}>
              {filterView === 'menu' ? (
                <>
                  <div className={styles.filterPanelHeader}>
                    <span className={styles.filterPanelTitle}>Filter by</span>
                    {(coachFilter || accountFilter) && (
                      <button type="button" className={styles.filterClearLink} onClick={() => { setCoachFilter(''); setAccountFilter(''); }}>
                        Clear all
                      </button>
                    )}
                  </div>
                  <div className={styles.filterPanelBody}>
                    <button type="button" className={styles.filterMenuItem} onClick={() => setFilterView('coach')}>
                      <span>Coach</span>
                      {coachFilter && <span className={styles.filterMenuActiveValue}>{coachFilter}</span>}
                    </button>
                    <button type="button" className={styles.filterMenuItem} onClick={() => setFilterView('account')}>
                      <span>Account</span>
                      {accountFilter && <span className={styles.filterMenuActiveValue}>{accountFilter}</span>}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className={styles.filterPanelHeader}>
                    <span className={styles.filterPanelTitle}>Filter by</span>
                  </div>
                  <div className={styles.filterPanelHeader} style={{ paddingTop: 0 }}>
                    <button type="button" className={styles.filterPanelBack} onClick={() => setFilterView('menu')}>&#8592;</button>
                    <span style={{ fontWeight: 500, fontSize: '14px', color: 'var(--pm-text-primary)' }}>{filterView === 'coach' ? 'Coach' : 'Account'}</span>
                  </div>
                  <select
                    className={styles.filterCategorySelect}
                    value={filterView === 'coach' ? (coachFilter || '') : (accountFilter || '')}
                    onChange={e => {
                      if (filterView === 'coach') setCoachFilter(e.target.value)
                      else setAccountFilter(e.target.value)
                    }}
                  >
                    <option value="">All</option>
                    {[...new Set(records.map(r => filterView === 'coach' ? r.coach_name : r.account_name).filter(Boolean))].sort().map(name => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Table ── */}
      <div className={styles.tableArea}>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Time</th>
                <th className={styles.th}>Type</th>
                <th className={styles.th}>Entity</th>
                <th className={styles.th}>Before</th>
                <th className={styles.th}>After</th>
                <th className={styles.th}>Coach</th>
                <th className={styles.th}>Sync #</th>
              </tr>
            </thead>
            <tbody>
              {paginatedRecords.map(record => (
                <tr key={record.id} className={styles.tr}>
                  <td className={styles.td}>
                    {formatTimestamp(record.detected_at)}
                  </td>
                  <td className={styles.td}>
                    <span
                      className={`${styles.badge} ${getBadgeClass(record.change_type)}`}
                    >
                      {record.change_type}
                    </span>
                  </td>
                  <td className={styles.td} title={`${record.entity_type}: ${record.entity_name}`}>
                    <strong>{record.entity_type}</strong>
                    {' — '}
                    {record.entity_name}
                  </td>
                  <td className={styles.tdWrap}>
                    {formatState(record.before_state)}
                  </td>
                  <td className={`${styles.tdWrap} ${styles.tdAfter}`}>
                    {formatState(record.after_state)}
                  </td>
                  <td className={styles.td}>{record.coach_name || '—'}</td>
                  <td className={styles.td}>
                    <span className={styles.syncPill}>
                      #{record.sync_id}
                    </span>
                  </td>
                </tr>
              ))}
              {paginatedRecords.length === 0 && (
                <tr>
                  <td colSpan={7} className={styles.emptyRow}>
                    {records.length === 0
                      ? 'No audit records yet. Run a sync to detect changes.'
                      : 'No records match the current filters.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>


      {/* ── Table Footer: record count + pagination ── */}
        <div className={styles.tableFooter}>
          <div className={styles.footerLeft}>
            Showing{' '}
            <span className={styles.resultCountBold}>{paginatedRecords.length}</span>
            {' '}of{' '}
            <span className={styles.resultCountBold}>{filtered.length}</span>
            {' '}records
          </div>

          <div className={styles.footerCenter}>
            <button
              type="button"
              className={styles.pageBtn}
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage(p => p - 1)}
              aria-label="Previous page"
            >
              &#8249;
            </button>
            <span className={styles.pageInfo}>
              Page {currentPage} of {totalPages}
            </span>
            <button
              type="button"
              className={styles.pageBtn}
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage(p => p + 1)}
              aria-label="Next page"
            >
              &#8250;
            </button>
          </div>

          <div className={styles.footerRight}>
            <span className={styles.footerLabel}>Rows per page</span>
            <select
              className={styles.rowsSelect}
              value={rowsPerPage}
              onChange={e => {
                setRowsPerPage(Number(e.target.value))
                setCurrentPage(1)
              }}
            >
              {[10, 20, 30, 50].map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}
