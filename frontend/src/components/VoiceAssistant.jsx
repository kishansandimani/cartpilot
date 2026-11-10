import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useVoice } from '../hooks/useVoice.js'
import { useShopping } from '../context/ShoppingContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { btnPrimary, Icon, inputCls } from './UI.jsx'

const STATUS_LABEL = { idle: 'Tap the mic and speak, or type below', listening: 'Listening...', processing: 'Working on it...', success: 'Done', error: 'Something went wrong' }
const STATUS_COLOR = { idle: 'text-on-surface-variant', listening: 'text-primary', processing: 'text-secondary', success: 'text-tertiary', error: 'text-error' }

/** Global voice assistant: floating mic on every page. Open with the button, the header mic, or Ctrl/Cmd+K. */
export default function VoiceAssistant() {
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const { lastProducts, refreshCart, setPendingQuery } = useShopping()
  const [open, setOpen] = useState(false)
  const [lang, setLang] = useState(user?.preferred_language || 'en')
  const [speakOut, setSpeakOut] = useState(true)
  const [typed, setTyped] = useState('')
  const [reply, setReply] = useState('')
  const [confirmNote, setConfirmNote] = useState(false)
  const lastIdsRef = useRef([])
  lastIdsRef.current = lastProducts.map((p) => p.id)
  const voiceRef = useRef(null)

  const run = useCallback(async (text) => {
    voiceRef.current?.setStatus('processing')
    setReply(''); setConfirmNote(false)
    try {
      const res = await api('/api/voice/command', { method: 'POST', body: { text, language: lang, context: { last_product_ids: lastIdsRef.current } } })
      setReply(res.speech)
      setConfirmNote(res.requires_confirmation)
      voiceRef.current?.setStatus('success')
      if (speakOut && res.speech) voiceRef.current?.speak(res.speech, res.language)
      const a = res.action || {}
      if (a.type === 'navigate' || a.type === 'confirm_purchase') navigate(a.path)
      else if (a.type === 'assistant_query') { setPendingQuery(a.query); navigate('/assistant') }
      else if (a.type === 'cart_updated') refreshCart()
    } catch (e) {
      voiceRef.current?.setStatus('error')
      voiceRef.current?.setError(e.message)
      toast.error(e.message)
    }
  }, [lang, speakOut, navigate, refreshCart, setPendingQuery, toast])

  const voice = useVoice({ lang, onFinal: run })
  voiceRef.current = voice

  useEffect(() => {
    const toggle = () => setOpen((o) => !o)
    const onKey = (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); toggle() } if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    window.addEventListener('cartpilot-open-voice', toggle)
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('cartpilot-open-voice', toggle) }
  }, [])

  const listening = voice.status === 'listening'
  const submitTyped = (e) => { e.preventDefault(); const t = typed.trim(); if (!t) return; setTyped(''); voice.setTranscript(t); run(t) }

  return (
    <>
      {open && (
        <div className="page-in fixed bottom-24 right-6 z-[90] w-[22rem] max-w-[calc(100vw-2rem)] bg-surface-container-low rounded-2xl shadow-2xl border border-outline-variant/40 p-space-md" role="dialog" aria-label="Voice assistant">
          <div className="flex items-center justify-between mb-2">
            <span className="font-title-md text-title-md text-on-surface">Voice assistant</span>
            <button onClick={() => setOpen(false)} aria-label="Close voice assistant" className="text-outline hover:text-on-surface"><Icon name="close" /></button>
          </div>
          <div className={`font-label-md text-label-md mb-2 ${STATUS_COLOR[voice.status]}`} aria-live="polite">{STATUS_LABEL[voice.status]}</div>

          <div className="h-14 flex items-center justify-center gap-[3px] bg-surface-container rounded-lg mb-2" aria-hidden="true">
            {voice.levels.map((l, i) => (
              <div key={i} className={`w-1 rounded-full transition-all duration-75 ${listening ? 'bg-primary' : 'bg-outline-variant'}`} style={{ height: `${Math.max(4, l * 48)}px` }} />
            ))}
          </div>

          <div className="min-h-[2.5rem] bg-surface-container rounded-lg px-3 py-2 font-body-md text-body-md text-on-surface mb-2">
            {voice.transcript || <span className="text-outline">Live transcript appears here</span>}
          </div>
          {voice.error && <div className="text-error font-body-sm text-body-sm mb-2" role="alert">{voice.error}</div>}
          {reply && <div className="text-tertiary font-body-sm text-body-sm mb-2">{reply}</div>}
          {confirmNote && <div className="bg-secondary-container/30 text-on-secondary-container rounded-lg px-3 py-2 font-body-sm text-body-sm mb-2">Nothing has been charged. Review the order on the Cart page and confirm there.</div>}

          <div className="flex items-center gap-2 mb-2">
            <select value={lang} onChange={(e) => setLang(e.target.value)} className={`${inputCls} !w-auto`} aria-label="Language">
              <option value="en">English</option><option value="hi">हिन्दी</option><option value="kn">ಕನ್ನಡ</option>
            </select>
            <label className="flex items-center gap-1 font-body-sm text-body-sm text-on-surface-variant cursor-pointer">
              <input type="checkbox" checked={speakOut} onChange={(e) => setSpeakOut(e.target.checked)} /> Speak replies
            </label>
          </div>
          {!voice.supported && <p className="font-body-sm text-body-sm text-outline mb-2">Voice input is not available in this browser. Typing works everywhere.</p>}
          <form onSubmit={submitTyped} className="flex gap-2">
            <input className={inputCls} value={typed} onChange={(e) => setTyped(e.target.value)} placeholder='Try: "open my cart"' aria-label="Type a command" />
            <button className={btnPrimary} type="submit" aria-label="Send command"><Icon name="send" className="text-base" /></button>
          </form>
        </div>
      )}
      <button
        onClick={() => { if (!open) setOpen(true); listening ? voice.stop() : voice.start() }}
        aria-label={listening ? 'Stop listening' : 'Start voice command'}
        title="Voice assistant (Ctrl/Cmd+K)"
        className={`fixed bottom-6 right-6 z-[90] h-14 w-14 rounded-full flex items-center justify-center shadow-xl transition active:scale-95 ${listening ? 'bg-error text-on-error orb-listening' : 'bg-primary-container text-on-primary-container hover:brightness-110'}`}
      >
        <Icon name={listening ? 'stop' : 'mic'} className="text-2xl" />
      </button>
    </>
  )
}
