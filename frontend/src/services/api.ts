export type Session = { access_token: string; refresh_token: string }

const API_BASE = import.meta.env.VITE_API_URL || ''
const SESSION_KEY = 'careconnect.session'
let refreshInFlight: Promise<boolean> | undefined

export function getSession(): Session | null {
  try {
    const value = localStorage.getItem(SESSION_KEY)
    return value ? (JSON.parse(value) as Session) : null
  } catch {
    return null
  }
}

export function saveSession(session: Session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  window.dispatchEvent(new Event('careconnect:session'))
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY)
  window.dispatchEvent(new Event('careconnect:session'))
}

async function refreshSession() {
  const current = getSession()
  if (!current?.refresh_token) return false
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: current.refresh_token }),
    })
      .then(async (response) => {
        if (!response.ok) return false
        saveSession((await response.json()) as Session)
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshInFlight = undefined
      })
  }
  return refreshInFlight
}

export async function apiRequest<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const session = getSession()
  if (session?.access_token) headers.set('Authorization', `Bearer ${session.access_token}`)
  headers.set('X-Request-ID', crypto.randomUUID())

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (response.status === 401 && !retried && !path.startsWith('/api/v1/auth/')) {
    if (await refreshSession()) return apiRequest<T>(path, init, true)
    clearSession()
  }
  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const error = contentType.includes('application/json')
      ? (await response.json().catch(() => ({}))) as { detail?: string | Array<{ msg?: string; loc?: Array<string | number> }> }
      : {}
    const detail = Array.isArray(error.detail)
      ? error.detail.map((item) => item.msg ? `${item.msg}${item.loc?.length ? ` (${item.loc.slice(1).join('.')})` : ''}` : '').filter(Boolean).join('; ')
      : error.detail
    throw new Error(detail || (contentType.includes('text/html') ? 'The API returned a web page instead of JSON. Check the backend deployment and API URL.' : `Request failed (${response.status})`))
  }
  if (response.status === 204) return undefined as T
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) throw new Error('The API returned a non-JSON response. Check the backend deployment and API URL.')
  return (await response.json()) as T
}

export const apiGet = <T,>(path: string) => apiRequest<T>(path)
export const apiPost = <T,>(path: string, body: unknown) => apiRequest<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const apiPut = <T,>(path: string, body: unknown) => apiRequest<T>(path, { method: 'PUT', body: JSON.stringify(body) })
export const apiPatch = <T,>(path: string, body: unknown) => apiRequest<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
export const apiDelete = <T,>(path: string) => apiRequest<T>(path, { method: 'DELETE' })
