import axios from 'axios'
import type {
  AuthUser,
  Coach,
  Client,
  Account,
  AuditRecord,
  SyncRun,
} from './types'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true, // send session cookie for CSRF
})

// -- CSRF: read Django's csrftoken cookie and attach it as X-CSRFToken --
function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : null
}

http.interceptors.request.use(config => {
  // Attach CSRF token for state-changing methods
  if (['post', 'put', 'patch', 'delete'].includes(config.method ?? '')) {
    const csrf = getCsrfToken()
    if (csrf) {
      config.headers['X-CSRFToken'] = csrf
    }
  }
  // Attach auth token
  const token = localStorage.getItem('cc_auth_token')
  if (token) {
    config.headers['Authorization'] = `Token ${token}`
  }
  return config
})

// -- Handle 401/403 responses globally --
http.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('cc_auth_token')
      localStorage.removeItem('cc_user_data')
      window.location.href = '/login'
    } else if (error.response?.status === 403) {
      window.dispatchEvent(new CustomEvent('cc:permission-denied'))
    }
    return Promise.reject(error)
  }
)

// -- Generic CRUD helper --
function crud<T>(resource: string) {
  return {
    list: (params?: Record<string, string>) =>
      http.get<{ results: T[]; count: number }>(`/${resource}/`, { params }).then(r => r.data),
    get: (id: number | string) =>
      http.get<T>(`/${resource}/${id}/`).then(r => r.data),
    create: (data: Partial<T>) =>
      http.post<T>(`/${resource}/`, data).then(r => r.data),
    update: (id: number | string, data: Partial<T>) =>
      http.patch<T>(`/${resource}/${id}/`, data).then(r => r.data),
    delete: (id: number | string) =>
      http.delete(`/${resource}/${id}/`),
  }
}

// -- Auth API --
export const authApi = {
  login: (credentials: { email: string; password: string }) =>
    http.post<{ token: string; user: AuthUser }>('/auth/login/', credentials).then(r => r.data),
  logout: () =>
    http.post('/auth/logout/'),
  me: () =>
    http.get<AuthUser>('/auth/me/').then(r => r.data),
}

// -- Resource APIs --
export const coachesApi = crud<Coach>('coaches')
export const accountsApi = crud<Account>('accounts')
export const clientsApi = crud<Client>('clients')

export const auditApi = {
  ...crud<AuditRecord>('audit'),
  listBySyncRun: (syncRunId: number) =>
    http.get<{ results: AuditRecord[]; count: number }>(`/audit/`, {
      params: { sync_run: syncRunId },
    }).then(r => r.data),
}

export const syncApi = {
  list: () =>
    http.get<{ results: SyncRun[]; count: number }>('/sync-runs/').then(r => r.data),
  trigger: () =>
    http.post<SyncRun>('/sync-runs/trigger/').then(r => r.data),
  get: (id: number) =>
    http.get<SyncRun>(`/sync-runs/${id}/`).then(r => r.data),
}

export default http
