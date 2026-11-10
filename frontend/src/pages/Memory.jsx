import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { btnGhost, btnPrimary, card, EmptyState, ErrorState, inputCls, PageHeader, Skeleton } from '../components/UI.jsx'
import { useToast } from '../context/ToastContext.jsx'

const LABELS = { preferred_brand: 'Preferred brand', last_category: 'Last category', last_budget: 'Last budget' }

export default function Memory() {
  const toast = useToast()
  const [prefs, setPrefs] = useState(null)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ key: '', value: '' })
  const load = useCallback(() => api('/api/users/me/preferences').then(setPrefs).catch((e) => setError(e.message)), [])
  useEffect(() => { load() }, [load])

  const save = async (e) => {
    e.preventDefault()
    try { await api('/api/users/me/preferences', { method: 'PUT', body: { key: form.key.trim().toLowerCase().replace(/\s+/g, '_'), value: form.value.trim() } }); setForm({ key: '', value: '' }); load() }
    catch (err) { toast.error(err.message) }
  }
  const del = async (k) => { try { await api(`/api/users/me/preferences/${k}`, { method: 'DELETE' }); load() } catch (e) { toast.error(e.message) } }

  return (
    <>
      <PageHeader title="Shopping Memory" subtitle="What the assistant remembers to personalise recommendations. You can edit or delete anything." />
      {error && <ErrorState message={error} onRetry={load} />}
      {!prefs && !error && <Skeleton className="h-40" />}
      {prefs?.length === 0 && <EmptyState icon="psychology" title="Nothing remembered yet">As you chat, I save brands, categories and budgets you mention. You can also add your own below.</EmptyState>}
      {prefs?.length > 0 && <div className={`${card} divide-y divide-outline-variant/30`}>{prefs.map((p) => (
        <div key={p.key} className="flex items-center justify-between py-2"><div><div className="font-label-md text-label-md text-on-surface-variant">{LABELS[p.key] || p.key.replace(/_/g, ' ')}</div><div className="font-body-md text-body-md">{p.value}</div></div>
          <button className={btnGhost} onClick={() => del(p.key)}>Forget</button></div>))}</div>}
      <form onSubmit={save} className={`${card} mt-space-md grid grid-cols-1 md:grid-cols-[12rem_1fr_auto] gap-2`}>
        <input className={inputCls} required placeholder="Name, e.g. screen_size" value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} />
        <input className={inputCls} required placeholder="Value, e.g. 15 inch" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
        <button className={btnPrimary}>Remember</button>
      </form>
    </>
  )
}
