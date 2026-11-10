export const card = 'bg-surface-container rounded-xl p-space-lg'
export const btnPrimary = 'inline-flex items-center justify-center gap-1.5 px-space-md py-2 rounded-lg bg-primary-container text-on-primary-container font-label-md text-label-md hover:brightness-110 active:scale-[.98] transition disabled:opacity-50 disabled:cursor-not-allowed'
export const btnGhost = 'inline-flex items-center justify-center gap-1.5 px-space-md py-2 rounded-lg bg-surface-container-high text-on-surface font-label-md text-label-md hover:bg-surface-container-highest active:scale-[.98] transition disabled:opacity-50 disabled:cursor-not-allowed'
export const inputCls = 'w-full bg-surface-container-high rounded-lg px-space-md py-2 text-on-surface placeholder:text-outline focus:outline-none focus:ring-1 focus:ring-primary font-body-md text-body-md'

export const Icon = ({ name, className = '' }) => <span className={`material-symbols-outlined ${className}`}>{name}</span>

export function Skeleton({ className = 'h-24 w-full' }) { return <div className={`skeleton ${className}`} /> }

export function SkeletonGrid({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-gutter-sm">
      {Array.from({ length: count }).map((_, i) => <Skeleton key={i} className="h-72" />)}
    </div>
  )
}

export function EmptyState({ icon = 'inbox', title, children, action }) {
  return (
    <div className="flex flex-col items-center text-center py-16 px-6 bg-surface-container-low rounded-xl">
      <Icon name={icon} className="text-5xl text-outline mb-3" />
      <h3 className="font-headline-sm text-headline-sm text-on-surface mb-1">{title}</h3>
      {children && <p className="font-body-md text-body-md text-on-surface-variant max-w-md">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex items-start gap-3 bg-error-container/30 border border-error/40 text-on-error-container rounded-xl p-space-md" role="alert">
      <Icon name="error" className="text-error" />
      <div className="flex-1 font-body-md text-body-md">{message}</div>
      {onRetry && <button onClick={onRetry} className={btnGhost}>Retry</button>}
    </div>
  )
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-space-lg">
      <div>
        <h1 className="font-headline-lg text-headline-lg text-on-surface">{title}</h1>
        {subtitle && <p className="font-body-md text-body-md text-on-surface-variant mt-1">{subtitle}</p>}
      </div>
      <div className="flex gap-2">{children}</div>
    </div>
  )
}

export function Bars({ rows, labelKey, valueKey, format }) {
  const max = Math.max(...rows.map((r) => Number(r[valueKey])), 1)
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r[labelKey]}>
          <div className="flex justify-between font-body-sm text-body-sm text-on-surface-variant mb-1">
            <span className="capitalize">{r[labelKey]}</span><span className="font-mono-data text-mono-data text-on-surface">{format(r[valueKey])}</span>
          </div>
          <div className="h-2 rounded-full bg-surface-container-high overflow-hidden">
            <div className="h-full rounded-full bg-primary-container transition-all duration-700" style={{ width: `${(Number(r[valueKey]) / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}
