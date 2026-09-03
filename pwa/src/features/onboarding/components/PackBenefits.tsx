import { motion } from 'framer-motion'
import { Sparkles, Users, TrendingUp, Award, Star, Trophy } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { memo } from 'react'

interface Benefit {
  icon: LucideIcon
  text: string
}

interface PackBenefitsProps {
  side: 'left' | 'right'
}

const leftBenefits: Benefit[] = [
  { icon: Sparkles, text: '13 Cartas Garantizadas' },
  { icon: Users, text: 'Jugadores Únicos' },
  { icon: TrendingUp, text: 'Mejores Posibilidades' },
]

const rightBenefits: Benefit[] = [
  { icon: Award, text: 'Varias Rarezas' },
  { icon: Star, text: 'Mejora tu Plantilla' },
  { icon: Trophy, text: 'Tu Camino a la Gloria' },
]

export const PackBenefits = memo(function PackBenefits({ side }: PackBenefitsProps) {
  const benefits = side === 'left' ? leftBenefits : rightBenefits

  return (
    <div className="hidden flex-col items-center justify-center gap-8 sm:flex lg:gap-10">
      {benefits.map((benefit, index) => {
        const Icon = benefit.icon
        return (
          <motion.div
            key={benefit.text}
            className="group flex flex-col items-center gap-2 text-center"
            initial={{ opacity: 0, x: side === 'left' ? -30 : 30, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{
              duration: 0.5,
              delay: 0.2 + index * 0.15,
              ease: 'easeOut',
            }}
            whileHover={{ scale: 1.1 }}
          >
            {/* Icono con resplandor */}
            <motion.div
              className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-koshien-gold/60 bg-gradient-to-br from-koshien-gold/20 to-koshien-dark/80 shadow-lg lg:h-14 lg:w-14"
              animate={{
                boxShadow: [
                  '0 0 10px rgba(197, 160, 89, 0.3)',
                  '0 0 20px rgba(197, 160, 89, 0.5)',
                  '0 0 10px rgba(197, 160, 89, 0.3)',
                ],
              }}
              transition={{
                duration: 2.5,
                delay: index * 0.3,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            >
              <Icon className="h-6 w-6 text-koshien-gold lg:h-7 lg:w-7" strokeWidth={2.5} />
            </motion.div>

            {/* Texto del beneficio */}
            <span className="max-w-[120px] font-vintage text-[10px] uppercase leading-tight tracking-wider text-koshien-cream/90 lg:max-w-[140px] lg:text-[11px]">
              {benefit.text}
            </span>
          </motion.div>
        )
      })}
    </div>
  )
})
