import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from '../api.js'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api('/api/users/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false))
  }, [])
  useEffect(() => {
    const onLogout = () => setUser(null)
    window.addEventListener('cartpilot-logout', onLogout)
    return () => window.removeEventListener('cartpilot-logout', onLogout)
  }, [])

  const authenticate = useCallback(async (path, body) => {
    const data = await api(path, { method: 'POST', body })
    setToken(data.access_token)
    setUser(data.user)
  }, [])
  const login = (email, password) => authenticate('/api/auth/login', { email, password })
  const register = (email, password, full_name) => authenticate('/api/auth/register', { email, password, full_name })
  const logout = () => { setToken(null); setUser(null) }

  return <AuthCtx.Provider value={{ user, setUser, loading, login, register, logout }}>{children}</AuthCtx.Provider>
}
