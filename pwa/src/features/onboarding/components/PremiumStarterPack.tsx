import { motion } from 'framer-motion'
import { FloatingParticles } from './FloatingParticles'
import { PackBenefits } from './PackBenefits'

interface PremiumStarterPackProps {
  cardCount: number
  onClick: () => void
  teamName?: string // Opcional para futuras extensiones
}

export function PremiumStarterPack({ cardCount, onClick }: PremiumStarterPackProps) {
  return (
    <motion.div
      className="relative mx-auto flex w-full max-w-6xl items-center justify-center gap-8 px-4 pt-10 lg:gap-16"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.15, rotate: 6 }}
      transition={{ duration: 0.45, ease: 'easeInOut' }}
    >
      {/* Partículas flotantes de fondo */}
      <FloatingParticles />

      {/* Beneficios lado izquierdo */}
      <PackBenefits side="left" />

      {/* Contenedor central del sobre */}
      <motion.button
        type="button"
        aria-label="Haz clic para abrir tu paquete inicial"
        onClick={onClick}
        className="group relative cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-8 focus-visible:outline-koshien-gold"
        animate={{ y: [0, -14, 0] }}
        transition={{ 
          y: { duration: 2.6, repeat: Infinity, ease: 'easeInOut' },
        }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        {/* Capa exterior con resplandor animado */}
        <motion.div
          className="premium-pack-outer"
          animate={{
            boxShadow: [
              '0 0 60px rgba(212, 175, 55, 0.4), 0 0 100px rgba(197, 160, 89, 0.3), 0 0 140px rgba(244, 229, 184, 0.2)',
              '0 0 80px rgba(212, 175, 55, 0.6), 0 0 120px rgba(197, 160, 89, 0.5), 0 0 160px rgba(244, 229, 184, 0.3)',
              '0 0 60px rgba(212, 175, 55, 0.4), 0 0 100px rgba(197, 160, 89, 0.3), 0 0 140px rgba(244, 229, 184, 0.2)',
            ],
          }}
          transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
        >
          {/* Marco dorado biselado */}
          <div className="premium-pack-frame">
            {/* Efecto de brillo deslizante (sweep shine) */}
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 z-20 w-1/3 bg-gradient-to-r from-transparent via-white/50 to-transparent"
              style={{
                left: '-40%',
                transform: 'skewX(-12deg)',
                animation: 'pack-sweep-shine 2.5s ease-in-out infinite',
                animationDelay: '1s',
              }}
            />

            {/* Contenido interno */}
            <div className="premium-pack-content">
              {/* Badge superior "PREMIUM STARTER PACK" */}
              <motion.span
                className="relative z-10 rounded-full bg-gradient-to-r from-white to-yellow-100 px-4 py-1.5 font-vintage text-[10px] font-bold uppercase tracking-widest text-[#1a1a00] shadow-lg lg:px-5 lg:py-2 lg:text-[11px]"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.4, ease: 'backOut' }}
              >
                Premium Starter Pack
              </motion.span>

              {/* Pelota central con rotación continua */}
              <motion.div
                className="relative z-10 flex flex-1 items-center justify-center"
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ delay: 0.5, duration: 0.6, ease: 'backOut' }}
              >
                <motion.span
                  className="text-7xl drop-shadow-2xl lg:text-8xl"
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                >
                  ⚾
                </motion.span>
              </motion.div>

              {/* Contador de cartas y CTA */}
              <motion.div
                className="relative z-10 text-center"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.7, duration: 0.5 }}
              >
                <span
                  className="block font-sports text-5xl font-bold uppercase tracking-wider text-white drop-shadow-lg lg:text-6xl"
                  style={{
                    textShadow:
                      '0 0 20px rgba(212, 175, 55, 0.6), 0 2px 8px rgba(0, 0, 0, 0.8), 0 4px 16px rgba(197, 160, 89, 0.4)',
                  }}
                >
                  {cardCount}
                </span>
                <span
                  className="mt-1 block font-sports text-2xl font-bold uppercase tracking-wide text-koshien-gold lg:text-3xl"
                  style={{
                    textShadow: '0 2px 6px rgba(0, 0, 0, 0.6)',
                  }}
                >
                  Cartas
                </span>
                <motion.span
                  className="mt-3 block font-vintage text-[10px] uppercase tracking-[0.18em] text-white/80 lg:mt-4 lg:text-[11px]"
                  animate={{
                    opacity: [0.8, 1, 0.8],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                >
                  ★ Haz clic para abrir ★
                </motion.span>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </motion.button>

      {/* Beneficios lado derecho */}
      <PackBenefits side="right" />
    </motion.div>
  )
}
