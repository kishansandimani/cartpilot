import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { btnGhost, btnPrimary, card, Icon, inputCls, PageHeader } from '../components/UI.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

export default function Settings() {
  const { user, setUser, logout } = useAuth()
  const toast = useToast()
  const [name, setName] = useState(user.full_name)
  const [lang, setLang] = useState(user.preferred_language)
  const [voice, setVoice] = useState(null)
  useEffect(() => { api('/api/voice/languages').then(setVoice).catch(() => {}) }, [])

  const save = async (e) => {
    e.preventDefault()
    try { setUser(await api('/api/users/me', { method: 'PATCH', body: { full_name: name, preferred_language: lang } })); toast.success('Profile saved') } catch (err) { toast.error(err.message) }
  }
  return (
    <>
      <PageHeader title="Settings & Security" subtitle="Your profile, voice language and how CartPilot keeps you in control." />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-gutter-sm">
        <form onSubmit={save} className={`${card} space-y-3`}>
          <h2 className="font-headline-sm text-headline-sm">Profile</h2>
          <div className="font-body-md text-body-md text-on-surface-variant">Email: {user.email}</div>
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" maxLength={120} aria-label="Full name" />
          <select className={inputCls} value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Preferred voice language"><option value="en">English</option><option value="hi">हिन्दी (Hindi)</option><option value="kn">ಕನ್ನಡ (Kannada)</option></select>
          <button className={btnPrimary}>Save</button>
        </form>
        <div className={`${card} space-y-3`}>
          <h2 className="font-headline-sm text-headline-sm">Security & control</h2>
          <ul className="space-y-2 font-body-md text-body-md">
            {['Voice commands require you to be logged in.', 'Saying "buy" only opens an order summary. Nothing is charged until you tick the confirmation box and approve in PayPal.', 'Payments are verified by the server with PayPal - never by the browser alone.', 'CartPilot never asks for or stores your Amazon/Flipkart passwords.'].map((t) => <li key={t} className="flex gap-2"><Icon name="verified_user" className="text-tertiary text-lg" />{t}</li>)}
          </ul>
          <button className={btnGhost} onClick={logout}>Log out</button>
        </div>
        <div className={`${card} lg:col-span-2`}>
          <h2 className="font-headline-sm text-headline-sm mb-2">Voice</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">{voice?.notes || 'Loading...'}</p>
          <ul className="mt-2 font-body-md text-body-md">{voice?.languages.map((l) => <li key={l.code}>{l.label} ({l.recognition}){l.note && <span className="text-outline"> - {l.note}</span>}</li>)}</ul>
        </div>
      </div>
    </>
  )
}
