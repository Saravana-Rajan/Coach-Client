import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import styles from './LoginPage.module.css'

/* ── Floating bubble icons ── */
function DashboardIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  )
}

function PeopleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  )
}

function SyncIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  )
}

/* ── Coach IQ Globe Logo ── */
function CoachIQLogo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M39.1481 43.392C41.974 38.7988 43.6921 32.6868 43.6921 25.9988C43.6921 19.3108 41.9691 13.2111 39.1481 8.60555C41.557 10.4244 43.5621 12.7235 45.0366 15.3573C46.5111 17.991 47.4229 20.9022 47.7143 23.9065H51.9137C51.3734 17.2142 48.265 10.9905 43.2395 6.53829C38.2139 2.08611 31.6608 -0.249272 24.9522 0.0211106C18.2437 0.291493 11.8998 3.14667 7.24883 7.98886C2.59787 12.831 0.000488281 19.2848 0.000488281 25.9988C0.000488281 32.7128 2.59787 39.1665 7.24883 44.0087C11.8998 48.8509 18.2437 51.7061 24.9522 51.9765C31.6608 52.2468 38.2139 49.9115 43.2395 45.4593C48.265 41.0071 51.3734 34.7833 51.9137 28.0911H47.7143C47.4229 31.0954 46.5111 34.0065 45.0366 36.6403C43.5621 39.2741 41.557 41.5731 39.1481 43.392ZM21.3315 23.9065C21.4768 18.9219 22.1365 14.1908 23.2245 10.4074C24.2485 6.8554 25.3758 5.10525 25.9986 4.43079C26.6214 5.10525 27.7488 6.8554 28.7728 10.4074C30.0035 14.7176 30.6977 20.2536 30.6977 25.9988C30.6977 31.744 30.0134 37.28 28.7728 41.5902C27.7488 45.1422 26.6214 46.8923 25.9986 47.5668C25.3758 46.8923 24.2485 45.1422 23.2245 41.5902C22.1365 37.8068 21.4768 33.0757 21.3315 28.0911H26.0085V23.9065H21.3315ZM20.1549 6.41479C18.4614 10.752 17.334 16.9428 17.1445 23.9065H12.5463C13.0386 16.3052 16.0392 9.70833 20.1549 6.41479ZM17.1445 28.0911C17.334 35.0548 18.4614 41.2455 20.1549 45.5828C16.0392 42.2892 13.0386 35.6923 12.5463 28.0911H17.1445ZM31.8398 45.5902C33.7032 40.8222 34.8823 33.8142 34.8823 25.9988C34.8823 18.1834 33.7032 11.1754 31.8398 6.4074C36.3321 9.99879 39.5075 17.5262 39.5075 25.9988C39.5075 34.4714 36.3321 41.9988 31.8398 45.5902ZM4.17708 25.9988C4.17725 22.6266 4.95987 19.3003 6.46336 16.2818C7.96685 13.2633 10.1502 10.6348 12.8417 8.6031C10.0183 13.2111 8.2977 19.3108 8.2977 25.9988C8.2977 32.6868 10.0208 38.7865 12.8417 43.3945C10.1502 41.3628 7.96685 38.7342 6.46336 35.7157C4.95987 32.6972 4.17725 29.371 4.17708 25.9988Z" fill="#DA291C"/>
    </svg>
  )
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)

  // Force light theme on login
  useEffect(() => {
    const root = document.documentElement
    const wasDark = root.classList.contains('dark')
    root.classList.remove('dark')
    return () => { if (wasDark) root.classList.add('dark') }
  }, [])

  // Animated steps
  useEffect(() => {
    const timers = [
      setTimeout(() => setStep(1), 500),
      setTimeout(() => setStep(2), 2500),
      setTimeout(() => setStep(3), 4500),
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await login(username.trim(), password)
      if (!result.success) {
        setError(result.error || 'Invalid username or password.')
        setLoading(false)
        return
      }
      if (result.user?.role === 'admin') {
        navigate('/admin', { replace: true })
      } else {
        navigate('/', { replace: true })
      }
    } catch {
      setError('Something went wrong. Please try again.')
      setLoading(false)
    }
  }

  const bubblesVisible = step >= 1

  return (
    <div className={styles.loginPage}>
      {/* Background blob */}
      <div className={styles.blobWrapper}>
        <div className={styles.blob} />
      </div>


      {/* Main content */}
      <div className={styles.contentArea}>
        {/* Floating bubbles */}
        <div className={styles.floatingIcons}>
          <div className={`${styles.iconBubble} ${styles.bubble1} ${bubblesVisible ? styles.visible : ''}`}><DashboardIcon /></div>
          <div className={`${styles.iconBubble} ${styles.bubble2} ${bubblesVisible ? styles.visible : ''}`}><PeopleIcon /></div>
          <div className={`${styles.iconBubble} ${styles.bubble3} ${bubblesVisible ? styles.visible : ''}`}><ChartIcon /></div>
          <div className={`${styles.iconBubble} ${styles.bubble4} ${bubblesVisible ? styles.visible : ''}`}><SyncIcon /></div>
        </div>

        {/* Animated text sections */}
        <div className={styles.textBlock}>
          {/* Step 1: Title */}
          <div className={`${styles.titleSection} ${step >= 1 && step < 2 ? styles.visible : ''} ${step >= 2 ? styles.fadeOut : ''}`}>
            <div className={styles.titleLogo}><CoachIQLogo size={52} /></div>
            <h1 className={styles.mainTitle}>Coach <span className={styles.titleAccent}>IQ</span></h1>
            <p className={styles.subtitle}>
              Detect coaching assignment changes from Salesforce,<br />
              keep everything in sync automatically.
            </p>
          </div>

          {/* Step 2: Tagline */}
          <div className={`${styles.taglineSection} ${step >= 2 && step < 3 ? styles.visible : ''} ${step >= 3 ? styles.fadeOut : ''}`}>
            <h2 className={styles.tagline}>
              Real-time <span className={styles.highlight}>sync</span>,{' '}
              <span className={styles.highlight}>audit trail</span> &{' '}
              <span className={styles.highlight}>AI briefs</span>{' '}
              all in one place
            </h2>
          </div>

          {/* Step 3: Login form */}
          <div className={`${styles.loginSection} ${step >= 3 ? styles.visible : ''}`}>
            <div className={styles.loginBrandRow}>
              <CoachIQLogo size={36} />
              <span className={styles.loginBrand}>Coach <span className={styles.titleAccent}>IQ</span></span>
            </div>
            <h2 className={styles.loginHeading}>Welcome Back</h2>
            <p className={styles.loginSubtext}>Sign in to access your coaching dashboard</p>

            <form className={styles.form} onSubmit={handleSubmit}>
              {error && <div className={styles.errorText}>{error}</div>}

              <div className={styles.fieldGroup}>
                <label htmlFor="username" className={styles.label}>Username</label>
                <input
                  id="username"
                  className={styles.input}
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  required
                />
              </div>

              <div className={styles.fieldGroup}>
                <label htmlFor="password" className={styles.label}>Password</label>
                <input
                  id="password"
                  className={styles.input}
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>

              <button type="submit" className={styles.submitBtn} disabled={loading || !username.trim() || !password}>
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

          </div>
        </div>
      </div>

      {/* Footer */}
      <div className={styles.footer}>
        <span>&copy; 2026 Coach IQ. All Rights Reserved.</span>
        <span className={styles.footerDot} />
        <span className={styles.footerLink}>Privacy Policy</span>
        <span className={styles.footerDot} />
        <span className={styles.footerLink}>Terms &amp; Conditions</span>
      </div>
    </div>
  )
}
