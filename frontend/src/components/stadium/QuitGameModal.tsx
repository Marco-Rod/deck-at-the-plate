import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface QuitGameModalProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

/**
 * Modal de confirmación para finalizar el partido.
 * Permite al usuario salir del juego actual y regresar al lobby.
 */
export const QuitGameModal: React.FC<QuitGameModalProps> = ({
  isOpen,
  onConfirm,
  onCancel,
  isLoading = false,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onCancel}
            className="fixed inset-0 bg-black/75 z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none"
          >
            <div className="pointer-events-auto bg-[#0F1419]/97 backdrop-blur-md rounded-xl border-2 border-[#C5A059]/50 shadow-2xl w-full max-w-md">
              {/* Header */}
              <div className="flex justify-between items-center px-6 py-4 border-b border-[#C5A059]/30">
                <h2 className="text-xl font-bold text-[#E6DFD3] font-mono tracking-wide">
                  ⚠️ FINALIZAR PARTIDO
                </h2>
              </div>

              {/* Content */}
              <div className="px-6 py-6">
                <p className="text-sm text-[#E6DFD3] mb-4 leading-relaxed">
                  ¿Estás seguro que deseas finalizar el partido actual?
                </p>
                <p className="text-xs text-[#A89968] font-mono">
                  Se cerrará la conexión con el servidor y regresarás al lobby.
                </p>
              </div>

              {/* Footer */}
              <div className="px-6 py-4 border-t border-[#C5A059]/20 flex gap-3 justify-end">
                <button
                  onClick={onCancel}
                  disabled={isLoading}
                  className="px-4 py-2 border border-[#C5A059]/50 text-[#C5A059] rounded-lg hover:bg-[#C5A059]/10 disabled:opacity-50 font-mono font-bold text-sm transition-colors"
                >
                  Cancelar
                </button>
                <motion.button
                  onClick={onConfirm}
                  disabled={isLoading}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg font-mono font-bold text-sm hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin inline-block">⟳</span>
                      Finalizando...
                    </span>
                  ) : (
                    'Finalizar Partido'
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

QuitGameModal.displayName = 'QuitGameModal';

export default QuitGameModal;
