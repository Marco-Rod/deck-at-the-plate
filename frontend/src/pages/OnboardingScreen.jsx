import React, { useState, useMemo } from 'react';
import { shop } from '../utils/api';
import { PlayerCard } from '../components/cards/PlayerCard';

const TEAMS = [
  {
    id: 'LAD',
    name: 'Los Angeles Dodgers',
    city: 'Los Angeles',
    color: '#005A9C',
    badge: 'LAD',
  },
  {
    id: 'NYY',
    name: 'New York Yankees',
    city: 'New York',
    color: '#0C2340',
    badge: 'NYY',
  },
];

const RARITY_WEIGHTS = {
  DIAMOND: 4,
  GOLD: 3,
  SILVER: 2,
  BRONZE: 1,
  COMMON: 0,
};

export default function OnboardingScreen({ userId, onComplete }) {
  const [step, setStep] = useState('SELECT_TEAM'); // 'SELECT_TEAM' | 'PACK_UNBOX' | 'SHOW_CARDS'
  const [selectedTeam, setSelectedTeam] = useState('LAD');
  const [loading, setLoading] = useState(false);
  const [claimedCards, setClaimedCards] = useState([]);
  const [error, setError] = useState(null);
  
  // Estado para controlar la tarjeta seleccionada y mostrar el modal
  const [selectedCard, setSelectedCard] = useState(null);

  const handleConfirmTeam = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await shop.claimStarterPack(userId, selectedTeam);
      setClaimedCards(response.cards || []);
      setStep('PACK_UNBOX');
    } catch (err) {
      setError(err.message || 'Error al asignar el sobre inicial.');
    } finally {
      setLoading(false);
    }
  };

  // Ordenamiento Jerárquico: 1º Rareza (Descendente) -> 2º Overall (Descendente)
  const sortedCards = useMemo(() => {
    return [...claimedCards].sort((a, b) => {
      const rarityA = RARITY_WEIGHTS[a.rarity?.toUpperCase()] ?? 0;
      const rarityB = RARITY_WEIGHTS[b.rarity?.toUpperCase()] ?? 0;

      if (rarityB !== rarityA) {
        return rarityB - rarityA;
      }
      return (b.overall || 0) - (a.overall || 0);
    });
  }, [claimedCards]);

  return (
    <div className="min-h-screen bg-[#0A0D0F] text-[#E6DFD3] flex flex-col items-center justify-center p-6 font-mono select-none">
      
      {/* PASO 1: SELECCIÓN DE FRANQUICIA */}
      {step === 'SELECT_TEAM' && (
        <div className="max-w-xl w-full border-2 border-[#C5A059]/50 p-8 bg-[#121619] shadow-2xl text-center">
          <span className="text-xs text-[#C5A059] uppercase tracking-widest block mb-2">
            ★ Funda tu Club ★
          </span>
          <h2 className="text-3xl font-extrabold text-white uppercase tracking-wider mb-6 font-sports">
            Selecciona tu Franquicia
          </h2>

          <div className="grid grid-cols-2 gap-4 mb-8">
            {TEAMS.map((team) => (
              <button
                key={team.id}
                type="button"
                onClick={() => setSelectedTeam(team.id)}
                className={`p-6 border-2 transition-all flex flex-col items-center gap-3 cursor-pointer ${
                  selectedTeam === team.id
                    ? 'border-[#C5A059] bg-[#1A2228] scale-105 shadow-[0_0_20px_rgba(197,160,89,0.3)]'
                    : 'border-[#2C3E35] bg-[#0A0D0F] opacity-60 hover:opacity-100'
                }`}
              >
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white border border-white/20 shadow-inner font-sports"
                  style={{ backgroundColor: team.color }}
                >
                  {team.badge}
                </div>
                <span className="font-bold text-sm text-white">{team.name}</span>
              </button>
            ))}
          </div>

          {error && <p className="text-red-400 text-xs mb-4">{error}</p>}

          <button
            type="button"
            disabled={loading}
            onClick={handleConfirmTeam}
            className="w-full py-4 bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#F7F5F0] font-sports text-2xl tracking-widest uppercase transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Asignando Mazo...' : 'Confirmar y Reclamar Sobre'}
          </button>
        </div>
      )}

      {/* PASO 2: ANIMACIÓN INTERACTIVA DEL SOBRE */}
      {step === 'PACK_UNBOX' && (
        <div className="text-center flex flex-col items-center justify-center gap-4">
          <span className="text-xs text-[#C5A059] uppercase tracking-widest">
            ¡Bienvenido a la Liga!
          </span>
          <h2 className="text-3xl font-extrabold text-white uppercase tracking-wide font-sports">
            Sobre de Bienvenida Concedido
          </h2>

          <button
            type="button"
            onClick={() => setStep('SHOW_CARDS')}
            className="group relative cursor-pointer my-6 transition-transform hover:scale-105 active:scale-95"
          >
            <div className="w-64 h-96 bg-gradient-to-br from-[#C5A059] via-[#8A6D3B] to-[#423318] border-4 border-[#F7F5F0] rounded-xl flex flex-col items-center justify-between p-6 shadow-[0_0_50px_rgba(197,160,89,0.5)] relative overflow-hidden">
              <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
              <span className="text-[10px] font-bold uppercase text-[#121619] tracking-widest bg-white/90 px-2 py-0.5 rounded shadow">
                Starter Pack
              </span>
              <div className="text-6xl my-auto animate-bounce">⚾</div>
              <div className="text-center">
                <span className="text-2xl font-black text-white block font-sports tracking-wider">25 CARTAS</span>
                <span className="text-[10px] text-[#F7F5F0] uppercase tracking-widest block mt-1">
                  Haz clic para abrir
                </span>
              </div>
            </div>
          </button>
        </div>
      )}

      {/* PASO 3: REVELACIÓN DEL MAZO ORDENADO */}
      {step === 'SHOW_CARDS' && (
        <div className="w-full max-w-6xl flex flex-col items-center gap-6">
          <div className="text-center">
            <h2 className="text-2xl font-extrabold text-[#C5A059] uppercase tracking-wider font-sports">
              ¡Mazo Inicial Desbloqueado!
            </h2>
            <p className="text-xs text-gray-400 mt-1 font-mono">
              Haz clic en cualquier carta para ver sus atributos detallados.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 w-full max-h-[60vh] overflow-y-auto p-4 border border-[#2C3E35] bg-[#121619]/90 rounded shadow-inner">
            {sortedCards.map((card) => (
              <div
                key={card.id || card.card_id}
                onClick={() => setSelectedCard(card)}
                className="scale-90 origin-top cursor-pointer transition-transform hover:scale-95"
              >
                <PlayerCard card={card} player={card} cardData={card} />
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={onComplete}
            className="px-8 py-4 bg-[#C5A059] text-[#121619] font-bold tracking-widest uppercase hover:bg-[#d4b06a] transition-all shadow-lg cursor-pointer font-sports text-xl"
          >
            Ir al Menú Principal
          </button>
        </div>
      )}

      {/* MODAL DE DETALLE DE CARTA */}
      {selectedCard && (
        <div
          onClick={() => setSelectedCard(null)}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-[#121619] border-2 border-[#C5A059] p-6 max-w-md w-full shadow-[0_0_50px_rgba(197,160,89,0.3)] relative flex flex-col items-center gap-4"
          >
            {/* Botón cerrar */}
            <button
              type="button"
              onClick={() => setSelectedCard(null)}
              className="absolute top-3 right-3 text-gray-400 hover:text-white font-bold text-lg cursor-pointer"
            >
              ✕
            </button>

            <span className="text-xs text-[#C5A059] uppercase tracking-widest font-mono">
              ★ Detalle del Atleta ★
            </span>

            {/* Carta en tamaño grande */}
            <div className="scale-110 my-2">
              <PlayerCard card={selectedCard} player={selectedCard} cardData={selectedCard} />
            </div>

            {/* Información y Atributos detallados */}
            <div className="w-full bg-[#0A0D0F] border border-[#2C3E35] p-4 text-xs font-mono space-y-2 mt-2">
              <div className="flex justify-between border-b border-[#2C3E35] pb-1">
                <span className="text-gray-400">POSICIÓN:</span>
                <span className="text-white font-bold">{selectedCard.position}</span>
              </div>
              <div className="flex justify-between border-b border-[#2C3E35] pb-1">
                <span className="text-gray-400">RAREZA:</span>
                <span className="text-[#C5A059] font-bold">{selectedCard.rarity}</span>
              </div>
              <div className="flex justify-between border-b border-[#2C3E35] pb-1">
                <span className="text-gray-400">EQUIPO:</span>
                <span className="text-white font-bold">{selectedCard.team_id}</span>
              </div>

              {/* Atributos de Bateo */}
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div className="bg-[#121619] p-2 border border-[#2C3E35]">
                  <span className="text-gray-400 block text-[10px]">PODER (PWR)</span>
                  <span className="text-white font-bold text-sm">{selectedCard.power ?? '--'}</span>
                </div>
                <div className="bg-[#121619] p-2 border border-[#2C3E35]">
                  <span className="text-gray-400 block text-[10px]">CONTACTO (CON)</span>
                  <span className="text-white font-bold text-sm">{selectedCard.contact ?? '--'}</span>
                </div>
              </div>

              {/* Atributos de Picheo (si aplica) */}
              {(selectedCard.position === 'SP' || selectedCard.position === 'RP' || selectedCard.position === 'CP' || selectedCard.is_two_way) && (
                <>
                  <div className="grid grid-cols-3 gap-2 pt-1">
                    <div className="bg-[#121619] p-2 border border-[#2C3E35]">
                      <span className="text-gray-400 block text-[10px]">VELOCIDAD</span>
                      <span className="text-white font-bold text-sm">{selectedCard.velocity ?? '--'}</span>
                    </div>
                    <div className="bg-[#121619] p-2 border border-[#2C3E35]">
                      <span className="text-gray-400 block text-[10px]">CONTROL</span>
                      <span className="text-white font-bold text-sm">{selectedCard.control ?? '--'}</span>
                    </div>
                    <div className="bg-[#121619] p-2 border border-[#2C3E35]">
                      <span className="text-gray-400 block text-[10px]">MOVIMIENTO</span>
                      <span className="text-white font-bold text-sm">{selectedCard.movement ?? '--'}</span>
                    </div>
                  </div>

                  {/* Repertorio de Pitcheo */}
                  {selectedCard.repertoire && selectedCard.repertoire.length > 0 && (
                    <div className="pt-2">
                      <span className="text-gray-400 block text-[10px] mb-1">REPERTORIO DE LANZAMIENTOS:</span>
                      <div className="space-y-1">
                        {selectedCard.repertoire.map((pitch, idx) => (
                          <div key={idx} className="flex justify-between bg-[#121619] px-2 py-1 text-[11px] border border-[#2C3E35]">
                            <span className="text-[#C5A059] font-bold">{pitch.pitch_type}</span>
                            <span>Vel: {pitch.velocity} | Ctl: {pitch.control} | Mov: {pitch.movement}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            <button
              type="button"
              onClick={() => setSelectedCard(null)}
              className="w-full py-2 bg-[#1A3323] hover:bg-[#2D5A3F] border border-[#C5A059] text-[#F7F5F0] font-sports text-lg uppercase tracking-wider cursor-pointer mt-2"
            >
              Cerrar Detalle
            </button>
          </div>
        </div>
      )}

    </div>
  );
}