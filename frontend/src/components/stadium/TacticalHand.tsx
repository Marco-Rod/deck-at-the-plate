import React from 'react';
import { motion } from 'framer-motion';
import { TacticalCard, PlayerRole } from '../../types/stadium';

interface TacticalHandProps {
  tacticalHand: TacticalCard[];
  selectedTacticalId: string | null;
  role: PlayerRole;
  isIBB: boolean;
  disabled?: boolean;
  onSelectTactical: (id: string) => void;
  onSubmitPlay: () => void;
}

export const TacticalHand: React.FC<TacticalHandProps> = ({
  tacticalHand,
  selectedTacticalId,
  role,
  isIBB,
  disabled = false,
  onSelectTactical,
  onSubmitPlay,
}) => {
  const buttonLabel = isIBB
    ? 'INTENCIONAL ⚾'
    : role === 'PITCHER'
    ? 'LANZAR 🔥'
    : 'BATEAR 💥';

  return (
    <footer className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 p-3.5 flex flex-col md:flex-row justify-between items-center gap-4 mt-3 shadow-2xl">
      <div className="flex flex-col">
        <span className="font-mono text-xs text-[#C5A059] uppercase font-bold">
          CARTAS TÁCTICAS EN MANO
        </span>
        <span className="font-mono text-[10px] text-[#E6DFD3]/70">
          SELECCIONA PARA ACTIVAR TÁCTICA EN LA JUGADA
        </span>
      </div>

      {/* Baraja de Cartas */}
      <div className="flex gap-3 overflow-x-auto py-1">
        {tacticalHand.map((card) => {
          const isSelected = selectedTacticalId === card.id;
          return (
            <div
              key={card.id}
              onClick={() => !disabled && onSelectTactical(card.id)}
              className={`bg-[#0A0D0F] border-2 ${card.color} ${
                isSelected ? 'ring-2 ring-[#C5A059] -translate-y-2' : ''
              } hover:-translate-y-1 p-3 w-40 text-center transition-all shadow-xl flex flex-col justify-between h-36 ${
                disabled ? 'opacity-40 cursor-not-allowed pointer-events-none' : 'cursor-pointer'
              }`}
            >
              <div>
                <div className="flex justify-between items-center font-mono text-[9px] border-b border-[#2C3E35] pb-1 mb-2">
                  <span className="font-bold">{card.type}</span>
                  <span>⚡{card.cost}</span>
                </div>
                <div className="text-3xl my-1">{card.icon}</div>
                <h5 className="font-sports text-base text-[#F7F5F0] leading-tight uppercase font-bold">
                  {card.name}
                </h5>
              </div>
              <p className="font-mono text-[9px] text-[#E6DFD3] leading-tight mt-1">
                {card.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Botón de Acción Principal con Efecto de Fuego e Incandescencia */}
      <div className="flex flex-col items-center">
        <motion.button
          type="button"
          onClick={onSubmitPlay}
          disabled={disabled}
          className={`relative bg-[#1A100A] border-2 border-orange-500 px-8 py-3.5 font-sports text-3xl text-[#F7F5F0] tracking-widest shadow-2xl rounded-sm overflow-hidden flex items-center gap-3 ${
            disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'
          }`}
          // 1. Pulso de fuego y sombras incandescentes en reposo
          animate={{
            boxShadow: [
              '0 0 15px rgba(239, 68, 68, 0.6), inset 0 0 10px rgba(249, 115, 22, 0.4)',
              '0 0 35px rgba(249, 115, 22, 0.9), inset 0 0 20px rgba(234, 179, 8, 0.7)',
              '0 0 15px rgba(239, 68, 68, 0.6), inset 0 0 10px rgba(249, 115, 22, 0.4)',
            ],
            borderColor: ['#ef4444', '#f97316', '#eab308', '#ef4444'],
            scale: [1, 1.03, 1],
          }}
          transition={{
            duration: 1.8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          // 2. Efecto de vibración rápida y cambio a fuego vivo al pasar el cursor (Hover)
          whileHover={{
            scale: 1.07,
            backgroundColor: '#381404',
            borderColor: '#f97316',
            rotate: [0, -1, 1, -1, 1, 0],
            transition: {
              rotate: { repeat: Infinity, duration: 0.12 },
              scale: { duration: 0.2 },
            },
          }}
          // 3. Feedback táctil al hacer clic (Tap)
          whileTap={{ scale: 0.95 }}
        >
          {/* Partículas de llamas flotando dentro del botón */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden flex items-end justify-center">
            {Array.from({ length: 4 }).map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-4 h-8 rounded-full bg-gradient-to-t from-red-600 via-orange-500 to-yellow-400 opacity-60 blur-[1px]"
                initial={{ y: 15, x: (i - 2) * 20, scale: 0.4, opacity: 0 }}
                animate={{
                  y: [-5, -35, -50],
                  x: [(i - 2) * 20, (i - 2) * 25 + (i % 2 === 0 ? 8 : -8)],
                  scale: [0.4, 1, 0.1],
                  opacity: [0, 0.7, 0],
                }}
                transition={{
                  duration: 1 + (i * 0.2),
                  repeat: Infinity,
                  ease: 'easeOut',
                  delay: i * 0.25,
                }}
              />
            ))}
          </div>

          {/* Destello de luz de fuego interno deslizándose */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-orange-500/30 to-transparent pointer-events-none"
            animate={{ x: ['-100%', '100%'] }}
            transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
          />

          <span className="relative z-10 flex items-center gap-3 text-orange-200 drop-shadow-[0_0_8px_rgba(249,115,22,0.8)]">
            {buttonLabel}
          </span>
        </motion.button>

        <span className="font-mono text-[9px] text-orange-400 uppercase tracking-wider mt-1 font-bold">
          🔥 CONFIRMA LA JUGADA 🔥
        </span>
      </div>
    </footer>
  );
};