import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PlayerData } from '../../types/stadium';

// Extiende PlayerData con el campo de uso previo que viene del backend
interface BullpenPitcher extends PlayerData {
  already_used?: boolean;
}

interface ChangePitcherModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPitcher: PlayerData | null;
  availablePitchers: BullpenPitcher[];
  onConfirm: (newPitcherId: string) => Promise<void>;
  isLoading?: boolean;
}

const RARITY_COLOR: Record<string, string> = {
  DIAMOND: 'text-cyan-300',
  GOLD:    'text-[#FFD700]',
  SILVER:  'text-slate-300',
  BRONZE:  'text-orange-400',
  COMMON:  'text-[#A89968]',
};

/**
 * Modal para cambiar el lanzador por uno disponible del bullpen.
 * Layout: modal ancho con filas compactas — sin scroll en la lista.
 * Los pitchers ya usados en el partido aparecen deshabilitados con badge "YA USADO".
 */
export const ChangePitcherModal: React.FC<ChangePitcherModalProps> = ({
  isOpen,
  onClose,
  currentPitcher,
  availablePitchers,
  onConfirm,
  isLoading = false,
}) => {
  const [selectedPitcherId, setSelectedPitcherId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!selectedPitcherId) {
      setError('Por favor selecciona un lanzador');
      return;
    }
    if (selectedPitcherId === currentPitcher?.id) {
      setError('Debes seleccionar un lanzador diferente');
      return;
    }
    try {
      setError(null);
      await onConfirm(selectedPitcherId);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cambiar lanzador');
    }
  };

  const selectedPitcher = availablePitchers.find(p => p.id === selectedPitcherId);
  const freshCount = availablePitchers.filter(p => !p.already_used).length;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/75 z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 16 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none"
          >
            <div className="pointer-events-auto bg-[#0F1419]/97 backdrop-blur-md rounded-xl border-2 border-[#C5A059]/50 shadow-2xl w-full max-w-3xl">

              {/* ── Header ─────────────────────────────────────────────── */}
              <div className="flex justify-between items-center px-6 py-4 border-b border-[#C5A059]/30">
                <h2 className="text-xl font-bold text-[#E6DFD3] font-mono tracking-wide">
                  🔄 CAMBIO DE LANZADOR
                </h2>
                <button
                  onClick={onClose}
                  disabled={isLoading}
                  className="text-[#C5A059] hover:text-[#FFD700] text-xl font-bold disabled:opacity-50 leading-none"
                >
                  ✕
                </button>
              </div>

              {/* ── Body ───────────────────────────────────────────────── */}
              <div className="flex flex-col md:flex-row gap-0 divide-y md:divide-y-0 md:divide-x divide-[#C5A059]/20">

                {/* Columna izquierda — pitcher actual + preview seleccionado */}
                <div className="md:w-56 flex-shrink-0 px-5 py-4 flex flex-col gap-4">
                  <div>
                    <p className="text-[10px] font-mono text-[#C5A059] uppercase tracking-widest mb-2">
                      En el montículo
                    </p>
                    <PitcherMiniCard pitcher={currentPitcher} dimmed />
                  </div>
                  <div>
                    <p className="text-[10px] font-mono text-[#C5A059] uppercase tracking-widest mb-2">
                      Seleccionado
                    </p>
                    {selectedPitcher ? (
                      <PitcherMiniCard pitcher={selectedPitcher} highlight />
                    ) : (
                      <div className="h-20 flex items-center justify-center rounded border border-dashed border-[#C5A059]/25 text-[#A89968] text-xs font-mono">
                        — elige un pitcher —
                      </div>
                    )}
                  </div>
                </div>

                {/* Columna derecha — bullpen */}
                <div className="flex-1 px-5 py-4 min-h-0">
                  <p className="text-[10px] font-mono text-[#C5A059] uppercase tracking-widest mb-3">
                    Bullpen —{' '}
                    <span className="text-[#E6DFD3]">{freshCount}</span> disponibles
                    {availablePitchers.length > freshCount && (
                      <span className="text-[#A89968]">
                        {' '}· {availablePitchers.length - freshCount} ya usados
                      </span>
                    )}
                  </p>

                  {availablePitchers.length === 0 ? (
                    <div className="flex items-center justify-center h-32 text-[#A89968] text-sm font-mono">
                      No hay relevistas en el bullpen
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {availablePitchers.map((pitcher) => {
                        const isSelected = selectedPitcherId === pitcher.id;
                        const isUsed = !!pitcher.already_used;
                        const rarityClass = RARITY_COLOR[pitcher.rarity || 'COMMON'];
                        const pitchStats = pitcher.stats?.slice(0, 3) ?? [];

                        return (
                          <motion.button
                            key={pitcher.id}
                            onClick={() => !isUsed && setSelectedPitcherId(pitcher.id)}
                            whileTap={isUsed ? {} : { scale: 0.97 }}
                            disabled={isUsed}
                            title={isUsed ? 'Este lanzador ya fue usado en el partido' : undefined}
                            className={`relative text-left px-3 py-2.5 rounded-lg border transition-all duration-150 ${
                              isUsed
                                ? 'border-[#C5A059]/10 bg-[#0C0F12] opacity-45 cursor-not-allowed'
                                : isSelected
                                  ? 'border-[#FFD700] bg-[#FFD700]/10 shadow-[0_0_8px_rgba(255,215,0,0.25)]'
                                  : 'border-[#C5A059]/25 bg-[#121619] hover:border-[#C5A059]/55 hover:bg-[#1A1F24]'
                            }`}
                          >
                            {/* Row 1: nombre + OVR */}
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className={`font-bold text-sm truncate leading-tight ${
                                isUsed ? 'text-[#5A5A5A]' : 'text-[#E6DFD3]'
                              }`}>
                                #{pitcher.number} {pitcher.name}
                              </span>
                              <span className={`text-lg font-black flex-shrink-0 ${
                                isUsed ? 'text-[#4A4A4A]' : isSelected ? 'text-[#FFD700]' : 'text-[#C5A059]'
                              }`}>
                                {pitcher.overall}
                              </span>
                            </div>

                            {/* Row 2: posición + rareza / badge usado */}
                            <div className="flex items-center gap-2 text-[11px] mb-1.5 flex-wrap">
                              <span className={`font-mono font-bold px-1.5 py-0.5 rounded text-[10px] ${
                                isUsed ? 'bg-[#2A2A2A] text-[#555]' : 'bg-[#C5A059]/20 text-[#C5A059]'
                              }`}>
                                {pitcher.position}
                              </span>
                              {isUsed ? (
                                <span className="font-mono text-[10px] text-red-500/70 font-bold tracking-wide">
                                  ✗ YA USADO
                                </span>
                              ) : (
                                <span className={`font-mono ${rarityClass}`}>
                                  {pitcher.rarity}
                                </span>
                              )}
                            </div>

                            {/* Row 3: stats (solo si disponible) */}
                            {!isUsed && pitchStats.length > 0 && (
                              <div className="flex gap-3 text-[10px] text-[#A89968] font-mono">
                                {pitchStats.map(stat => (
                                  <span key={stat.label}>
                                    <span className="text-[#C5A059]/70">{stat.label}</span>{' '}
                                    <span className="text-[#E6DFD3]">{stat.val}</span>
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Checkmark seleccionado */}
                            {isSelected && !isUsed && (
                              <span className="absolute top-2 right-2 text-[#FFD700] text-xs">✔</span>
                            )}
                          </motion.button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Footer ─────────────────────────────────────────────── */}
              <div className="px-6 py-4 border-t border-[#C5A059]/20 flex flex-col sm:flex-row items-center gap-3">
                <AnimatePresence>
                  {error && (
                    <motion.p
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      className="flex-1 text-sm text-red-400 font-mono"
                    >
                      ⚠ {error}
                    </motion.p>
                  )}
                </AnimatePresence>
                <div className="flex gap-3 ml-auto">
                  <button
                    onClick={onClose}
                    disabled={isLoading}
                    className="px-4 py-2 border border-[#C5A059]/50 text-[#C5A059] rounded-lg hover:bg-[#C5A059]/10 disabled:opacity-50 font-mono font-bold text-sm transition-colors"
                  >
                    Cancelar
                  </button>
                  <motion.button
                    onClick={handleConfirm}
                    disabled={isLoading || !selectedPitcherId || selectedPitcherId === currentPitcher?.id}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    className="px-6 py-2 bg-[#C5A059] text-[#0F1419] rounded-lg font-mono font-bold text-sm hover:bg-[#FFD700] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin inline-block">⟳</span>
                        Cambiando...
                      </span>
                    ) : (
                      'Confirmar Cambio'
                    )}
                  </motion.button>
                </div>
              </div>

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

// ── Mini-card compacta para pitcher actual / seleccionado ───────────────────
const PitcherMiniCard: React.FC<{
  pitcher: PlayerData | null;
  highlight?: boolean;
  dimmed?: boolean;
}> = ({ pitcher, highlight = false, dimmed = false }) => {
  if (!pitcher) return null;
  const rarityClass = RARITY_COLOR[pitcher.rarity || 'COMMON'];
  return (
    <div className={`rounded-lg border px-3 py-2.5 ${
      highlight
        ? 'border-[#FFD700] bg-[#FFD700]/10'
        : dimmed
          ? 'border-[#C5A059]/20 bg-[#0C1015]'
          : 'border-[#C5A059]/30 bg-[#121619]'
    }`}>
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className={`font-bold text-sm truncate ${dimmed ? 'text-[#A89968]' : 'text-[#E6DFD3]'}`}>
          #{pitcher.number} {pitcher.name}
        </span>
        <span className={`text-lg font-black flex-shrink-0 ${highlight ? 'text-[#FFD700]' : 'text-[#C5A059]'}`}>
          {pitcher.overall}
        </span>
      </div>
      <div className="flex items-center gap-2 text-[10px]">
        <span className="bg-[#C5A059]/15 text-[#C5A059] font-mono font-bold px-1.5 py-0.5 rounded">
          {pitcher.position}
        </span>
        <span className={`font-mono ${rarityClass}`}>{pitcher.rarity}</span>
      </div>
    </div>
  );
};

ChangePitcherModal.displayName = 'ChangePitcherModal';

export default ChangePitcherModal;
