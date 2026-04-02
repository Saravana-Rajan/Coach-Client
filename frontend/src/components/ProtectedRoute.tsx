import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { UserRole } from '../types'

type Props = {
  /** If set, only users with this role can access the route */
  requiredRole?: UserRole
}

export default function ProtectedRoute({ requiredRole }: Props) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          color: 'var(--pm-text-muted)',
        }}
      >
        Loading...
      </div>
    )
  }

  // Not logged in -> redirect to login
  if (!user) {
    return <Navigate to="/login" replace />
  }

  // Logged in but wrong role -> redirect to dashboard (or a 403 page)
  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
