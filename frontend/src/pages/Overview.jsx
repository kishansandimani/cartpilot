import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, money } from '../api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import { btnPrimary, card, EmptyState, ErrorState, Icon, PageHeader, Skeleton } from '../components/UI.jsx'

export default function Overview() {
  const { user } = useAuth()
  const { cartCount } = useShopping()
  const [data, setData] = useState(null)
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api('/api/analytics/summary').then(setData).catch((e) => setError(e.message))
    api('/api/health').then(setHealth).catch(() => {})
  }, [])

  const currencies = data ? Object.keys(data.by_currency) : []
  const quick = [
    { to: '/assistant', icon: 'smart_toy', title: 'Ask the AI', text: 'Describe what you need in plain words.' },
    { to: '/discover', icon: 'travel_explore', title: 'Discover', text: 'Search products and filter by budget.' },
    { to: '/orders', icon: 'receipt_long', title: 'Order history', text: 'CartPilot + imported orders in one place.' },
  ]
  return (
    <>
      <PageHeader title={`Welcome${user?.full_name ? ', ' + user.full_name.split(' ')[0] : ''}`} subtitle="One voice. Multiple shopping platforms. One intelligent shopping assistant." />
      {error && <ErrorState message={error} />}
      {health && (!health.gemini_configured || !health.product_provider_configured || !health.paypal_configured) && (
        <div className="mb-space-md bg-secondary-container/20 border border-secondary/40 rounded-xl p-space-md font-body-md text-body-md text-on-surface">
          <b>Setup needed:</b> {[!health.gemini_configured && 'GEMINI_API_KEY', !health.product_provider_configured && 'CHANNEL3_API_KEY (or PRODUCT_PROVIDER=fixtures for dev data)', !health.paypal_configured && 'PayPal sandbox keys'].filter(Boolean).join(', ')} missing in <code>backend/.env</code>.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter-sm mb-space-lg">
        {!data ? [0, 1, 2].map((i) => <Skeleton key={i} className="h-28" />) : <>
          <div className={card}><div className="font-label-md text-label-md text-on-surface-variant">Total tracked spend</div>
            {currencies.length ? currencies.map((c) => <div key={c} className="font-headline-md text-headline-md text-primary">{money(data.by_currency[c].total, c)}</div>) : <div className="font-headline-md text-headline-md text-outline">-</div>}</div>
          <div className={card}><div className="font-label-md text-label-md text-on-surface-variant">Orders recorded</div><div className="font-headline-md text-headline-md text-on-surface">{data.total_orders}</div></div>
          <Link to="/cart" className={card}><div className="font-label-md text-label-md text-on-surface-variant">Items in cart</div><div className="font-headline-md text-headline-md text-on-surface">{cartCount}</div></Link>
        </>}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter-sm mb-space-lg">
        {quick.map((q) => (
          <Link key={q.to} to={q.to} className={`${card} hover:ring-1 hover:ring-primary/40 transition`}>
            <Icon name={q.icon} className="text-primary text-3xl" /><div className="font-title-md text-title-md mt-2">{q.title}</div><div className="font-body-sm text-body-sm text-on-surface-variant">{q.text}</div>
          </Link>
        ))}
      </div>
      <h2 className="font-headline-sm text-headline-sm mb-space-sm">Recent purchases</h2>
      {!data ? <Skeleton className="h-40" /> : data.recent.length === 0 ? (
        <EmptyState icon="receipt_long" title="No orders yet" action={<Link to="/orders" className={btnPrimary}>Import an order</Link>}>
          Buy through CartPilot, or add orders from Amazon, Flipkart, Myntra and AJIO using receipt upload or manual entry.
        </EmptyState>
      ) : (
        <div className={`${card} divide-y divide-outline-variant/30`}>
          {data.recent.map((o) => (
            <div key={o.platform + o.order_id} className="flex justify-between py-2 font-body-md text-body-md">
              <div><div className="text-on-surface line-clamp-1">{o.product_name}</div><div className="text-on-surface-variant font-body-sm capitalize">{o.platform} - {o.order_id}</div></div>
              <div className="font-mono-data text-mono-data">{money(o.amount, o.currency)}</div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
