import { Loader2 } from 'lucide-react'

interface Props {
  label?: string
  className?: string
}

export function Spinner({ label, className = '' }: Props) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center gap-3 ${className}`}
    >
      <Loader2 className="h-8 w-8 animate-spin text-koshien-gold" aria-hidden />
      {label ? <span className="sr-only">{label}</span> : null}
    </div>
  )
}
