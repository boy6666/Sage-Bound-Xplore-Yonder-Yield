import type { ReactNode } from 'react'

interface FieldProps {
  label: string
  htmlFor?: string
  hint?: string
  error?: string | null
  required?: boolean
  className?: string
  children: ReactNode
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  required,
  className,
  children,
}: FieldProps) {
  return (
    <div className={className ?? 'space-y-1'}>
      <label className="label" htmlFor={htmlFor}>
        {label}
        {required ? (
          <span className="ml-0.5 text-rose-300" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {children}
      {hint ? <p className="text-xs text-muted">{hint}</p> : null}
      {error ? (
        <p role="alert" className="text-xs font-medium text-rose-300">
          {error}
        </p>
      ) : null}
    </div>
  )
}
