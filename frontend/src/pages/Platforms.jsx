import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { btnGhost, btnPrimary, card, ErrorState, Icon, PageHeader, Skeleton } from '../components/UI.jsx'
import { useToast } from '../context/ToastContext.jsx'

const ICON = { cartpilot: 'shopping_cart_checkout', amazon: 'storefront', flipkart: 'shopping_bag', myntra: 'checkroom', ajio: 'styler' }
const TYPE = { paypal_checkout: 'Built-in PayPal checkout', manual_receipts: 'Receipt upload / manual import' }

export default function Platforms() {
  const toast = useToast()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(() => api('/api/integrations').then(setData).catch((e) => setError(e.message)), [])
  useEffect(() => { load() }, [load])

  const connect = async (p) => { try { await api(`/api/integrations/${p.platform}/connect`, { method: 'POST' }); toast.success(`${p.name} import enabled`); load() } catch (e) { toast.error(e.message) } }
  const disconnect = async (p) => {
    if (!confirm(`Disable ${p.name} import? Your already-imported orders are kept.`)) return
    try { await api(`/api/integrations/${p.platform}`, { method: 'DELETE' }); toast.info(`${p.name} import disabled`); load() } catch (e) { toast.error(e.message) }
  }
  return (
    <>
      <PageHeader title="Connected Platforms" subtitle="Amazon, Flipkart, Myntra and AJIO do not share customers' order history through a public API. CartPilot never asks for your passwords and never scrapes accounts - you import receipts or orders yourself." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!data && !error && <div className="grid md:grid-cols-2 gap-gutter-sm">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-52" />)}</div>}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-gutter-sm">
        {data?.platforms.map((p) => (
          <div key={p.platform} className={`${card} page-in flex flex-col gap-2`}>
            <div className="flex items-center gap-3"><Icon name={ICON[p.platform]} className="text-primary text-3xl" />
              <div><div className="font-title-md text-title-md">{p.name}</div><div className="font-body-sm text-body-sm text-on-surface-variant">{TYPE[p.integration_type]}</div></div>
              <span className={`ml-auto px-2 py-0.5 rounded font-label-sm text-label-sm ${p.status === 'active' ? 'bg-tertiary-container text-on-tertiary-container' : 'bg-surface-container-high text-on-surface-variant'}`}>{p.status === 'active' ? 'Active' : 'Not connected'}</span></div>
            <div className="font-body-sm text-body-sm text-on-surface-variant">Last import: {p.last_synced_at ? new Date(p.last_synced_at).toLocaleString() : 'never'}{p.order_count != null && ` - ${p.order_count} orders`}</div>
            <div className="font-body-sm text-body-sm"><span className="text-on-surface-variant">Permissions: </span>{p.permissions.length ? p.permissions.join('; ') : 'none granted'}</div>
            {!p.official_api.available && <div className="font-body-sm text-body-sm text-outline">Direct account sync: unavailable. {p.official_api.reason}</div>}
            <div className="mt-auto pt-2 flex gap-2">
              {p.built_in ? <button className={btnGhost} onClick={() => navigate('/orders?platform=cartpilot')}>View orders</button> : p.status === 'active' ? <>
                <button className={btnPrimary} onClick={() => navigate(`/orders?platform=${p.platform}`)}>Import / view orders</button>
                <button className={btnGhost} onClick={() => disconnect(p)}>Disconnect</button></> : <button className={btnPrimary} onClick={() => connect(p)}>Enable import</button>}
            </div>
          </div>
        ))}
      </div>
      {data && <div className={`${card} mt-space-md`}><div className="font-title-md text-title-md mb-1">Email receipt import</div><p className="font-body-md text-body-md text-on-surface-variant">Not available: {data.email_import.reason}</p></div>}
    </>
  )
}
