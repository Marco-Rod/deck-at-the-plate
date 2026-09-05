import { useMemo, useState, useEffect, memo } from 'react'
import { motion } from 'framer-motion'

/**
 * Hook personalizado para determinar el número de partículas según viewport
 */
function useParticleCount(): number {
  const [count, setCount] = useState(() => {
    if (typeof window === 'undefined') return 10
    const width = window.innerWidth
    if (width >= 1024) return 35 // Desktop
    if (width >= 768) return 18 // Tablet
    return 10 // Mobile
  })

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth
      if (width >= 1024) setCount(35)
      else if (width >= 768) setCount(18)
      else setCount(10)
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return count
}

interface Particle {
  id: number
  left: string
  top: string
  delay: number
  duration: number
  size: number
  opacity: number
  blur: boolean
}

function pseudoRandom(seed: number): number {
  const value = Math.sin(seed * 12.9898) * 43758.5453
  return value - Math.floor(value)
}

export const FloatingParticles = memo(function FloatingParticles() {
  const particleCount = useParticleCount()

  const particles = useMemo<Particle[]>(() => {
    return Array.from({ length: particleCount }, (_, i) => ({
      id: i,
      left: `${pseudoRandom(i + 1) * 100}%`,
      top: `${pseudoRandom(i + 11) * 100}%`,
      delay: pseudoRandom(i + 23) * 3,
      duration: 3 + pseudoRandom(i + 37) * 4, // 3-7 segundos
      size: 2 + pseudoRandom(i + 41) * 4, // 2-6px
      opacity: 0.2 + pseudoRandom(i + 53) * 0.6, // 0.2-0.8
      blur: pseudoRandom(i + 67) > 0.6, // 40% con blur para profundidad
    }))
  }, [particleCount])

  return (
    <div 
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
      aria-hidden="true"
    >
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          className="particle absolute rounded-full"
          style={{
            left: particle.left,
            top: particle.top,
            width: particle.size,
            height: particle.size,
            backgroundColor: '#d4af37',
            opacity: particle.opacity,
            boxShadow: '0 0 4px rgba(212, 175, 55, 0.8)',
            filter: particle.blur ? 'blur(1px)' : 'none',
          }}
          animate={{
            y: [-20, 20, -20],
            x: [-10, 10, -10],
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: particle.duration,
            delay: particle.delay,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  )
})
