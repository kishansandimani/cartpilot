import { useState } from 'react'
import { api, money } from '../api.js'
import { useToast } from '../context/ToastContext.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import { btnGhost, btnPrimary, Icon } from './UI.jsx'

export default function ProductCard({ product: p, selected, onToggleCompare }) {
  const toast = useToast()
  const { refreshCart } = useShopping()
  const [busy, setBusy] = useState(false)
  const rec = p.recommendation

  const add = async () => {
    setBusy(true)
    try { await api('/api/cart/items', { method: 'POST', body: { product_id: p.id, quantity: 1 } }); await refreshCart(); toast.success('Added to cart') }
    catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="page-in bg-surface-container rounded-xl overflow-hidden flex flex-col hover:ring-1 hover:ring-primary/40 transition">
      <div className="h-40 bg-surface-container-low flex items-center justify-center">
        {p.image_url ? <img src={p.image_url} alt={p.title} className="h-full w-full object-contain" loading="lazy" /> : <Icon name="image_not_supported" className="text-4xl text-outline" />}
      </div>
      <div className="p-space-md flex flex-col gap-2 flex-1">
        {p.is_fixture && <span className="self-start px-2 py-0.5 rounded bg-secondary-container text-on-secondary-container font-label-sm text-label-sm uppercase">Dev fixture - not a real product</span>}
        <h3 className="font-title-md text-title-md text-on-surface line-clamp-2">{p.title}</h3>
        <div className="flex items-baseline gap-2">
          <span className="font-headline-sm text-headline-sm text-primary">{money(p.price, p.currency)}</span>
          {p.over_budget && <span className="font-label-sm text-label-sm text-error">Over your budget</span>}
        </div>
        <div className="font-body-sm text-body-sm text-on-surface-variant flex flex-wrap gap-x-3">
          <span>Merchant: {p.merchant || 'not listed'}</span>
          <span>Stock: {p.availability || 'not listed'}</span>
          {p.rating != null && <span>Rating: {p.rating}</span>}
        </div>
        {rec && (
          <div className="bg-surface-container-low rounded-lg p-space-sm font-body-sm text-body-sm space-y-1">
            <p className="text-on-surface">{rec.why}</p>
            {rec.pros?.length > 0 && <p className="text-tertiary">+ {rec.pros.join(' - ')}</p>}
            {rec.cons?.length > 0 && <p className="text-error">- {rec.cons.join(' - ')}</p>}
          </div>
        )}
        <div className="mt-auto pt-2 flex flex-wrap gap-2">
          <button className={btnPrimary} onClick={add} disabled={busy}><Icon name="add_shopping_cart" className="text-base" />Add to cart</button>
          {onToggleCompare && (
            <button className={`${btnGhost} ${selected ? 'ring-1 ring-primary text-primary' : ''}`} onClick={() => onToggleCompare(p)}>
              <Icon name="compare_arrows" className="text-base" />{selected ? 'Selected' : 'Compare'}
            </button>
          )}
          {p.product_url && <a className={btnGhost} href={p.product_url} target="_blank" rel="noopener noreferrer"><Icon name="open_in_new" className="text-base" />View</a>}
        </div>
      </div>
    </div>
  )
}
