import { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface IntroPlayer {
  name: string
  number: string
  photo?: string
  overall?: number
  position?: string
}

interface GameIntroModalProps {
  userTeamName: string
  userTeamLogo?: string
  userPitcher?: IntroPlayer
  userLineup?: IntroPlayer[]
  cpuTeamName: string
  cpuTeamLogo?: string
  cpuPitcher?: IntroPlayer
  cpuLineup?: IntroPlayer[]
  onPlayBall: () => void
}

export function GameIntroModal({
  userTeamName,
  userTeamLogo,
  userPitcher,
  userLineup = [],
  cpuTeamName,
  cpuTeamLogo,
  cpuPitcher,
  cpuLineup = [],
  onPlayBall,
}: GameIntroModalProps) {
  const { t } = useTranslation()
  const [isVisible, setIsVisible] = useState(true)

  const handlePlayBall = () => {
    setIsVisible(false)
    setTimeout(onPlayBall, 300)
  }

  if (!isVisible) return null

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-koshien-dark"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/start-mobile.png')" }}
      />
      <div
        className="absolute inset-0 hidden bg-cover bg-center desktop:block"
        style={{ backgroundImage: "url('/start-desktop.png')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/45 to-black/75" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(197,160,89,0.12),transparent_60%)]" />
      <div className="absolute inset-0 bg-black/25 backdrop-blur-[2px]" />

      <motion.div
        className="relative z-10 flex h-screen w-full items-center justify-between px-4 py-6"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      >
        <motion.div
          className="flex w-1/3 flex-col items-center justify-start gap-3"
          initial={{ x: -100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          {userTeamLogo && (
            <motion.img
              src={userTeamLogo}
              alt={userTeamName}
              className="h-16 w-16 object-contain drop-shadow-lg"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.4, type: 'spring' }}
            />
          )}

          <h3 className="font-sports text-center text-xl uppercase tracking-wider text-koshien-gold">
            {userTeamName}
          </h3>

          {userPitcher && (
            <motion.div
              className="w-full rounded border border-koshien-border bg-koshien-dark p-3 text-center"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <p className="mb-1 text-xs text-gray-400">{t('game.intro_pitcher_label')}</p>
              {userPitcher.photo && (
                <img
                  src={userPitcher.photo}
                  alt={userPitcher.name}
                  className="mx-auto mb-1 h-12 w-12 rounded-full object-cover"
                />
              )}
              <p className="text-sm font-bold text-koshien-chalk">{userPitcher.name}</p>
              <div className="mt-1 flex items-center justify-center text-xs">
                <p className="text-gray-400">#{userPitcher.number}</p>
                {userPitcher.position && (
                  <p className="mx-1 font-bold text-koshien-gold">{userPitcher.position}</p>
                )}
              </div>
              {userPitcher.overall && (
                <p className="mt-1 text-xs font-bold text-koshien-gold">
                  {t('game.intro_ovr')}: {userPitcher.overall}
                </p>
              )}
            </motion.div>
          )}

          <motion.div
            className="w-full space-y-1"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <p className="mb-2 text-center text-xs font-bold uppercase tracking-wider text-gray-400">
              {t('game.intro_lineup')}
            </p>
            {userLineup.slice(0, 9).map((player, idx) => (
              <motion.div
                key={idx}
                className="border border-koshien-border bg-[#0A0D0F] p-1.5 text-center"
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.7 + idx * 0.03 }}
              >
                <p className="text-xs font-bold text-koshien-gold">
                  {idx + 1}. {player.name}
                </p>
                <div className="flex items-center justify-between px-1 text-xs">
                  <p className="text-gray-400">#{player.number}</p>
                  {player.position && <p className="text-koshien-gold">{player.position}</p>}
                  {player.overall && <p className="font-bold text-koshien-gold">{player.overall}</p>}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>

        <motion.div
          className="flex w-1/3 flex-col items-center justify-center gap-8"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6, type: 'spring' }}
        >
          <motion.div
            className="font-sports text-8xl font-bold text-koshien-gold drop-shadow-lg"
            animate={{
              scale: [1, 1.1, 1],
              textShadow: [
                '0 0 20px rgba(197,160,89,0.5)',
                '0 0 40px rgba(197,160,89,0.8)',
                '0 0 20px rgba(197,160,89,0.5)',
              ],
            }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            VS
          </motion.div>

          <motion.button
            type="button"
            onClick={handlePlayBall}
            className="cursor-pointer border-2 border-koshien-gold bg-koshien-green px-8 py-4 font-sports text-3xl uppercase tracking-wider text-koshien-gold shadow-2xl transition-all hover:bg-[#2D5A3F]"
            animate={{
              scale: [1, 1.05, 1],
              boxShadow: [
                '0 0 20px rgba(197,160,89,0.5)',
                '0 0 40px rgba(197,160,89,0.8)',
                '0 0 20px rgba(197,160,89,0.5)',
              ],
            }}
            transition={{ duration: 2, repeat: Infinity }}
            whileHover={{ scale: 1.05, boxShadow: '0 0 30px rgba(197,160,89,0.6)' }}
            whileTap={{ scale: 0.95 }}
          >
            {t('game.intro_play_ball')}
          </motion.button>
        </motion.div>

        <motion.div
          className="flex w-1/3 flex-col items-center justify-start gap-3"
          initial={{ x: 100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          {cpuTeamLogo && (
            <motion.img
              src={cpuTeamLogo}
              alt={cpuTeamName}
              className="h-16 w-16 object-contain drop-shadow-lg"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.4, type: 'spring' }}
            />
          )}

          <h3 className="font-sports text-center text-xl uppercase tracking-wider text-koshien-chalk">
            {cpuTeamName}
          </h3>

          {cpuPitcher && (
            <motion.div
              className="w-full rounded border border-koshien-border bg-koshien-dark p-3 text-center"
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <p className="mb-1 text-xs text-gray-400">{t('game.intro_pitcher_label')}</p>
              {cpuPitcher.photo && (
                <img
                  src={cpuPitcher.photo}
                  alt={cpuPitcher.name}
                  className="mx-auto mb-1 h-12 w-12 rounded-full object-cover"
                />
              )}
              <p className="text-sm font-bold text-koshien-chalk">{cpuPitcher.name}</p>
              <div className="mt-1 flex items-center justify-center text-xs">
                <p className="text-gray-400">#{cpuPitcher.number}</p>
                {cpuPitcher.position && (
                  <p className="mx-1 font-bold text-koshien-gold">{cpuPitcher.position}</p>
                )}
              </div>
              {cpuPitcher.overall && (
                <p className="mt-1 text-xs font-bold text-koshien-gold">
                  {t('game.intro_ovr')}: {cpuPitcher.overall}
                </p>
              )}
            </motion.div>
          )}

          <motion.div
            className="w-full space-y-1"
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            <p className="mb-2 text-center text-xs font-bold uppercase tracking-wider text-gray-400">
              {t('game.intro_lineup')}
            </p>
            {cpuLineup.slice(0, 9).map((player, idx) => (
              <motion.div
                key={idx}
                className="border border-koshien-border bg-[#0A0D0F] p-1.5 text-center"
                initial={{ x: 20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.7 + idx * 0.03 }}
              >
                <p className="text-xs font-bold text-koshien-chalk">
                  {idx + 1}. {player.name}
                </p>
                <div className="flex items-center justify-between px-1 text-xs">
                  <p className="text-gray-400">#{player.number}</p>
                  {player.position && <p className="text-koshien-gold">{player.position}</p>}
                  {player.overall && <p className="font-bold text-koshien-gold">{player.overall}</p>}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </motion.div>
    </motion.div>
  )
}