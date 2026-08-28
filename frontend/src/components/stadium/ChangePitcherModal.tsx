import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PlayerData } from '../../types/stadium';

interface ChangePitcherModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPitcher: PlayerData | null;
  availablePitchers: PlayerData[];
  onConfirm: (newPitcherId: string) => Promise<void>;
  isLoading?: boolean;
}

/**
 * Modal para cambiar el lanzador por uno disponible del bullpen
 * - Muestra lanzador actual
 * - Lista de lanzadores disponibles
 * - Selección con preview en tiempo real
 * - Confirmación con cambio en backend
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
            className="fixed inset-0 bg-black/70 z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-auto"
          >
            <div className="bg-[#0F1419]/95 backdrop-blur-md rounded-lg border-2 border-[#C5A059]/50 p-6 shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              {/* Header */}
              <div className="flex justify-between items-center mb-6 pb-4 border-b border-[#C5A059]/30">
                <h2 className="text-2xl font-bold text-[#E6DFD3] font-mono tracking-wide">
                  🔄 CAMBIO DE LANZADOR
                </h2>
                <button
                  onClick={onClose}
                  disabled={isLoading}
                  className="text-[#C5A059] hover:text-[#FFD700] text-2xl font-bold disabled:opacity-50"
                >
                  ✕
                </button>
              </div>

              {/* Current Pitcher */}
              <div className="mb-6">
                <h3 className="text-sm font-mono text-[#C5A059] uppercase mb-3 tracking-wider">
                  Lanzador Actual
                </h3>
                <div className="bg-[#121619] border border-[#C5A059]/30 rounded p-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="text-lg font-bold text-[#E6DFD3]">
                        #{currentPitcher?.number || '-'} {currentPitcher?.name || 'Desconocido'}
                      </div>
                      <div className="text-sm text-[#C5A059]">
                        {currentPitcher?.team || 'N/A'} • {currentPitcher?.rarity || 'COMMON'}
                      </div>
                    </div>
                    <div className="text-4xl font-bold text-[#C5A059]">
                      {currentPitcher?.overall || '-'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Available Pitchers */}
              <div className="mb-6">
                <h3 className="text-sm font-mono text-[#C5A059] uppercase mb-3 tracking-wider">
                  Lanzadores Disponibles ({availablePitchers.length})
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-64 overflow-y-auto">
                  {availablePitchers.length > 0 ? (
                    availablePitchers.map((pitcher) => (
                      <motion.button
                        key={pitcher.id}
                        onClick={() => setSelectedPitcherId(pitcher.id)}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`p-3 rounded border-2 transition-all ${
                          selectedPitcherId === pitcher.id
                            ? 'border-[#FFD700] bg-[#FFD700]/10'
                            : 'border-[#C5A059]/30 bg-[#121619] hover:border-[#C5A059]/60'
                        }`}
                      >
                        <div className="text-left">
                          <div className="flex justify-between items-start mb-1">
                            <div className="font-bold text-[#E6DFD3]">
                              #{pitcher.number} {pitcher.name}
                            </div>
                            <div className="text-2xl font-bold text-[#C5A059]">
                              {pitcher.overall}
                            </div>
                          </div>
                          <div className="text-xs text-[#C5A059]">
                            {pitcher.team} • {pitcher.rarity}
                          </div>
                          {pitcher.stats && pitcher.stats.length > 0 && (
                            <div className="text-xs text-[#A89968] mt-2 flex gap-2">
                              {pitcher.stats.slice(0, 3).map((stat) => (
                                <span key={stat.label}>
                                  {stat.label}: {stat.val}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        {selectedPitcherId === pitcher.id && (
                          <motion.div
                            layoutId="selected-pitcher"
                            className="absolute inset-0 border-2 border-[#FFD700] rounded pointer-events-none"
                          />
                        )}
                      </motion.button>
                    ))
                  ) : (
                    <div className="col-span-2 text-center py-8 text-[#A89968]">
                      No hay lanzadores disponibles en el bullpen
                    </div>
                  )}
                </div>
              </div>

              {/* Error Message */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded text-red-300 text-sm"
                  >
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Actions */}
              <div className="flex gap-3 justify-end">
                <button
                  onClick={onClose}
                  disabled={isLoading}
                  className="px-4 py-2 border border-[#C5A059]/50 text-[#C5A059] rounded hover:bg-[#C5A059]/10 disabled:opacity-50 font-mono font-bold transition-colors"
                >
                  Cancelar
                </button>
                <motion.button
                  onClick={handleConfirm}
                  disabled={isLoading || !selectedPitcherId || selectedPitcherId === currentPitcher?.id}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-6 py-2 bg-[#C5A059] text-[#0F1419] rounded font-mono font-bold hover:bg-[#FFD700] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin">⟳</span>
                      Cambiando...
                    </span>
                  ) : (
                    'Confirmar Cambio'
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

ChangePitcherModal.displayName = 'ChangePitcherModal';

export default ChangePitcherModal;
