import { useTranslation } from 'react-i18next'

export function OnlineRequiredHint({ id, visible }: { id: string; visible: boolean }) {
  const { t } = useTranslation()
  if (!visible) return null
  return (
    <p id={id} role="note" className="mt-2 font-vintage text-[10px] uppercase tracking-wider text-amber-300">
      {t('offline.action_requires_connection')}
    </p>
  )
}
