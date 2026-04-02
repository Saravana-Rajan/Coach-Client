import { useState, useEffect, useCallback } from 'react'
import styles from './TransitionBriefsPage.module.css'

/* ── Types ── */
type TransitionBrief = {
  id: number
  contact_name: string
  account_name: string
  previous_coach_name: string
  coach_name: string
  generated_at: string
  content: string
  sync_id: number
}

/* ── Helpers ── */
function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

/* ── Inline markdown renderer (bold / italic) ── */
function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className={styles.contentBold}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={i}>{part.slice(1, -1)}</em>
    }
    return part
  })
}

/* ── Brief content renderer ── */
function BriefContent({ content }: { content: string }) {
  const lines = content.split('\n')

  // First pass: classify each line
  type LineInfo =
    | { type: 'spacer' }
    | { type: 'h1'; text: string }
    | { type: 'h2'; text: string }
    | { type: 'h3'; text: string }
    | { type: 'ul'; text: string }
    | { type: 'ol'; text: string }
    | { type: 'p'; text: string }

  const classified: LineInfo[] = lines.map((line) => {
    const trimmed = line.trim()
    if (!trimmed) return { type: 'spacer' }
    if (trimmed.startsWith('### ')) return { type: 'h3', text: trimmed.slice(4) }
    if (trimmed.startsWith('## ')) return { type: 'h2', text: trimmed.slice(3) }
    if (trimmed.startsWith('# ')) return { type: 'h1', text: trimmed.slice(2) }
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) return { type: 'ul', text: trimmed.slice(2) }
    if (/^\d+\.\s/.test(trimmed)) return { type: 'ol', text: trimmed.replace(/^\d+\.\s/, '') }
    return { type: 'p', text: trimmed }
  })

  // Second pass: group consecutive list items and render
  const elements: React.ReactNode[] = []
  let idx = 0
  let key = 0

  while (idx < classified.length) {
    const info = classified[idx]

    if (info.type === 'spacer') {
      elements.push(<div key={key++} className={styles.contentSpacer} />)
      idx++
    } else if (info.type === 'h1') {
      elements.push(<h2 key={key++} className={styles.contentH1}>{renderInline(info.text)}</h2>)
      idx++
    } else if (info.type === 'h2') {
      elements.push(<h3 key={key++} className={styles.contentH2}>{renderInline(info.text)}</h3>)
      idx++
    } else if (info.type === 'h3') {
      elements.push(<h4 key={key++} className={styles.contentH3}>{renderInline(info.text)}</h4>)
      idx++
    } else if (info.type === 'ul') {
      const items: React.ReactNode[] = []
      while (idx < classified.length && classified[idx].type === 'ul') {
        const li = classified[idx] as { type: 'ul'; text: string }
        items.push(<li key={idx} className={styles.contentListItem}>{renderInline(li.text)}</li>)
        idx++
      }
      elements.push(<ul key={key++} className={styles.contentList}>{items}</ul>)
    } else if (info.type === 'ol') {
      const items: React.ReactNode[] = []
      while (idx < classified.length && classified[idx].type === 'ol') {
        const li = classified[idx] as { type: 'ol'; text: string }
        items.push(<li key={idx} className={styles.contentListItemOrdered}>{renderInline(li.text)}</li>)
        idx++
      }
      elements.push(<ol key={key++} className={styles.contentListOrdered}>{items}</ol>)
    } else {
      elements.push(<p key={key++} className={styles.contentParagraph}>{renderInline(info.text)}</p>)
      idx++
    }
  }

  return <div className={styles.contentBody}>{elements}</div>
}

/* ── Main Page ── */
export default function TransitionBriefsPage() {
  const [briefs, setBriefs] = useState<TransitionBrief[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchBriefs = useCallback(async () => {
    try {
      setLoading(true)
      const { default: http } = await import('../api')
      const res = await http.get('/briefs/')
      const data = res.data
      const list: TransitionBrief[] = Array.isArray(data) ? data : data.results ?? []
      setBriefs(list)
      if (list.length > 0 && selectedId === null) {
        setSelectedId(list[0].id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  useEffect(() => {
    fetchBriefs()
  }, [fetchBriefs])

  const filtered = briefs.filter((b) => {
    if (!searchTerm) return true
    const q = searchTerm.toLowerCase()
    return (
      b.contact_name.toLowerCase().includes(q) ||
      b.account_name.toLowerCase().includes(q) ||
      b.previous_coach_name.toLowerCase().includes(q) ||
      b.coach_name.toLowerCase().includes(q)
    )
  })

  const selected = briefs.find((b) => b.id === selectedId) ?? null

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinnerOuter} />
          <span className={styles.loadingText}>Loading transition briefs...</span>
        </div>
      </div>
    )
  }

  /* ── Error state ── */
  if (error) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />
              <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <h3 className={styles.emptyTitle}>Error Loading Briefs</h3>
          <p className={styles.emptyDescription}>{error}</p>
          <button className={styles.retryBtn} onClick={fetchBriefs} type="button">
            Retry
          </button>
        </div>
      </div>
    )
  }

  /* ── Empty state (no briefs at all) ── */
  if (briefs.length === 0) {
    return (
      <div className={styles.wrapper}>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
              <path
                d="M9 12h6M12 9v6M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h3 className={styles.emptyTitle}>No Transition Briefs Yet</h3>
          <p className={styles.emptyDescription}>
            Transition briefs are automatically generated when a client is reassigned to a new coach.
            Run a sync to detect reassignments.
          </p>
        </div>
      </div>
    )
  }

  /* ── Main layout ── */
  return (
    <div className={styles.wrapper}>
      {/* Two-column detail body */}
      <div className={styles.detailBody}>
        {/* LEFT: Brief list panel */}
        <aside className={styles.listPanel}>
          {/* Search */}
          <div className={styles.searchWrap}>
            <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
              <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              className={styles.searchInput}
              type="text"
              placeholder="Search briefs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button
                className={styles.clearSearch}
                onClick={() => setSearchTerm('')}
                type="button"
              >
                &times;
              </button>
            )}
          </div>

          {/* Card list */}
          <div className={styles.cardList}>
            {filtered.length === 0 ? (
              <div className={styles.noResults}>No briefs match your search.</div>
            ) : (
              filtered.map((brief) => (
                <button
                  key={brief.id}
                  className={`${styles.briefCard} ${
                    selectedId === brief.id ? styles.briefCardActive : ''
                  }`}
                  onClick={() => setSelectedId(brief.id)}
                  type="button"
                >
                  <div className={styles.cardAvatar}>
                    {getInitials(brief.contact_name)}
                  </div>
                  <div className={styles.cardInfo}>
                    <span className={styles.cardName}>{brief.contact_name}</span>
                    <span className={styles.cardAccount}>{brief.account_name}</span>
                    <div className={styles.cardMeta}>
                      <span className={styles.cardCoaches}>
                        <span className={styles.cardCoachFrom}>{brief.previous_coach_name}</span>
                        <span className={styles.cardCoachArrow}>&rarr;</span>
                        <span className={styles.cardCoachTo}>{brief.coach_name}</span>
                      </span>
                      <span className={styles.cardDate}>{formatDate(brief.generated_at)}</span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* RIGHT: Brief detail panel */}
        <main className={styles.detailPanel}>
          {selected ? (
            <>
              {/* Detail header */}
              <div className={styles.detailHeader}>
                <div className={styles.detailAvatar}>
                  {getInitials(selected.contact_name)}
                </div>
                <div className={styles.detailHeaderInfo}>
                  <h2 className={styles.detailTitle}>{selected.contact_name}</h2>
                  <div className={styles.detailSubtitle}>
                    <span className={styles.detailAccount}>{selected.account_name}</span>
                    <span className={styles.detailDivider}>&bull;</span>
                    <span className={styles.detailDate}>
                      Generated {formatDateTime(selected.generated_at)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Coach reassignment badge row */}
              <div className={styles.reassignmentRow}>
                <div className={`${styles.coachBadge} ${styles.coachBadgePrev}`}>
                  <span className={styles.coachBadgeLabel}>Previous Coach</span>
                  <span className={styles.coachBadgeValuePrev}>{selected.previous_coach_name}</span>
                </div>
                <div className={styles.arrowIcon}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M5 12h14M13 6l6 6-6 6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className={`${styles.coachBadge} ${styles.coachBadgeNew}`}>
                  <span className={styles.coachBadgeLabel}>New Coach</span>
                  <span className={styles.coachBadgeValueNew}>{selected.coach_name}</span>
                </div>
                <div className={styles.syncBadge}>
                  Sync #{selected.sync_id}
                </div>
              </div>

              {/* Brief content */}
              <div className={styles.detailContent}>
                <BriefContent content={selected.content} />
              </div>
            </>
          ) : (
            <div className={styles.detailEmpty}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                <path
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <p>Select a brief from the list to view its details.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
