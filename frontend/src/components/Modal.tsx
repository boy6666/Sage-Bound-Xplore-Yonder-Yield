import { useEffect, useRef, type ReactNode } from 'react'

interface ModalProps {
  open: boolean
  title: string
  description?: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  widthClass?: string
}

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
  footer,
  widthClass = 'max-w-lg',
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', handleKey)
    const timer = window.setTimeout(() => panelRef.current?.focus(), 0)
    return () => {
      document.removeEventListener('keydown', handleKey)
      window.clearTimeout(timer)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm sm:items-center"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`card w-full ${widthClass} my-auto outline-none`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-edge p-4 md:p-5">
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-ink">{title}</h2>
            {description ? <p className="text-xs text-muted">{description}</p> : null}
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            aria-label="关闭对话框"
            onClick={onClose}
          >
            关闭
          </button>
        </div>
        <div className="p-4 md:p-5">{children}</div>
        {footer ? (
          <div className="flex flex-wrap justify-end gap-2 border-t border-edge p-4 md:p-5">
            {footer}
          </div>
        ) : null}
      </div>
    </div>
  )
}
