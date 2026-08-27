import React, { useState, useMemo, useEffect } from 'react';
import { user as userApi, shop as shopApi } from '../utils/api';
import { PlayerCard } from '../components/cards/PlayerCard';
import { FranchiseCarousel } from '../components/FranchiseCarousel';
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
  const [availableTeams, setAvailableTeams] = useState([]);

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

  // Cargar equipos cuando llegamos a SELECT_FRANCHISE
  useEffect(() => {
    if (step === 'SELECT_FRANCHISE' && availableTeams.length === 0) {
      const loadTeams = async () => {
        try {
          const teams = await userApi.getAvailableTeams();
          setAvailableTeams(teams);
          if (teams.length > 0) {
            setSelectedFranchise(teams[0].id);
          }
        } catch (err) {
          console.error('Error loading teams:', err);
          setError('No se pudieron cargar los equipos disponibles.');
        }
      };
      loadTeams();
    }
  }, [step, availableTeams.length]);

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
    <div className="min-h-screen text-[#E6DFD3] flex flex-col items-center justify-center p-6 font-mono select-none">
      
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
        <div className="max-w-4xl w-full border-2 border-[#C5A059]/50 p-8 bg-[#121619] shadow-2xl text-center">
          <span className="text-xs text-[#C5A059] uppercase tracking-widest block mb-1">
            ★ Paso 2 de 2 ★
          </span>
          <h2 className="text-3xl font-extrabold text-white uppercase tracking-wider mb-2 font-sports">
            Selecciona tu Franquicia Base
          </h2>
          <p className="text-xs text-gray-400 mb-8">
            Tu club <span className="text-[#C5A059] font-bold">"{teamForm.name}"</span> recibirá 5 jugadores de campo, 2 lanzadores y 6 jugadores aleatorios de otros equipos.
          </p>

          {/* Carrusel Infinito */}
          {availableTeams.length > 0 && (
            <FranchiseCarousel
              teams={availableTeams}
              selectedTeamId={selectedFranchise}
              onSelectTeam={(team) => setSelectedFranchise(team.id)}
            />
          )}

          {error && <p className="text-red-400 text-xs mb-4 mt-6">{error}</p>}

          <button
            type="button"
            disabled={loading}
            onClick={handleClaimStarterPack}
            className="w-full py-4 mt-8 bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#F7F5F0] font-sports text-2xl tracking-widest uppercase transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Asignando Mazo...' : '⚡ Confirmar y Reclamar Sobre'}
          </button>
        </div>
      )}

      {/* PASO 3: ANIMACIÓN INTERACTIVA DEL SOBRE */}
      {step === 'PACK_UNBOX' && (
        <div className="text-center flex flex-col items-center justify-center gap-4 min-h-screen justify-center">
          <span className="text-xs text-[#C5A059] uppercase tracking-widest animate-pulse">
            ¡Bienvenido a la Liga!
          </span>
          <h2 className="text-3xl font-extrabold text-white uppercase tracking-wide font-sports">
            Sobre de Bienvenida Concedido a {teamForm.name || 'tu Club'}
          </h2>

          <button
            type="button"
            onClick={() => {
              if (soundFx?.playPackOpen) soundFx.playPackOpen();
              setStep('SHOW_CARDS');
            }}
            className="group relative cursor-pointer my-6 transition-transform hover:scale-110 active:scale-95"
          >
            {/* Luz de fondo dinámica */}
            <div className="absolute inset-0 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-[#C5A059] via-[#8A6D3B] to-transparent animate-pulse"></div>
            
            {/* Sobre principal */}
            <div className="relative w-64 h-96 bg-gradient-to-br from-[#D4AF37] via-[#C5A059] to-[#8A6D3B] border-4 border-[#F7F5F0] rounded-2xl flex flex-col items-center justify-between p-6 shadow-[0_0_80px_rgba(197,160,89,0.8)] overflow-hidden group-hover:shadow-[0_0_120px_rgba(212,175,55,1)]">
              
              {/* Brillo interior animado */}
              <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-30 transition-opacity duration-300 rounded-2xl" />
              
              {/* Partículas de brillo */}
              <div className="absolute top-2 left-4 w-12 h-12 bg-white/30 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-pulse"></div>
              <div className="absolute bottom-4 right-6 w-16 h-16 bg-[#FFD700]/20 blur-3xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
              
              {/* Borde de brillo superior */}
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              
              <span className="text-[10px] font-black uppercase text-[#1A1A00] tracking-widest bg-gradient-to-r from-white to-yellow-200 px-4 py-1 rounded-full shadow-lg relative z-10">
                Premium Starter Pack
              </span>
              
              {/* Beisbol animado */}
              <div className="text-8xl my-auto relative z-10 group-hover:animate-spin" style={{ animationDuration: '2s' }}>
                ⚾
              </div>
              
              <div className="text-center relative z-10">
                <span className="text-4xl font-black text-white block font-sports tracking-wider drop-shadow-lg">13 CARTAS</span>
                <span className="text-[11px] text-[#F7F5F0] uppercase tracking-widest block mt-2 font-bold drop-shadow">
                  ▶ Haz clic para abrir ◀
                </span>
                <span className="text-[10px] text-yellow-300/80 mt-2 block animate-bounce">CLICK AQUI PARA REVELAR TU DESTINO</span>
              </div>
            </div>
            
            {/* Brillo externo pulsante */}
            <div className="absolute -inset-8 border-2 border-[#C5A059]/0 group-hover:border-[#C5A059]/50 rounded-3xl transition-all duration-500 animate-pulse"></div>
          </button>

          <p className="text-xs text-[#C5A059] animate-pulse mt-4">✨ Presiona el sobre para abrir ✨</p>
        </div>
      )}

      {/* PASO 4: REVELACIÓN DEL MAZO ORDENADO */}
      {step === 'SHOW_CARDS' && (
        <div className="w-full min-h-screen flex flex-col items-center justify-start pt-6 px-4 pb-6">
          <div className="text-center mb-4 flex-shrink-0">
            <h2 className="text-3xl font-extrabold text-[#C5A059] uppercase tracking-wider font-sports drop-shadow-lg">
              ¡Mazo Inicial Desbloqueado!
            </h2>
            <p className="text-xs text-gray-400 mt-2 font-mono">
              🎯 Click para girar • Doble Click para ver detalles • "Revelar Todas" para revelar todo de una vez
            </p>
          </div>

          {/* Botón Revelar Todas */}
          <button
            type="button"
            onClick={() => {
              // Girar solo las cartas que están boca abajo (data-card-flipped="true")
              const cards = document.querySelectorAll('[data-is-card][data-card-flipped="true"]');
              cards.forEach((cardElement, idx) => {
                setTimeout(() => {
                  // Hacer click directamente en el PlayerCard
                  cardElement.click();
                }, idx * 120); // 120ms de stagger entre cada carta
              });
            }}
            className="group relative px-8 py-3 mb-4 flex-shrink-0 bg-gradient-to-r from-[#C5A059] to-[#FFD700] text-[#121619] font-bold tracking-widest uppercase hover:shadow-[0_0_30px_rgba(197,160,89,0.8)] transition-all duration-300 shadow-lg cursor-pointer font-sports text-lg border-2 border-[#F7F5F0] hover:scale-105 active:scale-95"
          >
            <span className="drop-shadow-md">⚡ Revelar Todas las Cartas ⚡</span>
            <div className="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-colors rounded"></div>
          </button>

          {/* Cuadrícula de Cartas - Con scroll suave */}
          <div className="w-full flex-1 flex items-center justify-center px-2 min-h-0">
            <div className="grid gap-3 w-full h-full overflow-y-auto" style={{
              gridTemplateColumns: 'repeat(auto-fill, minmax(165px, 1fr))',
              alignContent: 'start',
              paddingRight: '8px',
            }}>
              {sortedCards.map((card, idx) => (
                <div
                  key={card.id || card.card_id}
                  data-card-flipper
                  onDoubleClick={() => {
                    // Double click abre el modal con detalles
                    setSelectedCard(card);
                  }}
                  role="button"
                  tabIndex={0}
                  className="flex justify-center cursor-pointer select-none h-fit"
                  style={{
                    animationDelay: `${idx * 0.05}s`,
                  }}
                >
                  <PlayerCard card={card} player={card} cardData={card} />
                </div>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={onComplete}
            className="px-8 py-4 mt-6 mb-4 flex-shrink-0 bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#F7F5F0] font-bold tracking-widest uppercase transition-all shadow-lg cursor-pointer font-sports text-xl hover:shadow-[0_0_20px_rgba(197,160,89,0.5)]"
          >
            ➔ Ir al Menú Principal
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
              ★ Detalle Completo del Atleta ★
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