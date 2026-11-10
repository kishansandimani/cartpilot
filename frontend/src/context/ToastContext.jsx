import { createContext, useCallback, useContext, useState } from 'react'

const ToastCtx = createContext(null)
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, type = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500)
  }, [])
  const toast = { info: (m) => push(m, 'info'), success: (m) => push(m, 'success'), error: (m) => push(m, 'error') }
  const color = { info: 'border-primary', success: 'border-tertiary', error: 'border-error' }
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="fixed bottom-24 right-6 z-[100] flex flex-col gap-2 max-w-sm" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-in bg-surface-container-high text-on-surface text-body-md px-4 py-3 rounded-lg border-l-4 shadow-xl ${color[t.type]}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
