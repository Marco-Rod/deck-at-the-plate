import { useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Languages, Loader2, User } from 'lucide-react'
import { ApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/Button'
import { InputField } from '@/shared/ui/InputField'
import { PasswordField } from '@/shared/ui/PasswordField'
import { login, register } from '../api'
import { useAuthStore } from '../store'
import { validateLogin, validateRegister } from '../lib/validation'
import { OnlineRequiredHint } from '@/offline/OnlineRequiredHint'
import { useOnlineStatus } from '@/offline/useOnlineStatus'
import type { AuthFieldErrors, AuthFieldKey, AuthFormValues, AuthMode } from '../lib/validation'

const initialValues: AuthFormValues = {
  username: '',
  password: '',
  confirmPassword: '',
}

const tabs: Array<{ id: AuthMode; labelKey: 'auth.login_tab' | 'auth.register_tab' }> = [
  { id: 'login', labelKey: 'auth.login_tab' },
  { id: 'register', labelKey: 'auth.register_tab' },
]

export function AuthPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const signIn = useAuthStore((state) => state.signIn)
  const refreshProfile = useAuthStore((state) => state.refreshProfile)
  const online = useOnlineStatus()

  const [mode, setMode] = useState<AuthMode>('login')
  const [values, setValues] = useState<AuthFormValues>(initialValues)
  const [fieldErrors, setFieldErrors] = useState<AuthFieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const switchMode = (next: AuthMode) => {
    setMode(next)
    setFieldErrors({})
    setSubmitError(null)
  }

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const nextIndex = event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? tabs.length - 1
        : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
    const nextTab = tabs[nextIndex]
    if (!nextTab) return
    switchMode(nextTab.id)
    event.currentTarget.parentElement
      ?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[nextIndex]
      ?.focus()
  }

  const setField = (key: AuthFieldKey, value: string) => {
    setValues((current) => ({ ...current, [key]: value }))
    setFieldErrors((current) => (current[key] ? { ...current, [key]: undefined } : current))
  }

  const toggleLanguage = () => {
    const next = (i18n.language ?? 'es').startsWith('es') ? 'en' : 'es'
    void i18n.changeLanguage(next)
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError(null)
    if (!online) {
      setSubmitError(t('offline.action_requires_connection'))
      return
    }

    const errors = mode === 'login' ? validateLogin(values) : validateRegister(values)
    setFieldErrors(errors)
    if (Object.values(errors).some(Boolean)) return

    setLoading(true)
    try {
      if (mode === 'register') {
        await register({ username: values.username.trim(), password: values.password })
      }
      const session = await login(values.username.trim(), values.password)
      signIn(session)
      await refreshProfile()
      navigate('/lobby', { replace: true })
    } catch (error) {
      setSubmitError(error instanceof ApiError ? error.message : t('auth.error.generic'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-aurora relative flex min-h-dvh flex-col overflow-x-hidden bg-koshien-dark px-4 pb-[max(2rem,calc(env(safe-area-inset-bottom)+1rem))] pt-[max(1rem,env(safe-area-inset-top))] select-none">
      <link
        rel="preload"
        as="image"
        href="/login-background.avif"
        type="image/avif"
        fetchPriority="high"
      />
      <button
        type="button"
        onClick={toggleLanguage}
        className="absolute right-4 top-[max(1rem,env(safe-area-inset-top))] z-10 inline-flex items-center gap-1.5 rounded-full border border-koshien-gold/40 bg-koshien-green/70 px-3 py-1.5 font-vintage text-xs uppercase tracking-widest text-koshien-chalk transition-colors hover:bg-koshien-green focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold"
      >
        <Languages className="h-3.5 w-3.5" aria-hidden />
        {(i18n.language ?? 'es').startsWith('es') ? 'EN' : 'ES'}
      </button>

      <div className="relative mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
        <header className="mb-8 text-center">
          <picture>
            <source srcSet="/logo-mark-128.avif" type="image/avif" />
            <img
              src="/logo-mark.png"
              alt=""
              width="128"
              height="128"
              fetchPriority="high"
              decoding="async"
              className="mx-auto mb-4 h-auto w-24 sm:w-28"
            />
          </picture>
          <span className="inline-block rounded-full border border-koshien-gold/40 bg-koshien-green/60 px-4 py-1 font-vintage text-[10px] uppercase tracking-[0.28em] text-koshien-gold">
            {t('app.tradition')}
          </span>
          <h1 className="mt-3 font-sports text-[2.6rem] font-bold uppercase leading-[0.95] tracking-wide text-koshien-chalk">
            Deck at the Plate
          </h1>
          <p className="mt-2 font-vintage text-xs uppercase tracking-[0.22em] text-koshien-cream">
            {t('app.subtitle')}
          </p>
        </header>

        <section
          role="tablist"
          aria-label={t('auth.select_mode')}
          className="grid grid-cols-2 gap-1 rounded-2xl border border-koshien-border bg-koshien-dark/80 p-1"
        >
          {tabs.map((tab, index) => {
            const active = mode === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                tabIndex={active ? 0 : -1}
                onClick={() => switchMode(tab.id)}
                onKeyDown={(event) => handleTabKeyDown(event, index)}
                className={`rounded-xl py-2.5 font-sports text-xl uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-koshien-gold ${
                  active
                    ? 'bg-koshien-green text-koshien-chalk'
                    : 'text-koshien-cream/70 hover:text-koshien-chalk'
                }`}
              >
                {t(tab.labelKey)}
              </button>
            )
          })}
        </section>

        <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4">
          {submitError ? (
            <div
              role="alert"
              className="rounded-xl border border-red-500/50 bg-red-900/40 px-4 py-3 font-vintage text-xs leading-relaxed text-red-300"
            >
              {submitError}
            </div>
          ) : null}

          <InputField
            label={t('auth.username_label')}
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            placeholder="Bateador33"
            value={values.username}
            onChange={(event) => setField('username', event.target.value)}
            error={fieldErrors.username ? t(fieldErrors.username) : undefined}
            leadingIcon={<User className="h-4 w-4" aria-hidden />}
          />

          <PasswordField
            label={t('auth.password_label')}
            name="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            placeholder="••••••••"
            value={values.password}
            onChange={(event) => setField('password', event.target.value)}
            error={fieldErrors.password ? t(fieldErrors.password) : undefined}
          />

          {mode === 'register' ? (
            <PasswordField
              label={t('auth.confirm_password_label')}
              name="confirmPassword"
              autoComplete="new-password"
              placeholder="••••••••"
              value={values.confirmPassword ?? ''}
              onChange={(event) => setField('confirmPassword', event.target.value)}
              error={fieldErrors.confirmPassword ? t(fieldErrors.confirmPassword) : undefined}
            />
          ) : null}

          <Button
            type="submit"
            size="lg"
            disabled={loading || !online}
            aria-describedby={!online ? 'auth-online-required' : undefined}
            className="mt-2 w-full"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : null}
            {loading
              ? t('common.loading')
              : t(mode === 'login' ? 'auth.submit_login' : 'auth.submit_register')}
          </Button>
          <OnlineRequiredHint id="auth-online-required" visible={!online} />
        </form>
      </div>
    </main>
  )
}
