import { useTranslation } from 'react-i18next'

export function CardBack() {
  const { t } = useTranslation()
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-3 text-center">
      <span className="pack-card__back-logo block aspect-square opacity-90">
        <img src="/card-back-logo.png" alt="" className="h-auto w-full" />
      </span>
      <span className="font-sports text-base font-bold uppercase tracking-widest text-koshien-gold sm:text-lg">
        DECK
      </span>
      <span className="font-sports -mt-2 text-base font-bold uppercase tracking-[0.18em] text-koshien-cream/70 sm:text-lg">
        AT THE PLATE
      </span>
      <span className="font-vintage text-[9px] uppercase tracking-[0.2em] text-koshien-cream/45 sm:text-[10px]">
        {t('card.tapToReveal')}
      </span>
    </div>
  )
}
