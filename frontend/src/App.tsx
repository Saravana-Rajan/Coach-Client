import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LoadingSpinner from './components/LoadingSpinner'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import CrmLayout from './components/CrmLayout'

// Lazy-loaded page components for code splitting
const LoginPage = lazy(() => import('./pages/LoginPage'))
const CoachDashboard = lazy(() => import('./pages/CoachDashboard'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const AuditTrailPage = lazy(() => import('./pages/AuditTrailPage'))
const BriefsPage = lazy(() => import('./pages/TransitionBriefsPage'))
const SourceEditorPage = lazy(() => import('./pages/SourceEditorPage'))
const AdminManagementPage = lazy(() => import('./pages/AdminManagementPage'))
const SchemaChangesPage = lazy(() => import('./pages/SchemaChangesPage'))

// Prefetch common pages after initial load
if (typeof window !== 'undefined') {
  window.addEventListener(
    'load',
    () => {
      setTimeout(() => {
        import('./pages/CoachDashboard')
        import('./pages/TransitionBriefsPage')
      }, 1000)
    },
    { once: true }
  )
}

export default function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes — any authenticated user */}
        <Route element={<ProtectedRoute />}>
          <Route element={<CrmLayout />}>
            <Route path="/" element={<CoachDashboard />} />
            <Route path="/briefs" element={<BriefsPage />} />
          </Route>
        </Route>

        {/* Admin-only routes */}
        <Route element={<AdminRoute />}>
          <Route element={<CrmLayout />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/audit" element={<AuditTrailPage />} />
            <Route path="/source" element={<SourceEditorPage />} />
            <Route path="/manage" element={<AdminManagementPage />} />
            <Route path="/schema" element={<SchemaChangesPage />} />
          </Route>
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
