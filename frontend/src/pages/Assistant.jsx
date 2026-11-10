import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import ProductCard from '../components/ProductCard.jsx'
import { btnGhost, btnPrimary, Icon, inputCls, PageHeader } from '../components/UI.jsx'
import { useShopping } from '../context/ShoppingContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

const SUGGESTIONS = ['I need a laptop under 60000 rupees for programming', 'Find wireless headphones under 2000 rupees', 'A phone under 25000 with a good camera and battery']

export default function Assistant() {
  const navigate = useNavigate()
  const toast = useToast()
  const { setLastProducts, pendingQuery, setPendingQuery } = useShopping()
  const [messages, setMessages] = useState([])
  const [convId, setConvId] = useState(null)
  const [convs, setConvs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [picked, setPicked] = useState([])
  const bottom = useRef(null)
  const sentRef = useRef(null)

  const loadConvs = useCallback(() => api('/api/chat/conversations').then(setConvs).catch(() => {}), [])
  useEffect(() => { loadConvs() }, [loadConvs])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  const send = useCallback(async (text, cid) => {
    if (!text.trim()) return
    setMessages((m) => [...m, { role: 'user', content: text }])
    setBusy(true)
    try {
      const r = await api('/api/chat', { method: 'POST', body: { message: text, conversation_id: cid ?? convId } })
      setConvId(r.conversation_id)
      setMessages((m) => [...m, { role: 'assistant', content: r.reply, products: r.products, notes: r.notes }])
      if (r.products.length) setLastProducts(r.products)
      loadConvs()
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: e.message, error: true }])
      toast.error(e.message)
    } finally { setBusy(false) }
  }, [convId, setLastProducts, loadConvs, toast])

  // A query typed in the header bar or spoken through the voice assistant arrives here.
  useEffect(() => {
    if (!pendingQuery) return
    const q = pendingQuery
    setPendingQuery(null)
    if (sentRef.current === q) return // already sending this exact message (dev-mode double run)
    sentRef.current = q
    setTimeout(() => { sentRef.current = null }, 1500)
    send(q)
  }, [pendingQuery]) // eslint-disable-line

  const openConv = async (id) => {
    try {
      const c = await api(`/api/chat/conversations/${id}`)
      const msgs = await Promise.all(c.messages.map(async (m) => {
        const ids = m.meta?.product_ids || []
        const products = (await Promise.all(ids.map((i) => api(`/api/products/${i}`).catch(() => null)))).filter(Boolean)
        return { role: m.role, content: m.content, products }
      }))
      setConvId(id); setMessages(msgs)
      setLastProducts(msgs.filter((m) => m.products?.length).slice(-1)[0]?.products || [])
    } catch (e) { toast.error(e.message) }
  }
  const newChat = () => { setConvId(null); setMessages([]); setPicked([]) }
  const toggle = (p) => setPicked((s) => (s.find((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : s.length < 4 ? [...s, p] : (toast.info('You can compare up to 4 products'), s)))

  return (
    <>
      <PageHeader title="AI Shopping Assistant" subtitle="Describe what you need. I search real products, compare them, and explain my picks.">
        <button className={btnGhost} onClick={newChat}><Icon name="add" className="text-base" />New chat</button>
      </PageHeader>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_16rem] gap-gutter-sm">
        <div>
          <div className="space-y-4 min-h-[40vh]">
            {messages.length === 0 && (
              <div className="bg-surface-container rounded-xl p-space-lg">
                <p className="font-body-md text-body-md text-on-surface-variant mb-3">Try one of these, or just speak using the mic:</p>
                <div className="flex flex-wrap gap-2">{SUGGESTIONS.map((s) => <button key={s} className={btnGhost} onClick={() => send(s)}>{s}</button>)}</div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`page-in ${m.role === 'user' ? 'flex justify-end' : ''}`}>
                <div className={`max-w-[95%] rounded-2xl px-space-md py-space-sm font-body-md text-body-md ${m.role === 'user' ? 'bg-primary-container text-on-primary-container' : m.error ? 'bg-error-container/30 text-on-error-container' : 'bg-surface-container text-on-surface'}`}>
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.notes?.map((n, j) => <p key={j} className="mt-2 font-body-sm text-body-sm text-secondary">{n}</p>)}
                </div>
                {m.products?.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-gutter-sm mt-3">
                    {m.products.map((p) => <ProductCard key={p.id} product={p} selected={!!picked.find((x) => x.id === p.id)} onToggleCompare={toggle} />)}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="flex gap-1 px-4 py-3 bg-surface-container rounded-2xl w-fit" aria-label="Assistant is thinking">{[0, 1, 2].map((i) => <span key={i} className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: `${i * 120}ms` }} />)}</div>}
            <div ref={bottom} />
          </div>
          {picked.length >= 2 && (
            <div className="page-in sticky bottom-24 mt-4 flex items-center justify-between bg-surface-container-high rounded-xl px-space-md py-space-sm shadow-xl">
              <span className="font-body-md text-body-md">{picked.length} products selected</span>
              <button className={btnPrimary} onClick={() => { setLastProducts(picked); navigate('/compare?ids=' + picked.map((p) => p.id).join(',')) }}>Compare</button>
            </div>
          )}
          <form onSubmit={(e) => { e.preventDefault(); const t = input; setInput(''); send(t) }} className="flex gap-2 mt-4">
            <input className={inputCls} value={input} onChange={(e) => setInput(e.target.value)} placeholder="e.g. I need a laptop under 60,000 for programming" aria-label="Message" disabled={busy} />
            <button className={btnPrimary} disabled={busy || !input.trim()}><Icon name="send" className="text-base" />Send</button>
          </form>
        </div>
        <aside className="bg-surface-container rounded-xl p-space-md h-fit">
          <div className="font-label-md text-label-md text-on-surface-variant mb-2">Previous chats</div>
          {convs.length === 0 ? <p className="font-body-sm text-body-sm text-outline">No chats yet.</p> : (
            <ul className="space-y-1">{convs.map((c) => <li key={c.id}><button onClick={() => openConv(c.id)} className={`w-full text-left px-2 py-1.5 rounded-lg font-body-sm text-body-sm line-clamp-1 hover:bg-surface-container-high ${c.id === convId ? 'bg-surface-container-high text-primary' : 'text-on-surface'}`}>{c.title}</button></li>)}</ul>
          )}
        </aside>
      </div>
    </>
  )
}