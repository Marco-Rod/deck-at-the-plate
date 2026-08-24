import React, { useState, useEffect } from 'react';
import { soundFx } from '../utils/audioManager';
import { user as userApi, games as gamesApi } from '../utils/api';

export const RosterSelectionScreen = ({ user, gameConfig, onRosterConfirmed, onBack }) => {
  const [activeLineup, setActiveLineup] = useState({});
  const [loading, setLoading] = useState(true);
  const [creatingGame, setCreatingGame] = useState(false);
  const [error, setError] = useState(null);

  // Cargar la alineación activa del usuario desde la base de datos
  useEffect(() => {
    if (!user?.userId) return;

    setLoading(true);
    userApi.getLineup(user.userId)
      .then(data => {
        if (data && data.slots) {
          setActiveLineup(data.slots);
        }
      })
      .catch(err => {
        console.error("Error al cargar la alineación:", err);
        setError("No se pudo cargar la alineación activa.");
      })
      .finally(() => setLoading(false));
  }, [user?.userId]);

  const handleConfirmAndPlay = async () => {
    if (soundFx?.playGameStart) soundFx.playGameStart();
    setCreatingGame(true);
    setError(null);

    try {
      // Extraer IDs de bateadores en orden
      const homeLineupIds = ['DH', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'C']
        .map(pos => activeLineup[pos]?.id)
        .filter(Boolean);

      const homePitcherId = activeLineup['P']?.id;

      if (!homePitcherId || homeLineupIds.length < 9) {
        throw new Error("Alineación incompleta. Por favor, asigna 9 bateadores y 1 pitcher en 'Gestionar Mi Equipo'.");
      }

      // Invocar la API para crear la partida en PostgreSQL
      const gameSession = await gamesApi.create({
        home_user_id: user.userId,
        away_user_id: gameConfig?.rival?.id || 'JAL',
        game_mode: gameConfig?.mode || 'PVE',
        difficulty: gameConfig?.difficulty || 'MEDIUM',
        home_pitcher_id: homePitcherId,
        away_pitcher_id: homePitcherId, // Se asignará automáticamente en el backend para la CPU
        home_lineup: homeLineupIds,
        away_lineup: homeLineupIds,     // Se generará en el backend
        home_tactics_deck: ["t1", "t2", "t3", "t4", "t1"],
        away_tactics_deck: ["t1", "t2", "t3", "t4", "t1"],
      });

      // Pasar el ID real de la partida a App.jsx para cambiar a la vista STADIUM
      onRosterConfirmed(gameSession.id);

    } catch (err) {
      console.error("Error al crear la partida:", err);
      setError(err.message || "Error al conectar con el servidor.");
      setCreatingGame(false);
    }
  };

  const pitcher = activeLineup['P'];

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-6 bg-[#121619] text-[#F7F5F0] font-mono select-none">
      
      {/* HEADER */}
      <div className="w-full flex justify-between items-center border-b-2 border-[#C5A059] pb-3 mb-4">
        <div>
          <span className="text-xs text-[#C5A059] uppercase block tracking-widest">
            MATCHMAKING • CONFIRMACIÓN DE ROSTER
          </span>
          <h2 className="font-sports text-4xl uppercase text-white leading-none mt-1">
            PREPARAR ENCUENTRO VS {gameConfig?.rival?.name || 'CPU'}
          </h2>
        </div>

        <button
          onClick={onBack}
          disabled={creatingGame}
          className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#0A0D0F] px-5 py-3 text-xs text-[#F7F5F0] transition-colors cursor-pointer"
        >
          VOLVER AL LOBBY
        </button>
      </div>

      {/* ÁREA DE CONFIRMACIÓN */}
      <div className="max-w-4xl mx-auto w-full my-auto grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* MI EQUIPO (HOME) */}
        <div className="bg-[#0A0D0F] border-2 border-[#C5A059] p-5 rounded shadow-2xl flex flex-col justify-between">
          <div>
            <span className="text-xs text-[#C5A059] uppercase block mb-1">EQUIPO LOCAL (TÚ)</span>
            <h3 className="font-sports text-3xl text-white uppercase border-b border-[#2C3E35] pb-2 mb-4">
              MI ALINEACIÓN
            </h3>

            {loading ? (
              <p className="text-xs text-gray-400 py-6 text-center">Cargando alineación...</p>
            ) : (
              <div className="space-y-2 text-xs">
                <div className="bg-[#121619] p-2.5 border border-[#C5A059]/50 flex justify-between items-center rounded">
                  <span className="text-[#C5A059] font-bold">⚾ PITCHER TITULAR:</span>
                  <span className="text-white font-sports text-base">{pitcher ? pitcher.name : 'SIN ASIGNAR'} ({pitcher?.overall || '--'} OVR)</span>
                </div>

                <div className="bg-[#121619] p-3 border border-[#2C3E35] rounded space-y-1 max-h-48 overflow-y-auto">
                  <span className="text-[10px] text-gray-400 block uppercase mb-1">ORDEN AL BATE (9 TITULARES)</span>
                  {['DH', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'C'].map((pos, idx) => {
                    const card = activeLineup[pos];
                    return (
                      <div key={pos} className="flex justify-between items-center text-[11px] border-b border-[#2C3E35]/40 py-1">
                        <span className="text-gray-400">#{idx + 1} {pos}</span>
                        <span className="text-white font-bold">{card ? card.name : 'VACÍO'}</span>
                        <span className="text-[#C5A059]">{card ? `${card.overall} OVR` : '--'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIVAL CPU (AWAY) */}
        <div className="bg-[#0A0D0F] border-2 border-[#2C3E35] p-5 rounded shadow-2xl flex flex-col justify-between">
          <div>
            <span className="text-xs text-gray-400 uppercase block mb-1">EQUIPO VISITANTE</span>
            <h3 className="font-sports text-3xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              {gameConfig?.rival?.name || 'CHARROS'} ({gameConfig?.rival?.city || 'JALISCO'})
            </h3>

            <div className="bg-[#121619] p-4 border border-[#2C3E35] rounded text-center space-y-3">
              <div 
                className="w-20 h-20 rounded-full mx-auto flex items-center justify-center font-sports text-3xl text-white border-2 border-white/20 shadow-xl"
                style={{ backgroundColor: gameConfig?.rival?.color || '#002B66' }}
              >
                {gameConfig?.rival?.badge || 'JAL'}
              </div>

              <div>
                <span className="text-xs text-gray-400 block font-mono">FRANQUICIA CPU</span>
                <h4 className="font-sports text-2xl text-white">{gameConfig?.rival?.name}</h4>
              </div>

              <div className="flex justify-center gap-4 text-xs font-mono pt-2 border-t border-[#2C3E35]">
                <div>
                  <span className="text-gray-400 block text-[9px]">OVERALL</span>
                  <span className="text-[#C5A059] font-bold text-lg font-sports">{gameConfig?.rival?.ovr || 80}</span>
                </div>
                <div>
                  <span className="text-gray-400 block text-[9px]">DIFICULTAD</span>
                  <span className="text-[#C5A059] font-bold text-lg font-sports">{gameConfig?.difficulty || 'MEDIUM'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* MENSAJE DE ERROR */}
      {error && (
        <div className="max-w-xl mx-auto w-full bg-red-950/80 border border-red-500 p-3 rounded text-center text-red-300 text-xs mb-3 font-mono">
          ⚠️ {error}
        </div>
      )}

      {/* BOTÓN INICIAR PARTIDO */}
      <div className="max-w-md mx-auto w-full">
        <button
          onClick={handleConfirmAndPlay}
          disabled={creatingGame || loading}
          className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#C5A059] py-4 font-sports text-3xl tracking-widest transition-all active:scale-95 shadow-2xl cursor-pointer disabled:opacity-50 uppercase"
        >
          {creatingGame ? 'CARGANDO ESTADIO...' : '⚡ ENTRAR AL CAMPO DE JUEGO'}
        </button>
      </div>

      <div className="text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-4">
        KOSHIEN MATCHMAKING ENGINE • 2026
      </div>
    </div>
  );
};