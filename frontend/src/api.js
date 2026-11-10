// One small helper that talks to the FastAPI backend. All pages use it.
const TOKEN_KEY = 'cartpilot_token'
// In development the Vite proxy handles /api. In production set VITE_API_URL to the backend URL.
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

export async function api(path, { method = 'GET', body, params, form } = {}) {
  const url = new URL(API_BASE + path, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && v !== null && v !== '' && url.searchParams.set(k, v))
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }

  let res
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 90000)
  try {
    res = await fetch(url, { method, headers, body: payload, signal: ctrl.signal })
  } catch (e) {
    throw new ApiError(e.name === 'AbortError'
      ? 'The server took more than 90 seconds to answer. It may be waking up - try again in a minute.'
      : 'Cannot reach the CartPilot server. Is the backend running?', 0)
  } finally {
    clearTimeout(timer)
  }

  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) { setToken(null); window.dispatchEvent(new Event('cartpilot-logout')) }
    const detail = data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join('; ') : `Request failed (${res.status})`
    throw new ApiError(msg, res.status)
  }
  return data
}

export const money = (amount, currency) => {
  if (amount === null || amount === undefined) return 'not listed'
  const n = Number(amount)
  try { return new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(n) }
  catch { return `${currency} ${n.toFixed(2)}` }
}