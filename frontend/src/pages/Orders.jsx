import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, money } from '../api.js'
import { btnGhost, btnPrimary, card, EmptyState, ErrorState, Icon, inputCls, PageHeader, Skeleton } from '../components/UI.jsx'
import { useToast } from '../context/ToastContext.jsx'

const FILTERS = [['all', 'All platforms'], ['amazon', 'Amazon'], ['flipkart', 'Flipkart'], ['myntra', 'Myntra'], ['ajio', 'AJIO'], ['cartpilot', 'CartPilot purchases']]
const SOURCE = { paypal_checkout: 'CartPilot - PayPal', manual: 'Manually imported', receipt_upload: 'Receipt import', email: 'Email import' }
const empty = { platform: 'amazon', external_order_id: '', order_date: '', total: '', currency: 'INR', product_name: '', category: '', status: '', payment_method: '', tracking_info: '', receipt_import_id: null }

export default function Orders() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const platform = params.get('platform') || 'all'
  const [q, setQ] = useState('')
  const [range, setRange] = useState({ from: '', to: '' })
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [form, setForm] = useState(null) // null = closed
  const [paste, setPaste] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try { setRows(await api('/api/orders/unified', { params: { platform, q, date_from: range.from && `${range.from}T00:00:00`, date_to: range.to && `${range.to}T23:59:59` } })) }
    catch (e) { setError(e.message) }
  }, [platform, q, range])
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t) }, [load])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const applyParsed = (r) => {
    const p = r.parsed
    setForm((f) => ({ ...f, platform: p.platform || f.platform, external_order_id: p.external_order_id || '', order_date: p.order_date || '', total: p.total ?? '', currency: p.currency || f.currency,
      product_name: p.product_name || '', tracking_info: p.tracking_info || '', receipt_import_id: r.receipt_import_id }))
    toast.info(`Receipt read (${p.confidence} confidence). Please check every field before saving.`)
  }
  const upload = async (file) => {
    if (!file) return
    const fd = new FormData(); fd.append('file', file)
    setBusy(true)
    try { applyParsed(await api('/api/external-orders/receipts/parse', { method: 'POST', form: fd })) } catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  const parsePaste = async () => {
    setBusy(true)
    try { applyParsed(await api('/api/external-orders/receipts/parse-text', { method: 'POST', body: { text: paste } })); setPaste('') } catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  const save = async (e) => {
    e.preventDefault(); setBusy(true)
    const body = { ...form, total: String(form.total) }
    Object.keys(body).forEach((k) => (body[k] === '' || body[k] === null) && delete body[k])
    try { await api('/api/external-orders', { method: 'POST', body }); toast.success('Order imported'); setForm(null); load() }
    catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }
  const del = async (o) => { if (!confirm('Delete this imported order?')) return; try { await api(`/api/external-orders/${o.id}`, { method: 'DELETE' }); load() } catch (e) { toast.error(e.message) } }

  const totals = {}
  rows?.forEach((o) => { if (!['cancelled', 'returned', 'refunded', 'failed'].includes((o.status || '').toLowerCase())) totals[o.currency] = (totals[o.currency] || 0) + Number(o.amount) })

  return (
    <>
      <PageHeader title="Unified Order History" subtitle="CartPilot purchases and orders you imported from other stores - clearly labelled.">
        <button className={btnPrimary} onClick={() => setForm({ ...empty, platform: platform !== 'all' && platform !== 'cartpilot' ? platform : 'amazon' })}><Icon name="add" className="text-base" />Import an order</button>
      </PageHeader>
      <div className="flex flex-wrap gap-2 mb-3">
        {FILTERS.map(([k, l]) => <button key={k} onClick={() => setParams(k === 'all' ? {} : { platform: k })} className={`px-3 py-1.5 rounded-full font-label-md text-label-md transition ${platform === k ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface'}`}>{l}</button>)}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-space-md">
        <input className={`${inputCls} md:col-span-2`} placeholder="Search by product, platform or order ID" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search orders" />
        <input className={inputCls} type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} aria-label="From date" />
        <input className={inputCls} type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} aria-label="To date" />
      </div>
      {rows && rows.length > 0 && <div className="mb-3 font-body-md text-body-md text-on-surface-variant">{rows.length} orders - spend: {Object.entries(totals).map(([c, t]) => money(t, c)).join(' + ') || '-'}</div>}
      {error && <ErrorState message={error} onRetry={load} />}
      {!rows && !error && <div className="space-y-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-24" />)}</div>}
      {rows?.length === 0 && <EmptyState icon="receipt_long" title="No orders found" action={<button className={btnPrimary} onClick={() => setForm({ ...empty })}>Import an order</button>}>Nothing matches these filters. Orders from other stores appear here after you import them.</EmptyState>}
      <div className="space-y-3">
        {rows?.map((o) => (
          <div key={o.source + o.id} className={`${card} page-in flex flex-wrap gap-4 items-center`}>
            <div className="w-16 h-16 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">{o.image_url ? <img src={o.image_url} alt="" className="max-h-full object-contain" /> : <Icon name="inventory_2" className="text-outline" />}</div>
            <div className="flex-1 min-w-[12rem]">
              <div className="font-title-md text-title-md line-clamp-1">{o.product_name}</div>
              <div className="font-body-sm text-body-sm text-on-surface-variant"><span className="capitalize">{o.platform}</span> - {o.order_id} - {new Date(o.order_date).toLocaleDateString()}</div>
              <div className="font-body-sm text-body-sm text-on-surface-variant">Payment: {o.payment_method || 'not recorded'} - Status: {o.status || 'not recorded'} - Tracking: {o.tracking_info || 'none verified'}</div>
              <span className="inline-block mt-1 px-2 py-0.5 rounded bg-surface-container-high font-label-sm text-label-sm text-secondary">{SOURCE[o.import_source] || o.import_source}</span>
            </div>
            <div className="text-right"><div className="font-headline-sm text-headline-sm text-primary">{money(o.amount, o.currency)}</div>
              {o.source === 'external' && <button className="text-error font-label-sm text-label-sm" onClick={() => del(o)}>Delete</button>}</div>
          </div>
        ))}
      </div>

      {form && (
        <div className="fixed inset-0 z-[80] bg-black/60 flex items-center justify-center p-4" onClick={() => setForm(null)}>
          <form onSubmit={save} onClick={(e) => e.stopPropagation()} className="page-in w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-surface-container rounded-2xl p-space-lg space-y-3">
            <div className="flex justify-between items-center"><h2 className="font-headline-sm text-headline-sm">Import an external order</h2><button type="button" onClick={() => setForm(null)} aria-label="Close"><Icon name="close" /></button></div>
            <p className="font-body-sm text-body-sm text-on-surface-variant">You choose what to import - CartPilot never logs in to your shopping accounts. Upload a receipt (.txt, .eml, .html, .pdf), paste receipt text, or type the details.</p>
            <div className="flex flex-wrap gap-2 items-start">
              <label className={`${btnGhost} cursor-pointer`}><Icon name="upload_file" className="text-base" />Upload receipt<input type="file" accept=".txt,.eml,.html,.htm,.pdf" className="hidden" onChange={(e) => upload(e.target.files[0])} /></label>
            </div>
            <div className="flex gap-2"><textarea className={inputCls} rows={2} placeholder="...or paste receipt text here" value={paste} onChange={(e) => setPaste(e.target.value)} /><button type="button" className={btnGhost} disabled={busy || paste.trim().length < 10} onClick={parsePaste}>Read</button></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <select className={inputCls} value={form.platform} onChange={set('platform')} aria-label="Platform">{['amazon', 'flipkart', 'myntra', 'ajio', 'other'].map((p) => <option key={p} value={p}>{p}</option>)}</select>
              <input className={inputCls} required placeholder="Order ID *" value={form.external_order_id} onChange={set('external_order_id')} />
              <input className={inputCls} required type="date" value={form.order_date} onChange={set('order_date')} aria-label="Order date" />
              <div className="flex gap-2"><input className={inputCls} required type="number" step="0.01" min="0.01" placeholder="Total *" value={form.total} onChange={set('total')} /><input className={`${inputCls} !w-24`} maxLength={3} value={form.currency} onChange={set('currency')} aria-label="Currency" /></div>
              <input className={`${inputCls} sm:col-span-2`} required placeholder="Product name *" value={form.product_name} onChange={set('product_name')} />
              <input className={inputCls} placeholder="Category (optional)" value={form.category} onChange={set('category')} />
              <input className={inputCls} placeholder="Status, e.g. Delivered (optional)" value={form.status} onChange={set('status')} />
              <input className={inputCls} placeholder="Payment method (optional)" value={form.payment_method} onChange={set('payment_method')} />
              <input className={inputCls} placeholder="Tracking ID (optional)" value={form.tracking_info} onChange={set('tracking_info')} />
            </div>
            <div className="flex justify-end gap-2"><button type="button" className={btnGhost} onClick={() => setForm(null)}>Cancel</button><button className={btnPrimary} disabled={busy}>Save order</button></div>
          </form>
        </div>
      )}
    </>
  )
}
