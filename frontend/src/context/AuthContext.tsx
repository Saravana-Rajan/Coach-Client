import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import http from '../api'
import type { UserRole } from '../types'

interface User {
  id: number
  username: string
  email: string
  role: UserRole
  coach_sf_id: string | null
}

type LoginResult = {
  success: boolean
  error?: string
  user?: User
}

type AuthContextType = {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<LoginResult>
  logout: () => void
  isAdmin: boolean
  isCoach: boolean
  hasRole: (role: UserRole) => boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount: get CSRF token, then check if already logged in via session
  useEffect(() => {
    http
      .get('/auth/csrf/')
      .then(() => http.get('/auth/me/'))
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (username: string, password: string): Promise<LoginResult> => {
    try {
      // Ensure we have a CSRF token first
      await http.get('/auth/csrf/')
      const res = await http.post('/auth/login/', { username, password })
      const u = res.data as User
      setUser(u)
      return { success: true, user: u }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error || 'Login failed'
      return { success: false, error: msg }
    }
  }

  const logout = async () => {
    try {
      await http.post('/auth/logout/')
    } catch {
      // ignore
    }
    setUser(null)
  }

  const isAdmin = user?.role === 'admin'
  const isCoach = user?.role === 'coach'
  const hasRole = useCallback(
    (role: UserRole): boolean => user?.role === role,
    [user]
  )

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, isAdmin, isCoach, hasRole }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
