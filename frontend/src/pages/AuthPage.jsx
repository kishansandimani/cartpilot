import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { btnPrimary, Icon, inputCls } from '../components/UI.jsx'

export default function AuthPage({ mode }) {
  const { login, register } = useAuth()
  const isLogin = mode === 'login'
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault(); setError(''); setBusy(true)
    try { isLogin ? await login(form.email, form.password) : await register(form.email, form.password, form.full_name) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <form onSubmit={submit} className="page-in w-full max-w-md bg-surface-container rounded-2xl p-space-xl space-y-4">
        <div className="flex items-center gap-2 mb-2"><Icon name="shopping_cart_checkout" className="text-primary text-3xl" /><span className="font-headline-sm text-headline-sm text-on-surface font-bold">CartPilot AI</span></div>
        <p className="font-body-md text-body-md text-on-surface-variant">Tell AI what you need. Let it shop. You stay in control.</p>
        <h1 className="font-headline-md text-headline-md text-on-surface">{isLogin ? 'Log in' : 'Create your account'}</h1>
        {!isLogin && <input className={inputCls} placeholder="Full name" value={form.full_name} onChange={set('full_name')} autoComplete="name" />}
        <input className={inputCls} type="email" required placeholder="Email" value={form.email} onChange={set('email')} autoComplete="email" />
        <input className={inputCls} type="password" required minLength={isLogin ? 1 : 8} maxLength={72} placeholder={isLogin ? 'Password' : 'Password (8+ characters)'} value={form.password} onChange={set('password')} autoComplete={isLogin ? 'current-password' : 'new-password'} />
        {error && <div className="text-error font-body-sm text-body-sm" role="alert">{error}</div>}
        <button className={`${btnPrimary} w-full`} disabled={busy}>{busy ? 'Please wait...' : isLogin ? 'Log in' : 'Sign up'}</button>
        <p className="font-body-sm text-body-sm text-on-surface-variant text-center">
          {isLogin ? <>New here? <Link className="text-primary" to="/register">Create an account</Link></> : <>Already registered? <Link className="text-primary" to="/login">Log in</Link></>}
        </p>
      </form>
    </div>
  )
}
