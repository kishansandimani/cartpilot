import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, money } from '../api.js'
import { Bars, btnPrimary, card, EmptyState, ErrorState, Icon, PageHeader, Skeleton } from '../components/UI.jsx'
import { useToast } from '../context/ToastContext.jsx'

export default function Insights() {
  const toast = useToast()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [cur, setCur] = useState(null)
  const [ai, setAi] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/api/analytics/summary').then((d) => { setData(d); setCur(Object.keys(d.by_currency)[0] || null) }).catch((e) => setError(e.message)) }, [])

  const generate = async () => {
    setBusy(true)
    try { const r = await api('/api/analytics/insights', { method: 'POST' }); setAi(r.insights); if (!r.insights.length && r.message) toast.info(r.message) }
    catch (e) { toast.error(e.message) } finally { setBusy(false) }
  }
  if (error) return <ErrorState message={error} />
  if (!data) return <Skeleton className="h-64" />
  const currencies = Object.keys(data.by_currency)
  if (!currencies.length) return <><PageHeader title="AI Insights" /><EmptyState icon="auto_graph" title="No spending data yet" action={<Link to="/orders" className={btnPrimary}>Import orders</Link>}>Insights are calculated from your CartPilot purchases and imported orders.</EmptyState></>
  const d = data.by_currency[cur]
  const fmt = (v) => money(v, cur)

  return (
    <>
      <PageHeader title="AI Insights" subtitle="Spending analysis from your real orders. Each currency is kept separate - no exchange rates are guessed.">
        {currencies.length > 1 && <select className="bg-surface-container-high rounded-lg px-3 py-2" value={cur} onChange={(e) => setCur(e.target.value)} aria-label="Currency">{currencies.map((c) => <option key={c}>{c}</option>)}</select>}
        <button className={btnPrimary} onClick={generate} disabled={busy}><Icon name="auto_awesome" className="text-base" />{busy ? 'Thinking...' : 'Generate AI insights'}</button>
      </PageHeader>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter-sm mb-space-md">
        <div className={card}><div className="font-label-md text-on-surface-variant">Total spend</div><div className="font-headline-md text-headline-md text-primary">{fmt(d.total)}</div></div>
        <div className={card}><div className="font-label-md text-on-surface-variant">This month</div><div className="font-headline-md text-headline-md">{fmt(d.this_month)}</div></div>
        <div className={card}><div className="font-label-md text-on-surface-variant">Orders counted</div><div className="font-headline-md text-headline-md">{d.order_count}</div></div>
      </div>
      {ai?.length > 0 && <div className={`${card} mb-space-md page-in`}><h2 className="font-headline-sm text-headline-sm mb-2">AI observations</h2><ul className="list-disc pl-5 space-y-1 font-body-md text-body-md">{ai.map((t, i) => <li key={i}>{t}</li>)}</ul></div>}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-gutter-sm">
        <div className={card}><h2 className="font-title-md text-title-md mb-3">Monthly spending</h2><Bars rows={d.monthly} labelKey="month" valueKey="amount" format={fmt} /></div>
        <div className={card}><h2 className="font-title-md text-title-md mb-3">By platform</h2><Bars rows={d.by_platform} labelKey="platform" valueKey="amount" format={fmt} /></div>
        <div className={card}><h2 className="font-title-md text-title-md mb-3">By category</h2><Bars rows={d.by_category} labelKey="category" valueKey="amount" format={fmt} /></div>
      </div>
    </>
  )
}
