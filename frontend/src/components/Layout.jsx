import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import VoiceAssistant from './VoiceAssistant.jsx'
import { Icon } from './UI.jsx'

const NAV = [
  { to: '/', label: 'Overview', icon: 'dashboard', end: true },
  { to: '/assistant', label: 'AI Shopping Assistant', icon: 'smart_toy' },
  { to: '/discover', label: 'Discover Products', icon: 'travel_explore' },
  { to: '/compare', label: 'Compare Products', icon: 'compare_arrows' },
  { to: '/cart', label: 'My Cart', icon: 'shopping_cart', badge: 'cart' },
  { to: '/platforms', label: 'Connected Platforms', icon: 'hub' },
  { to: '/orders', label: 'Unified Order History', icon: 'receipt_long' },
  { to: '/memory', label: 'Shopping Memory', icon: 'psychology' },
  { to: '/insights', label: 'AI Insights', icon: 'auto_graph' },
  { to: '/settings', label: 'Settings & Security', icon: 'shield_person' },
]

function SystemStatus() {
  const [h, setH] = useState(null)
  useEffect(() => { api('/api/health').then(setH).catch(() => setH(false)) }, [])
  const row = (label, ok) => (
    <div className="flex items-center justify-between py-0.5">
      <span className="font-body-sm text-body-sm text-outline">{label}</span>
      <span className={`font-label-sm text-label-sm ${ok ? 'text-tertiary' : 'text-error'}`}>{ok ? 'Ready' : 'Not set up'}</span>
    </div>
  )
  return (
    <div className="p-space-md m-space-sm rounded-xl bg-surface-container-low">
      <div className="font-label-sm text-label-sm text-on-surface mb-1">System status</div>
      {h === null && <div className="font-body-sm text-body-sm text-outline">Checking...</div>}
      {h === false && <div className="font-body-sm text-body-sm text-error">Backend unreachable</div>}
      {h && <>{row('Gemini AI', h.gemini_configured)}{row(`Products (${h.product_provider})`, h.product_provider_configured)}{row(`PayPal ${h.paypal_env}`, h.paypal_configured)}</>}
    </div>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const { cartCount, setPendingQuery } = useShopping()
  const navigate = useNavigate()
  const location = useLocation()
  const [q, setQ] = useState('')
  const [menu, setMenu] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  useEffect(() => setNavOpen(false), [location.pathname])

  const submit = (e) => { e.preventDefault(); const t = q.trim(); if (!t) return; setPendingQuery(t); setQ(''); navigate('/assistant') }

  return (
    <div className="min-h-screen bg-background">
      <aside className={`fixed left-0 top-0 h-full w-72 bg-surface-container-lowest z-50 flex flex-col justify-between shadow-[0_1px_8px_rgba(0,0,0,0.5)] transition-transform lg:translate-x-0 ${navOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col overflow-y-auto">
          <div className="h-16 px-space-lg flex items-center gap-space-sm bg-surface-container-low/50">
            <Icon name="shopping_cart_checkout" className="text-primary text-3xl" />
            <span className="font-title-md text-title-md text-on-surface tracking-tight font-bold">CartPilot AI</span>
          </div>
          <nav className="flex flex-col gap-1 px-space-sm py-space-md">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}
                className={({ isActive }) => `group flex items-center justify-between px-space-md py-space-sm rounded-lg transition-all ${isActive ? 'bg-surface-container-high text-primary font-title-md' : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'}`}>
                <div className="flex items-center gap-space-sm">
                  <Icon name={n.icon} className="text-lg" /><span className="font-body-md text-body-md">{n.label}</span>
                </div>
                {n.badge === 'cart' && cartCount > 0 && <span className="px-1.5 py-0.5 rounded-full bg-primary-container text-on-primary-container font-mono-data text-mono-data">{cartCount}</span>}
              </NavLink>
            ))}
          </nav>
        </div>
        <SystemStatus />
      </aside>
      {navOpen && <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setNavOpen(false)} />}

      <div className="lg:pl-72">
        <header className="fixed top-0 left-0 lg:left-72 right-0 h-16 bg-surface-container-lowest/80 backdrop-blur-xl z-30 px-space-md lg:px-space-lg flex items-center justify-between gap-3 shadow-[0_1px_8px_rgba(0,0,0,0.3)]">
          <button className="lg:hidden text-on-surface" onClick={() => setNavOpen(true)} aria-label="Open menu"><Icon name="menu" /></button>
          <form onSubmit={submit} className="relative flex-1 max-w-xl flex items-center bg-surface-container-high rounded-lg px-space-md py-1.5 focus-within:ring-1 focus-within:ring-primary">
            <Icon name="search" className="text-outline mr-2 text-lg" />
            <input value={q} onChange={(e) => setQ(e.target.value)} className="w-full bg-transparent font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none" placeholder="Ask the shopping assistant... e.g. laptop under 60000 for coding" aria-label="Ask the shopping assistant" />
            <button type="button" onClick={() => window.dispatchEvent(new Event('cartpilot-open-voice'))} aria-label="Open voice assistant" className="ml-2 text-primary"><Icon name="mic" className="text-xl" /></button>
          </form>
          <div className="relative">
            <button onClick={() => setMenu((m) => !m)} className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-surface-container-high" aria-haspopup="menu" aria-expanded={menu}>
              <div className="w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-label-md text-label-md">{(user?.full_name || user?.email || '?')[0].toUpperCase()}</div>
              <span className="hidden sm:block font-label-md text-label-md text-on-surface">{user?.full_name || user?.email}</span>
            </button>
            {menu && (
              <div className="page-in absolute right-0 mt-2 w-48 bg-surface-container-high rounded-lg shadow-xl py-1" role="menu">
                <button className="w-full text-left px-4 py-2 hover:bg-surface-container-highest font-body-md text-body-md" onClick={() => { setMenu(false); navigate('/settings') }}>Profile & settings</button>
                <button className="w-full text-left px-4 py-2 hover:bg-surface-container-highest font-body-md text-body-md text-error" onClick={logout}>Log out</button>
              </div>
            )}
          </div>
        </header>
        <main className="w-full pt-16 px-space-md lg:px-gutter bg-background min-h-screen">
          <div key={location.pathname} className="page-in pt-space-lg pb-28"><Outlet /></div>
        </main>
      </div>
      <VoiceAssistant />
    </div>
  )
}
