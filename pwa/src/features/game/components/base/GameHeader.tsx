import { useTranslation } from 'react-i18next'

interface GameHeaderProps {
  teamName?: string
  isConnected?: boolean
  onBack: () => void
}

export function GameHeader({
  teamName = 'CAMPO DE JUEGO',
  isConnected = false,
  onBack,
}: GameHeaderProps) {
  const { t } = useTranslation()
  const connectionClass = isConnected ? 'text-emerald-400' : 'text-red-400'
  const indicator = isConnected ? '●' : '○'

  return (
    <header className="z-30 mb-3 w-full border-b-2 border-koshien-gold/40 pb-4">
      <div className="mb-2 flex items-start justify-between">
        <h2 className="font-sports text-4xl uppercase leading-none tracking-wider text-koshien-chalk">
          {teamName}
        </h2>

        <button
          type="button"
          onClick={onBack}
          className="cursor-pointer border border-koshien-gold bg-koshien-dark px-4 py-2 font-vintage text-xs font-bold text-koshien-gold transition-colors duration-200 hover:bg-koshien-green"
        >
          {t('game.lobby')}
        </button>
      </div>

      <span className={`flex items-center gap-1.5 font-vintage text-[9px] ${connectionClass}`}>
        <span>{indicator}</span>
        <span>{isConnected ? t('game.live') : t('game.disconnected')}</span>
      </span>
    </header>
  )
}