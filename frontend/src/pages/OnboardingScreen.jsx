import React, { useState, useMemo } from 'react';
import { user as userApi, shop as shopApi } from '../utils/api';
import { PlayerCard } from '../components/cards/PlayerCard';
import { soundFx } from '../utils/audioManager';

const PRESET_COLORS = [
  { primary: '#C5A059', secondary: '#1A3323', name: 'Dorado / Verde Tactical' },
  { primary: '#005A9C', secondary: '#FFFFFF', name: 'Azul Real / Blanco' },
  { primary: '#132448', secondary: '#BD3039', name: 'Marina / Rojo' },
  { primary: '#E3D4AD', secondary: '#0C2340', name: 'Crema / Azul Noche' },
];

const FRANCHISES = [
  {
    id: 'LAD',
    name: 'Los Angeles Dodgers',
    city: 'Los Angeles',
    color: '#005A9C',
    badge: 'LAD',
    description: 'Soberbios en Pitcheo & Bateo',
  },
  {
    id: 'NYY',
    name: 'New York Yankees',
    city: 'New York',
    color: '#0C2340',
    badge: 'NYY',
    description: 'Poder Ofensivo Devastador',
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
  // Pasos: 'CREATE_TEAM' -> 'SELECT_FRANCHISE' -> 'PACK_UNBOX' -> 'SHOW_CARDS'
  const [step, setStep] = useState('CREATE_TEAM');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Estado del Formulario de Club
  const [teamForm, setTeamForm] = useState({
    name: '',
    short_name: '',
    city: 'Zapopan',
    stadium_name: 'Estadio Municipal',
    primary_color: '#C5A059',
    secondary_color: '#1A3323',
    logo_id: 'logo_baseball_01',
  });

  const [selectedFranchise, setSelectedFranchise] = useState('LAD');
  const [claimedCards, setClaimedCards] = useState([]);
  const [selectedCard, setSelectedCard] = useState(null);

  // 1. Manejar Creación del Club
  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!teamForm.name || !teamForm.short_name) {
      setError('Por favor ingresa el nombre y las siglas de tu club.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      if (soundFx?.playClick) soundFx.playClick();

      await userApi.createTeam(userId, {
        ...teamForm,
        base_franchise: selectedFranchise,
      });

      setStep('SELECT_FRANCHISE');
    } catch (err) {
      console.error('Error al fundar el club:', err);
      setError(err.message || 'No se pudo crear el club.');
    } finally {
      setLoading(false);
    }
  };

  // 2. Manejar Reclamo de Sobre Inicial
  const handleClaimStarterPack = async () => {
    try {
      setLoading(true);
      setError(null);
      if (soundFx?.playPackOpen) soundFx.playPackOpen();

      const response = await shopApi.claimStarterPack(userId, selectedFranchise);
      setClaimedCards(response.cards || []);
      setStep('PACK_UNBOX');
    } catch (err) {
      console.error('Error al reclamar el sobre:', err);
      setError(err.message || 'Error al obtener el sobre inicial.');
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
      
      {/* PASO 1: FORMULARIO DE FUNDACIÓN DE CLUB */}
      {step === 'CREATE_TEAM' && (
        <div className="max-w-xl w-full border-2 border-[#C5A059]/50 p-8 bg-[#121619] shadow-2xl">
          <div className="text-center mb-6 border-b border-[#2C3E35] pb-4">
            <span className="text-xs text-[#C5A059] uppercase tracking-widest block mb-1">
              ★ Paso 1 de 2 ★
            </span>
            <h2 className="text-3xl font-extrabold text-white uppercase tracking-wider font-sports">
              Funda tu Club de Béisbol
            </h2>
            <p className="text-xs text-gray-400 mt-1">
              Define la identidad de tu franquicia personalizada para competir.
            </p>
          </div>

          {error && <p className="text-red-400 text-xs mb-4 text-center">{error}</p>}

          <form onSubmit={handleCreateTeam} className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="text-[10px] text-[#C5A059] uppercase block mb-1">Nombre del Club</label>
                <input
                  type="text"
                  required
                  placeholder="Ej. Tigres"
                  value={teamForm.name}
                  onChange={(e) => setTeamForm({ ...teamForm, name: e.target.value })}
                  className="w-full bg-[#0A0D0F] border border-[#2C3E35] focus:border-[#C5A059] p-2 text-sm text-white outline-none rounded"
                />
              </div>
              <div>
                <label className="text-[10px] text-[#C5A059] uppercase block mb-1">Siglas (3)</label>
                <input
                  type="text"
                  required
                  maxLength={3}
                  placeholder="TIG"
                  value={teamForm.short_name}
                  onChange={(e) => setTeamForm({ ...teamForm, short_name: e.target.value.toUpperCase() })}
                  className="w-full bg-[#0A0D0F] border border-[#2C3E35] focus:border-[#C5A059] p-2 text-sm text-white uppercase text-center outline-none rounded"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-[#C5A059] uppercase block mb-1">Ciudad / Estado</label>
                <input
                  type="text"
                  value={teamForm.city}
                  onChange={(e) => setTeamForm({ ...teamForm, city: e.target.value })}
                  className="w-full bg-[#0A0D0F] border border-[#2C3E35] focus:border-[#C5A059] p-2 text-sm text-white outline-none rounded"
                />
              </div>
              <div>
                <label className="text-[10px] text-[#C5A059] uppercase block mb-1">Estadio</label>
                <input
                  type="text"
                  value={teamForm.stadium_name}
                  onChange={(e) => setTeamForm({ ...teamForm, stadium_name: e.target.value })}
                  className="w-full bg-[#0A0D0F] border border-[#2C3E35] focus:border-[#C5A059] p-2 text-sm text-white outline-none rounded"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] text-[#C5A059] uppercase block mb-2">Paleta de Colores del Club</label>
              <div className="grid grid-cols-2 gap-2">
                {PRESET_COLORS.map((color, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setTeamForm({
                      ...teamForm,
                      primary_color: color.primary,
                      secondary_color: color.secondary,
                    })}
                    className={`p-2 border flex items-center justify-between text-left rounded transition-all cursor-pointer ${
                      teamForm.primary_color === color.primary
                        ? 'border-[#C5A059] bg-[#1A3323]'
                        : 'border-[#2C3E35] bg-[#0A0D0F]'
                    }`}
                  >
                    <span className="text-[10px] text-gray-300">{color.name}</span>
                    <div className="flex gap-1">
                      <div className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: color.primary }} />
                      <div className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: color.secondary }} />
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#F7F5F0] font-sports text-2xl tracking-widest uppercase transition-all cursor-pointer disabled:opacity-50 py-3"
            >
              {loading ? 'Fundando Club...' : 'Confirmar e Ir a Franquicia ➔'}
            </button>
          </form>
        </div>
      )}

      {/* PASO 2: SELECCIÓN DE FRANQUICIA BASE Y SOBRE */}
      {step === 'SELECT_FRANCHISE' && (
        <div className="max-w-xl w-full border-2 border-[#C5A059]/50 p-8 bg-[#121619] shadow-2xl text-center">
          <span className="text-xs text-[#C5A059] uppercase tracking-widest block mb-1">
            ★ Paso 2 de 2 ★
          </span>
          <h2 className="text-3xl font-extrabold text-white uppercase tracking-wider mb-2 font-sports">
            Selecciona tu Franquicia Base
          </h2>
          <p className="text-xs text-gray-400 mb-6">
            Tu club <span className="text-[#C5A059] font-bold">"{teamForm.name}"</span> recibirá su sobre inicial con jugadores de este equipo.
          </p>

          <div className="grid grid-cols-2 gap-4 mb-6">
            {FRANCHISES.map((team) => (
              <button
                key={team.id}
                type="button"
                onClick={() => setSelectedFranchise(team.id)}
                className={`p-5 border-2 transition-all flex flex-col items-center gap-2 cursor-pointer rounded ${
                  selectedFranchise === team.id
                    ? 'border-[#C5A059] bg-[#1A3323] scale-105 shadow-[0_0_20px_rgba(197,160,89,0.3)]'
                    : 'border-[#2C3E35] bg-[#0A0D0F] opacity-60 hover:opacity-100'
                }`}
              >
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold text-white border border-white/20 shadow-inner font-sports"
                  style={{ backgroundColor: team.color }}
                >
                  {team.badge}
                </div>
                <span className="font-bold text-sm text-white uppercase font-sports">{team.name}</span>
                <span className="text-[10px] text-gray-400">{team.description}</span>
              </button>
            ))}
          </div>

          {error && <p className="text-red-400 text-xs mb-4">{error}</p>}

          <button
            type="button"
            disabled={loading}
            onClick={handleClaimStarterPack}
            className="w-full py-4 bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#F7F5F0] font-sports text-2xl tracking-widest uppercase transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Asignando Mazo...' : '⚡ Confirmar y Reclamar Sobre'}
          </button>
        </div>
      )}

      {/* PASO 3: ANIMACIÓN INTERACTIVA DEL SOBRE */}
      {step === 'PACK_UNBOX' && (
        <div className="text-center flex flex-col items-center justify-center gap-4">
          <span className="text-xs text-[#C5A059] uppercase tracking-widest">
            ¡Bienvenido a la Liga!
          </span>
          <h2 className="text-3xl font-extrabold text-white uppercase tracking-wide font-sports">
            Sobre de Bienvenida Concedido a {teamForm.name || 'tu Club'}
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

      {/* PASO 4: REVELACIÓN DEL MAZO ORDENADO */}
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

            <div className="scale-110 my-2">
              <PlayerCard card={selectedCard} player={selectedCard} cardData={selectedCard} />
            </div>

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