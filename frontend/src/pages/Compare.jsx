import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, money } from '../api.js'
import { btnPrimary, EmptyState, ErrorState, PageHeader, Skeleton } from '../components/UI.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

export default function Compare() {
  const [params] = useSearchParams()
  const { lastProducts, refreshCart } = useShopping()
  const toast = useToast()
  const ids = (params.get('ids') || lastProducts.slice(0, 3).map((p) => p.id).join(',')).split(',').filter(Boolean).map(Number)
  const key = ids.join(',')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setData(null); setError('')
    if (ids.length < 2) return
    setLoading(true)
    api('/api/compare', { method: 'POST', body: { product_ids: ids } }).then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }, [key]) // eslint-disable-line

  const add = async (id) => { try { await api('/api/cart/items', { method: 'POST', body: { product_id: id, quantity: 1 } }); refreshCart(); toast.success('Added to cart') } catch (e) { toast.error(e.message) } }

  return (
    <>
      <PageHeader title="Compare Products" subtitle="Side-by-side facts from the store API. Anything the store did not provide is shown as 'not listed'." />
      {ids.length < 2 && <EmptyState icon="compare_arrows" title="Pick at least two products" action={<Link to="/discover" className={btnPrimary}>Find products</Link>}>Select products with the Compare button in Discover or the AI Assistant, or say "compare these two".</EmptyState>}
      {error && <ErrorState message={error} />}
      {loading && <Skeleton className="h-96" />}
      {data && (
        <div className="overflow-x-auto bg-surface-container rounded-xl page-in">
          <table className="w-full text-left">
            <thead><tr><th className="p-space-md w-40" />
              {data.products.map((p) => (
                <th key={p.id} className="p-space-md align-top min-w-[14rem]">
                  <div className="h-24 flex items-center justify-center mb-2">{p.image_url && <img src={p.image_url} alt="" className="max-h-full object-contain" />}</div>
                  <div className="font-title-md text-title-md text-on-surface line-clamp-2">{p.title}</div>
                  {data.cheapest_id === p.id && <span className="inline-block mt-1 px-2 py-0.5 rounded bg-tertiary-container text-on-tertiary-container font-label-sm text-label-sm">Lowest price</span>}
                  <div className="mt-2"><button className={btnPrimary} onClick={() => add(p.id)}>Add to cart</button></div>
                </th>))}
            </tr></thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.label} className="border-t border-outline-variant/30">
                  <td className="p-space-md font-label-md text-label-md text-on-surface-variant">{r.label}</td>
                  {r.values.map((v, i) => <td key={i} className={`p-space-md font-body-md text-body-md ${v == null ? 'text-outline' : 'text-on-surface'}`}>{v == null ? 'not listed' : String(v)}</td>)}
                </tr>))}
            </tbody>
          </table>
          {!data.comparable_prices && <p className="p-space-md font-body-sm text-body-sm text-secondary">These products are priced in different currencies, so no price ranking is shown.</p>}
        </div>
      )}
    </>
  )
}
