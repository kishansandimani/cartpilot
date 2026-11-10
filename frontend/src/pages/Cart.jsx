import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { PayPalButtons, PayPalScriptProvider } from '@paypal/react-paypal-js'
import { api, money } from '../api.js'
import { btnGhost, btnPrimary, card, EmptyState, ErrorState, Icon, PageHeader, Skeleton } from '../components/UI.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

export default function Cart() {
  const navigate = useNavigate()
  const toast = useToast()
  const [params] = useSearchParams()
  const { refreshCart } = useShopping()
  const [cart, setCart] = useState(null)
  const [cfg, setCfg] = useState(null)
  const [error, setError] = useState('')
  const [review, setReview] = useState(params.get('review') === '1') // voice "buy" lands here
  const [confirmed, setConfirmed] = useState(false)
  const [paid, setPaid] = useState(null)

  const load = useCallback(async () => {
    try { setCart(await api('/api/cart')); refreshCart() } catch (e) { setError(e.message) }
  }, [refreshCart])
  useEffect(() => { load(); api('/api/payments/config').then(setCfg).catch(() => {}) }, [load])
  useEffect(() => { if (params.get('review') === '1') setReview(true) }, [params])

  const act = async (fn) => { try { setCart(await fn()); refreshCart(); setConfirmed(false) } catch (e) { toast.error(e.message) } }
  const setQty = (i, q) => act(() => api(`/api/cart/items/${i.id}`, { method: 'PATCH', body: { quantity: q } }))
  const remove = (i) => act(() => api(`/api/cart/items/${i.id}`, { method: 'DELETE' }))
  const clear = () => act(() => api('/api/cart', { method: 'DELETE' }))

  if (paid) return (
    <div className="page-in max-w-lg mx-auto text-center bg-surface-container rounded-2xl p-space-xl">
      <Icon name="check_circle" className="text-tertiary text-6xl" />
      <h1 className="font-headline-md text-headline-md mt-2">Payment confirmed</h1>
      <p className="font-body-md text-body-md text-on-surface-variant mt-1">Order CP-{paid.order_id} - {money(paid.total, paid.currency)} paid with PayPal ({cfg?.env}).</p>
      <button className={`${btnPrimary} mt-4`} onClick={() => navigate('/orders?platform=cartpilot')}>View my orders</button>
    </div>
  )
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!cart) return <Skeleton className="h-64" />

  const payable = cart.currency && cfg?.configured && cart.currency === cfg.currency
  return (
    <>
      <PageHeader title="My Cart" subtitle="You always review and confirm before any payment.">
        {cart.items.length > 0 && <button className={btnGhost} onClick={clear}>Clear cart</button>}
      </PageHeader>
      {cart.items.length === 0 ? (
        <EmptyState icon="shopping_cart" title="Your cart is empty" action={<Link to="/discover" className={btnPrimary}>Find products</Link>}>Add products from Discover or ask the AI assistant.</EmptyState>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_22rem] gap-gutter-sm">
          <div className="space-y-3">
            {cart.items.map((i) => (
              <div key={i.id} className={`${card} page-in flex gap-4 items-center`}>
                <div className="w-20 h-20 bg-surface-container-low rounded-lg flex items-center justify-center shrink-0">{i.product.image_url ? <img src={i.product.image_url} alt="" className="max-h-full object-contain" /> : <Icon name="image_not_supported" className="text-outline" />}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-title-md text-title-md line-clamp-2">{i.product.title}</div>
                  <div className="font-body-sm text-body-sm text-on-surface-variant">{i.product.merchant || 'merchant not listed'}{i.product.is_fixture && ' - DEV FIXTURE'}</div>
                  <div className="font-mono-data text-mono-data text-primary">{money(i.product.price, i.product.currency)}</div>
                </div>
                <div className="flex items-center gap-1">
                  <button className={btnGhost} aria-label="Decrease quantity" disabled={i.quantity <= 1} onClick={() => setQty(i, i.quantity - 1)}>-</button>
                  <span className="w-8 text-center font-mono-data text-mono-data">{i.quantity}</span>
                  <button className={btnGhost} aria-label="Increase quantity" disabled={i.quantity >= 20} onClick={() => setQty(i, i.quantity + 1)}>+</button>
                </div>
                <button className="text-error" aria-label="Remove item" onClick={() => remove(i)}><Icon name="delete" /></button>
              </div>
            ))}
          </div>
          <div className={`${card} h-fit space-y-3`}>
            <h2 className="font-headline-sm text-headline-sm">Order summary</h2>
            {Object.entries(cart.totals).map(([c, t]) => <div key={c} className="flex justify-between font-body-md text-body-md"><span>{cart.item_count} items</span><span className="font-mono-data text-mono-data text-on-surface">{money(t, c)}</span></div>)}
            {cart.mixed_currencies && <p className="text-error font-body-sm text-body-sm">Your cart mixes currencies. CartPilot does not guess exchange rates, so remove items until one currency remains.</p>}
            {cfg && cart.currency && cart.currency !== cfg.currency && <p className="text-error font-body-sm text-body-sm">Checkout runs in {cfg.currency}, but this cart is priced in {cart.currency}, so it cannot be paid here.</p>}
            {cfg && !cfg.configured && <p className="text-error font-body-sm text-body-sm">PayPal is not configured on the server (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET).</p>}
            {!review ? (
              <button className={`${btnPrimary} w-full`} disabled={!payable} onClick={() => setReview(true)}>Review & buy</button>
            ) : (
              <div className="page-in space-y-3">
                <div className="bg-surface-container-low rounded-lg p-space-sm font-body-sm text-body-sm">
                  You are about to pay <b>{cart.currency && money(cart.total, cart.currency)}</b> for {cart.item_count} item(s) using PayPal{cfg?.env === 'sandbox' && ' (Sandbox - no real money)'}. Prices are re-checked with the store when you continue.
                </div>
                <label className="flex items-start gap-2 font-body-md text-body-md cursor-pointer">
                  <input type="checkbox" className="mt-1" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
                  I confirm this order and want to pay.
                </label>
                {confirmed && payable ? (
                  <PayPalScriptProvider options={{ clientId: cfg.client_id, currency: cfg.currency, intent: 'capture' }}>
                    <PayPalButtons style={{ layout: 'vertical', shape: 'rect' }}
                      createOrder={async () => (await api('/api/payments/create-order', { method: 'POST', body: { confirmed: true } })).paypal_order_id}
                      onApprove={async (data) => {
                        try { setPaid(await api('/api/payments/capture', { method: 'POST', body: { paypal_order_id: data.orderID } })); refreshCart() }
                        catch (e) { toast.error(e.message) }
                      }}
                      onCancel={() => toast.info('Payment cancelled. Nothing was charged.')}
                      onError={(e) => toast.error(e?.message || 'PayPal reported an error. Nothing was charged.')} />
                  </PayPalScriptProvider>
                ) : <p className="font-body-sm text-body-sm text-outline">Tick the box to show the PayPal button.</p>}
                <button className={`${btnGhost} w-full`} onClick={() => { setReview(false); setConfirmed(false) }}>Back</button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
