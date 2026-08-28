import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface PitcherInfo {
  id: string;
  name: string;
  number: string;
  overall: number;
  position: string;
  team: string;
  rarity: string;
}

interface RivalPitcherChangeModalProps {
  isOpen: boolean;
  oldPitcher: PitcherInfo | null;
  newPitcher: PitcherInfo | null;
  onAccept: () => void;
}

/**
 * RivalPitcherChangeModal
 * Notifica al usuario cuando el rival ha hecho un cambio de pitcher
 * Muestra:
 * - Nombre del pitcher que salió (con Overall)
 * - Nombre del pitcher que entra (con Overall)
 * - Botón para aceptar y continuar
 * 
 * @component
 * @example
 * <RivalPitcherChangeModal
 *   isOpen={true}
 *   oldPitcher={{ id: 'c1', name: 'Clayton Kershaw', number: '22', overall: 94, ... }}
 *   newPitcher={{ id: 'c2', name: 'Walker Buehler', number: '6', overall: 89, ... }}
 *   onAccept={() => console.log('Aceptado')}
 * />
 */
export const RivalPitcherChangeModal: React.FC<RivalPitcherChangeModalProps> = ({
  isOpen,
  oldPitcher,
  newPitcher,
  onAccept,
}) => {
  if (!oldPitcher || !newPitcher) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay oscuro */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={onAccept}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none"
          >
            <div className="bg-gradient-to-br from-[#1a1d23] via-[#0f1219] to-[#0a0d0f] border-2 border-[#C5A059]/60 rounded-lg shadow-2xl p-6 sm:p-8 md:p-10 max-w-lg w-full mx-4 pointer-events-auto">
              {/* Header */}
              <div className="text-center mb-6">
                <h2 className="text-lg sm:text-xl md:text-2xl font-mono font-bold text-[#C5A059] uppercase tracking-wider mb-2">
                  🔄 Cambio de Lanzador
                </h2>
                <p className="text-xs sm:text-sm text-[#A89968]">
                  El rival ha realizado un cambio de pitcher
                </p>
              </div>

              {/* Content - Old vs New Pitcher */}
              <div className="space-y-4 mb-8">
                {/* Salida - Old Pitcher */}
                <div className="bg-[#0F1419]/80 border border-[#C5A059]/40 rounded-lg p-4">
                  <div className="text-[10px] sm:text-xs font-mono text-[#A89968] uppercase tracking-widest mb-2">
                    ⬆️ Sale del Montículo
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1">
                      <p className="text-sm sm:text-base font-mono font-bold text-[#F7F5F0] truncate">
                        {oldPitcher.name}
                      </p>
                      <p className="text-[10px] sm:text-xs text-[#A89968]">
                        #{oldPitcher.number} • {oldPitcher.position}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-lg sm:text-2xl font-bold font-sports text-[#C5A059]">
                        {oldPitcher.overall}
                      </div>
                      <div className="text-[8px] sm:text-[9px] font-mono text-[#A89968]">
                        OVR
                      </div>
                    </div>
                  </div>
                </div>

                {/* Divider */}
                <div className="flex items-center gap-3 py-1">
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[#C5A059]/30 to-transparent" />
                  <div className="text-[10px] font-mono text-[#A89968] uppercase tracking-widest px-2">
                    Relevo
                  </div>
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-[#C5A059]/30 to-transparent" />
                </div>

                {/* Entrada - New Pitcher */}
                <div className="bg-[#0F1419]/80 border border-[#C5A059]/60 rounded-lg p-4 ring-1 ring-[#C5A059]/20">
                  <div className="text-[10px] sm:text-xs font-mono text-[#C5A059] uppercase tracking-widest mb-2 font-bold">
                    ⬇️ Entra al Montículo
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1">
                      <p className="text-sm sm:text-base font-mono font-bold text-[#C5A059] truncate">
                        {newPitcher.name}
                      </p>
                      <p className="text-[10px] sm:text-xs text-[#A89968]">
                        #{newPitcher.number} • {newPitcher.position}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-lg sm:text-2xl font-bold font-sports text-[#C5A059]">
                        {newPitcher.overall}
                      </div>
                      <div className="text-[8px] sm:text-[9px] font-mono text-[#A89968]">
                        OVR
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Rarity Badge */}
              <div className="flex justify-center mb-6">
                <div className="text-[10px] sm:text-xs font-mono font-bold uppercase tracking-wider px-3 py-1 rounded border"
                  style={{
                    borderColor: newPitcher.rarity === 'DIAMOND' ? '#4A90E2' : 
                                 newPitcher.rarity === 'GOLD' ? '#FFD700' :
                                 newPitcher.rarity === 'SILVER' ? '#C0C0C0' :
                                 newPitcher.rarity === 'BRONZE' ? '#CD7F32' : '#A89968',
                    color: newPitcher.rarity === 'DIAMOND' ? '#4A90E2' : 
                           newPitcher.rarity === 'GOLD' ? '#FFD700' :
                           newPitcher.rarity === 'SILVER' ? '#C0C0C0' :
                           newPitcher.rarity === 'BRONZE' ? '#CD7F32' : '#A89968',
                  }}>
                  {newPitcher.rarity}
                </div>
              </div>

              {/* Accept Button */}
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onAccept}
                className="w-full bg-gradient-to-r from-[#C5A059] to-[#D4AF7A] hover:from-[#D4AF7A] hover:to-[#E8C497] text-[#0A0D0F] font-mono font-bold uppercase tracking-wider py-2.5 sm:py-3 md:py-3.5 rounded transition-all duration-200 text-sm sm:text-base"
              >
                Entendido, Continuar
              </motion.button>

              {/* Subtitle */}
              <p className="text-center text-[8px] sm:text-[9px] text-[#A89968] mt-3 uppercase tracking-widest">
                El nuevo pitcher comienza con 0 lanzamientos
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

RivalPitcherChangeModal.displayName = 'RivalPitcherChangeModal';
