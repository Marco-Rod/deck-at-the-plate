import React, { useState, useEffect, useRef } from 'react';
import { soundFx } from '../utils/audioManager';
import { user as userApi, games as gamesApi, cards as cardsApi } from '../utils/api';

export const StadiumShowcaseScreen = ({ user, gameSession, onBack }) => {
  const [gameState, setGameState] = useState(gameSession);
  const [selectedZone, setSelectedZone] = useState(5);
  const [selectedPitch, setSelectedPitch] = useState('4-SEAM');
  const [selectedSwing, setSelectedSwing] = useState('NORMAL');

  const [pitcherCard, setPitcherCard] = useState(null);
  const [batterCard, setBatterCard] = useState(null);
  const [lastEventMsg, setLastEventMsg] = useState('¡Juego iniciado!');
  const [userTeam, setUserTeam] = useState(null);
  const [isLineupOpen, setIsLineupOpen] = useState(false);
  const wsRef = useRef(null);

  const stateData = gameState?.state_data || {};
  const isTopInning = gameState?.is_top_inning;

  // Rol actual: En la Alta (Top Inning), la CPU batea y el humano pichea (PITCHER)
  const currentRole = isTopInning ? 'PITCHER' : 'BATTER';

  // 1. Conexión WebSocket para sincronización en tiempo real
  useEffect(() => {
    if (!gameSession?.id || !user?.userId) return;

    const wsUrl = `ws://localhost:8000/ws/games/${gameSession.id}/${user.userId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (['PLAY_RESOLVED', 'INIT_GAME_STATE', 'PITCH_COMMITTED'].includes(data.type)) {
        if (data.description) setLastEventMsg(data.description);
        if (data.message) setLastEventMsg(data.message);

        setGameState((prev) => ({
          ...prev,
          outs: data.outs ?? prev.outs,
          balls: data.balls ?? prev.balls,
          strikes: data.strikes ?? prev.strikes,
          score_home: data.score_home ?? prev.score_home,
          score_away: data.score_away ?? prev.score_away,
          current_inning: data.current_inning ?? prev.current_inning,
          is_top_inning: data.is_top_inning ?? prev.is_top_inning,
          state_data: data.state_data || prev.state_data,
        }));
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [gameSession?.id, user?.userId]);

  // 2. Cargar detalles del equipo local (Usuario)
  useEffect(() => {
    if (!user?.userId) return;
    userApi.getTeam(user.userId).then(setUserTeam).catch(() => null);
  }, [user?.userId]);

  // 3. Cargar las cartas activas (Pitcher y Bateador) desde state_data
  useEffect(() => {
    const activePitcherId = stateData.active_pitcher;
    const activeBatterId = stateData.active_batter;

    if (activePitcherId) {
      cardsApi
        .getCard(activePitcherId)
        .then((card) => {
          setPitcherCard(card);
          if (card?.repertoire && card.repertoire.length > 0) {
            setSelectedPitch(card.repertoire[0].pitch_type);
          }
        })
        .catch(() => null);
    }

    if (activeBatterId) {
      cardsApi
        .getCard(activeBatterId)
        .then((card) => setBatterCard(card))
        .catch(() => null);
    }
  }, [stateData.active_pitcher, stateData.active_batter]);

  const handlePitch = async () => {
    if (soundFx?.playGameStart) soundFx.playGameStart();
    try {
      await gamesApi.pitch(gameSession.id, {
        pitch_type: selectedPitch,
        zone: selectedZone,
      });
      setLastEventMsg(`Picheo enviado: ${selectedPitch} a zona Z${selectedZone}`);
    } catch (err) {
      console.error('Error al pichear:', err);
      setLastEventMsg(`⚠️ Error: ${err.message || 'No se pudo registrar el picheo'}`);
    }
  };

  const handleSwing = async () => {
    if (soundFx?.playGameStart) soundFx.playGameStart();
    try {
      const res = await gamesApi.swing(gameSession.id, {
        swing_type: selectedSwing,
        guessed_zone: selectedZone,
        guessed_pitch: selectedPitch,
      });
      if (res.description) setLastEventMsg(res.description);
    } catch (err) {
      console.error('Error al batear:', err);
      setLastEventMsg(`⚠️ Error: ${err.message || 'No se pudo realizar el swing'}`);
    }
  };

  const runners = stateData.runners || { '1b': null, '2b': null, '3b': null };
  const homeLineupIds = stateData.home_lineup || [];

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 bg-[#121619] text-[#F7F5F0] relative overflow-hidden select-none font-mono">
      
      {/* BARRA SUPERIOR */}
      <header className="w-full flex justify-between items-center border-b-2 border-[#C5A059]/40 pb-3 mb-2 z-20">
        <div className="flex items-center gap-3">
          {userTeam && (
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center font-sports text-sm text-white border border-white/20 shadow"
              style={{ backgroundColor: userTeam.primary_color }}
            >
              {userTeam.short_name}
            </div>
          )}
          <h2 className="font-sports text-2xl text-[#F7F5F0] uppercase tracking-wider leading-none">
            {userTeam ? `${userTeam.name} VS ${gameState.away_user_id || 'CPU'}` : 'PARTIDO EN VIVO'}
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (soundFx?.playClick) soundFx.playClick();
              setIsLineupOpen(!isLineupOpen);
            }}
            className="bg-[#0A0D0F] border border-[#2C3E35] hover:border-[#C5A059] px-3 py-1.5 font-mono text-xs text-[#E6DFD3] flex items-center gap-2 cursor-pointer"
          >
            📋 LINEUPS
          </button>
          <button
            onClick={onBack}
            className="border border-red-500/50 bg-red-950/30 text-red-400 px-3 py-1.5 text-xs font-bold cursor-pointer hover:bg-red-900/50"
          >
            🏳️ SALIR AL LOBBY
          </button>
        </div>
      </header>

      {/* MARCADOR PRINCIPAL */}
      <div className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 px-6 py-2.5 grid grid-cols-3 items-center shadow-2xl mb-2 z-20">
        <div className="flex flex-col justify-center items-start">
          <span className="text-xs text-[#C5A059] font-bold uppercase tracking-wider">
            ENTRADA {gameState.current_inning}° • {isTopInning ? 'ALTA (TOP)' : 'BAJA (BOT)'} • {currentRole === 'PITCHER' ? 'DEFENSA' : 'ATAQUE'}
          </span>
          <span className="text-[10px] text-gray-400 uppercase truncate max-w-xs">
            {lastEventMsg}
          </span>
        </div>

        <div className="text-center mx-auto">
          <div className="font-sports text-3xl md:text-4xl tracking-widest text-[#F7F5F0] flex items-center justify-center gap-3">
            <span style={{ color: userTeam?.primary_color || '#C5A059' }}>
              {userTeam?.short_name || 'HOME'}
            </span>
            <strong className="text-[#C5A059]">{gameState.score_home ?? 0}</strong> -{' '}
            <strong className="text-[#F7F5F0]">{gameState.score_away ?? 0}</strong>
            <span className="text-gray-300">{gameState.away_user_id || 'CPU'}</span>
          </div>
        </div>

        <div className="font-mono text-sm flex gap-4 text-[#E6DFD3] font-bold justify-end items-center">
          <span>B: <strong className="text-[#C5A059]">{gameState.balls ?? 0}</strong></span>
          <span>S: <strong className="text-[#C5A059]">{gameState.strikes ?? 0}</strong></span>
          <span>O: <strong className="text-[#C5A059]">{gameState.outs ?? 0}</strong></span>

          <div className="relative w-7 h-7 flex items-center justify-center ml-2">
            <div className={`absolute top-0 w-2.5 h-2.5 rotate-45 border transition-all ${runners['2b'] ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`} />
            <div className={`absolute left-0 w-2.5 h-2.5 rotate-45 border transition-all ${runners['3b'] ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`} />
            <div className={`absolute right-0 w-2.5 h-2.5 rotate-45 border transition-all ${runners['1b'] ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`} />
          </div>
        </div>
      </div>

      {/* ÁREA CENTRAL */}
      <main className="w-full max-w-6xl mx-auto border-2 border-[#C5A059]/50 p-4 relative flex justify-between items-center min-h-[460px] shadow-2xl bg-[#0A0D0F] rounded z-10">
        
        {/* TARJETA DEL PITCHER */}
        <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl">
          <span className="font-mono text-[10px] text-[#C5A059] font-bold block mb-1">LANZADOR EN LA LOMA</span>

          <div className="relative h-36 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2">
            <img
              src={pitcherCard?.photo || 'https://via.placeholder.com/150/121619/C5A059?text=PITCHER'}
              alt={pitcherCard?.name}
              onError={(e) => {
                e.target.src = 'https://via.placeholder.com/150/121619/C5A059?text=CARD';
              }}
              className="w-full h-full object-cover object-top"
            />
            <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">
              {pitcherCard?.position || 'P'}
            </span>
          </div>

          <h4 className="font-sports text-xl text-white truncate leading-none mb-1">
            {pitcherCard ? pitcherCard.name : 'Cargando...'}
          </h4>
          <span className="text-xs text-gray-400 block mb-2">{pitcherCard?.overall || '--'} OVR</span>

          {currentRole === 'PITCHER' && (
            <div className="space-y-1.5 mt-3 border-t border-[#2C3E35] pt-2">
              <span className="text-[10px] text-[#C5A059] block font-bold">REPERTORIO REAL:</span>
              <div className="grid grid-cols-2 gap-1">
                {pitcherCard?.repertoire && pitcherCard.repertoire.length > 0 ? (
                  pitcherCard.repertoire.map((p) => (
                    <button
                      key={p.pitch_type}
                      type="button"
                      onClick={() => setSelectedPitch(p.pitch_type)}
                      className={`py-1 px-1 text-[9px] font-bold border transition-all cursor-pointer ${
                        selectedPitch === p.pitch_type
                          ? 'bg-[#1A3323] border-[#C5A059] text-[#C5A059] shadow-[0_0_8px_rgba(197,160,89,0.5)]'
                          : 'border-[#2C3E35] text-gray-400 hover:border-gray-500'
                      }`}
                    >
                      {p.pitch_type}
                    </button>
                  ))
                ) : (
                  ['4-SEAM', 'SLIDER', 'CHANGE'].map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setSelectedPitch(p)}
                      className={`py-1 text-[9px] font-bold border ${
                        selectedPitch === p ? 'bg-[#1A3323] border-[#C5A059] text-[#C5A059]' : 'border-[#2C3E35] text-gray-400'
                      }`}
                    >
                      {p}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* GRILLA DE LA STRIKE ZONE */}
        <div className="z-10 flex flex-col items-center gap-2">
          <span className="font-mono text-[10px] text-[#C5A059] uppercase font-bold">
            {currentRole === 'PITCHER'
              ? `UBICACIÓN PICHEO: ZONA Z${selectedZone}`
              : `PREDICCIÓN DE ZONA: ZONA Z${selectedZone}`}
          </span>
          <div className="grid grid-cols-3 gap-2 bg-[#0A0D0F] p-3 border-2 border-[#C5A059] shadow-2xl">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((z) => (
              <button
                key={z}
                onClick={() => setSelectedZone(z)}
                className={`w-16 h-16 border flex items-center justify-center font-mono text-sm cursor-pointer transition-all ${
                  selectedZone === z
                    ? 'border-[#C5A059] bg-[#1A3323] text-[#C5A059] font-bold shadow-[0_0_15px_rgba(197,160,89,0.6)]'
                    : 'border-[#2C3E35] text-gray-300 hover:border-[#C5A059]/60'
                }`}
              >
                Z{z}
              </button>
            ))}
          </div>
        </div>

        {/* TARJETA DEL BATEADOR */}
        <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl">
          <span className="font-mono text-[10px] text-[#C5A059] font-bold block mb-1">BATEADOR EN EL CAJÓN</span>

          <div className="relative h-36 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2">
            <img
              src={batterCard?.photo || 'https://via.placeholder.com/150/121619/C5A059?text=BATTER'}
              alt={batterCard?.name}
              onError={(e) => {
                e.target.src = 'https://via.placeholder.com/150/121619/C5A059?text=CARD';
              }}
              className="w-full h-full object-cover object-top"
            />
            <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">
              {batterCard?.position || 'DH'}
            </span>
          </div>

          <h4 className="font-sports text-xl text-white truncate leading-none mb-1">
            {batterCard ? batterCard.name : 'Cargando...'}
          </h4>
          <span className="text-xs text-gray-400 block mb-2">{batterCard?.overall || '--'} OVR</span>

          {currentRole === 'BATTER' && (
            <div className="space-y-1.5 mt-3 border-t border-[#2C3E35] pt-2">
              <span className="text-[10px] text-[#C5A059] block font-bold">SELECCIONA TIPO DE SWING:</span>
              <div className="grid grid-cols-2 gap-1">
                {['NORMAL', 'POWER', 'TAKE', 'BUNT'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSelectedSwing(s)}
                    className={`py-1 text-[9px] font-bold border transition-all cursor-pointer ${
                      selectedSwing === s ? 'bg-[#1A3323] border-[#C5A059] text-[#C5A059]' : 'border-[#2C3E35] text-gray-400'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

      </main>

      {/* DOCK INFERIOR DE ACCIÓN */}
      <footer className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 p-3 flex justify-between items-center mt-2 shadow-2xl z-20">
        <div className="text-xs text-gray-400">
          <span>
            Rival Activo: <strong className="text-[#C5A059]">CPU ({gameState.away_user_id || 'BOT'})</strong>
          </span>
        </div>

        <button
          onClick={currentRole === 'PITCHER' ? handlePitch : handleSwing}
          className="bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] px-10 py-3 font-sports text-3xl text-[#C5A059] tracking-widest shadow-xl cursor-pointer active:scale-95 transition-all uppercase"
        >
          {currentRole === 'PITCHER' ? 'LANZAR ⚾' : 'BATEAR 💥'}
        </button>
      </footer>

      {/* DRAWER DE LINEUPS */}
      {isLineupOpen && (
        <div className="fixed inset-0 bg-[#0A0D0F]/85 backdrop-blur-sm z-50 flex justify-end">
          <div className="bg-[#121619] border-l-2 border-[#C5A059] w-full max-w-sm p-5 flex flex-col justify-between shadow-2xl">
            <div>
              <div className="flex justify-between items-center border-b border-[#2C3E35] pb-3 mb-4">
                <h3 className="font-sports text-2xl text-[#F7F5F0] uppercase">📋 ALINEACIÓN LOCAL</h3>
                <button onClick={() => setIsLineupOpen(false)} className="text-[#C5A059] font-mono text-xl cursor-pointer">
                  ✕
                </button>
              </div>

              <div className="space-y-2 font-mono text-xs max-h-[60vh] overflow-y-auto pr-1">
                {homeLineupIds.map((cardId, idx) => (
                  <div key={cardId || idx} className="p-2 border border-[#2C3E35] bg-[#0A0D0F] flex justify-between items-center">
                    <span className="text-[#C5A059] font-bold">#{idx + 1}</span>
                    <span className="text-white text-xs truncate max-w-[180px]">{cardId}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => setIsLineupOpen(false)}
              className="w-full bg-[#1A3323] border border-[#C5A059] py-2.5 font-mono text-xs text-[#F7F5F0] mt-4 cursor-pointer uppercase font-bold"
            >
              CERRAR PANORÁMICA
            </button>
          </div>
        </div>
      )}

    </div>
  );
};