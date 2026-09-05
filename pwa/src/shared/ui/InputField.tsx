import { useId } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'

export interface InputFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
  leadingIcon?: ReactNode
  trailingAction?: ReactNode
}

export function InputField({
  label,
  error,
  leadingIcon,
  trailingAction,
  className = '',
  id,
  ...props
}: InputFieldProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const errorId = error ? `${inputId}-error` : undefined

  return (
    <div className="w-full">
      <label
        htmlFor={inputId}
        className="mb-1.5 block font-vintage text-xs uppercase tracking-widest text-koshien-cream"
      >
        {label}
      </label>
      <div className="relative">
        {leadingIcon ? (
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-koshien-cream/50"
          >
            {leadingIcon}
          </span>
        ) : null}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          className={`h-12 w-full rounded-xl border bg-koshien-dark/80 px-3 text-base text-koshien-chalk transition-colors placeholder:text-koshien-cream/60 focus:border-koshien-gold focus:outline-none focus:ring-2 focus:ring-koshien-gold/40 ${leadingIcon ? 'pl-10' : ''} ${trailingAction ? 'pr-12' : ''} ${error ? 'border-red-500/60 focus:border-red-400 focus:ring-red-400/40' : 'border-koshien-border'} ${className}`}
          {...props}
        />
        {trailingAction ? (
          <span className="absolute inset-y-0 right-2 flex items-center">{trailingAction}</span>
        ) : null}
      </div>
      {errorId && error ? (
        <p id={errorId} role="alert" className="mt-1.5 font-vintage text-xs text-red-400">
          {error}
        </p>
      ) : null}
    </div>
  )
}
