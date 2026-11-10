import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import ProductCard from '../components/ProductCard.jsx'
import { btnGhost, btnPrimary, EmptyState, ErrorState, Icon, inputCls, PageHeader, SkeletonGrid } from '../components/UI.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

const CATEGORIES = ['', 'Laptops', 'Phones', 'Headphones', 'Shoes', 'Watches', 'Home']

export default function Discover() {
  const navigate = useNavigate()
  const toast = useToast()
  const { setLastProducts } = useShopping()
  const [f, setF] = useState({ q: '', max_price: '', min_price: '', brand: '', category: '' })
  const [res, setRes] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [picked, setPicked] = useState([])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const search = async (e) => {
    e?.preventDefault()
    if (f.q.trim().length < 2) return toast.info('Type at least 2 characters to search')
    setLoading(true); setError(''); setPicked([])
    try { const r = await api('/api/products/search', { params: f }); setRes(r); setLastProducts(r.products) }
    catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  const toggle = (p) => setPicked((s) => (s.find((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : s.length < 4 ? [...s, p] : s))

  return (
    <>
      <PageHeader title="Discover Products" subtitle="Search real products and filter by budget, brand and category." />
      <form onSubmit={search} className="grid grid-cols-2 md:grid-cols-6 gap-2 mb-space-md">
        <input className={`${inputCls} col-span-2 md:col-span-2`} placeholder="What are you looking for?" value={f.q} onChange={set('q')} aria-label="Search" />
        <input className={inputCls} type="number" min="0" placeholder="Min price" value={f.min_price} onChange={set('min_price')} aria-label="Minimum price" />
        <input className={inputCls} type="number" min="0" placeholder="Max price" value={f.max_price} onChange={set('max_price')} aria-label="Maximum price" />
        <input className={inputCls} placeholder="Brand" value={f.brand} onChange={set('brand')} aria-label="Brand" />
        <select className={inputCls} value={f.category} onChange={set('category')} aria-label="Category">{CATEGORIES.map((c) => <option key={c} value={c}>{c || 'Any category'}</option>)}</select>
        <button className={`${btnPrimary} col-span-2 md:col-span-6 md:w-fit`}><Icon name="search" className="text-base" />Search</button>
      </form>
      {error && <ErrorState message={error} onRetry={search} />}
      {loading && <SkeletonGrid />}
      {!loading && res?.is_fixture_data && <div className="mb-3 bg-secondary-container/20 rounded-lg px-4 py-2 font-body-sm text-body-sm">Development mode: these are labelled fixture products, not real listings.</div>}
      {!loading && res && res.products.length === 0 && <EmptyState icon="search_off" title="No products found">Try a broader search or remove some filters.</EmptyState>}
      {!loading && !res && !error && <EmptyState icon="travel_explore" title="Search to get started">Prices are in the currency returned by the store API.</EmptyState>}
      {!loading && res?.products.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-gutter-sm">
          {res.products.map((p) => <ProductCard key={p.id} product={p} selected={!!picked.find((x) => x.id === p.id)} onToggleCompare={toggle} />)}
        </div>
      )}
      {picked.length >= 2 && (
        <div className="page-in sticky bottom-24 mt-4 flex items-center justify-between bg-surface-container-high rounded-xl px-space-md py-space-sm shadow-xl">
          <span className="font-body-md text-body-md">{picked.length} selected</span>
          <div className="flex gap-2"><button className={btnGhost} onClick={() => setPicked([])}>Clear</button>
            <button className={btnPrimary} onClick={() => navigate('/compare?ids=' + picked.map((p) => p.id).join(','))}>Compare</button></div>
        </div>
      )}
    </>
  )
}
