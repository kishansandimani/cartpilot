import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken } from '../api.js'
import { useAuth } from './AuthContext.jsx'

/** Shared shopping state: cart badge, the products last shown (so voice can say "add the second one"). */
const Ctx = createContext(null)
export const useShopping = () => useContext(Ctx)

export function ShoppingProvider({ children }) {
  const { user } = useAuth()
  const [cartCount, setCartCount] = useState(0)
  const [lastProducts, setLastProducts] = useState([])
  const [pendingQuery, setPendingQuery] = useState(null) // set by voice/search bar, consumed by the Assistant page

  const refreshCart = useCallback(async () => {
    if (!getToken()) return null
    try { const c = await api('/api/cart'); setCartCount(c.item_count); return c } catch { return null }
  }, [])
  useEffect(() => { if (user) refreshCart(); else setCartCount(0) }, [user, refreshCart])

  return (
    <Ctx.Provider value={{ cartCount, refreshCart, lastProducts, setLastProducts, pendingQuery, setPendingQuery }}>
      {children}
    </Ctx.Provider>
  )
}
