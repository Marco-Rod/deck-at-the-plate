import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff, Lock } from 'lucide-react'
import type { InputHTMLAttributes } from 'react'
import { InputField } from './InputField'

export interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  error?: string
}

export function PasswordField({ label, error, ...props }: PasswordFieldProps) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)

  return (
    <InputField
      {...props}
      label={label}
      error={error}
      type={visible ? 'text' : 'password'}
      leadingIcon={<Lock className="h-4 w-4" />}
      trailingAction={
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? t('auth.hide_password') : t('auth.show_password')}
          aria-pressed={visible}
          className="rounded-lg p-2 text-koshien-cream/60 transition-colors hover:text-koshien-gold focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-koshien-gold"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      }
    />
  )
}
