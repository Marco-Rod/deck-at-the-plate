import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';
import { user as userApi, teams as teamsApi } from '../utils/api';

export const LobbyScreen = ({ user, onStartGame, onOpenMyTeam, onOpenShowcase, onLogout }) => {
  const { t, i18n } = useTranslation();
  const [gameMode, setGameMode] = useState('PVE');
  const [difficulty, setDifficulty] = useState('EASY');  // ⭐ CHANGED: MEDIUM → EASY
  const [totalInnings, setTotalInnings] = useState(3);    // ⭐ CHANGED: 9 → 3
  const [playerPosition, setPlayerPosition] = useState('HOME');  // ⭐ Already HOME (correct)
  
  const [cpuRivals, setCpuRivals] = useState([]);
  const [rivalIndex, setRivalIndex] = useState(0);
  const [userTeam, setUserTeam] = useState(null);
  const [userStats, setUserStats] = useState({ overall: '--', batOvr: '--', pitOvr: '--' });

  const currentRival = cpuRivals[rivalIndex] || {
    id: 'JAL',
    name: 'Charros',
    city: 'Jalisco',
    color: '#002B66',
    badge: 'JAL',
    desc: 'Cargando rivales...',
    ovr: 80,
    batOvr: 80,
    pitOvr: 80,
  };

  useEffect(() => {
    if (!user?.userId) return;

    // 1. Obtener club del usuario
    userApi.getTeam()
      .then(data => setUserTeam(data))
      .catch(err => console.error('Sin club activo:', err));

    // 2. Obtener métricas calculadas del club del usuario (OVR, BAT, PIT)
    if (userApi.getTeamStats) {
      userApi.getTeamStats()
        .then(stats => {
          if (stats) setUserStats(stats);
        })
        .catch(err => console.error('Error al obtener métricas del usuario:', err));
    }

    // 3. Obtener lista de rivales CPU desde el módulo teams de api.js
    teamsApi.getCpuTeams()
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setCpuRivals(data);
        }
      })
      .catch(err => console.error('Error al cargar equipos CPU:', err));
  }, [user?.userId]);

  const toggleLanguage = () => {
    if (soundFx?.playClick) soundFx.playClick();
    const nextLang = i18n.language === 'es' ? 'en' : 'es';
    i18n.changeLanguage(nextLang);
  };

  const handlePrevRival = () => {
    if (soundFx?.playClick) soundFx.playClick();
    if (cpuRivals.length === 0) return;
    setRivalIndex((prev) => (prev === 0 ? cpuRivals.length - 1 : prev - 1));
  };

  const handleNextRival = () => {
    if (soundFx?.playClick) soundFx.playClick();
    if (cpuRivals.length === 0) return;
    setRivalIndex((prev) => (prev === cpuRivals.length - 1 ? 0 : prev + 1));
  };

  const handleStartGame = () => {
    if (soundFx?.playGameStart) soundFx.playGameStart();
    console.log('[DEBUG-LobbyScreen] handleStartGame llamado con:', {
      mode: gameMode,
      difficulty,
      totalInnings,
      playerPosition,
      rival: currentRival,
      rival_id: currentRival?.id,
      rival_id_undefined: currentRival?.id === undefined,
      rival_id_null: currentRival?.id === null,
      currentRival_complete: JSON.stringify(currentRival)
    });
    onStartGame({
      mode: gameMode,
      difficulty,
      totalInnings,
      playerPosition,  // ⭐ NUEVO: incluir posición elegida
      rival: currentRival
    });
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-2 sm:p-4 md:p-6 font-mono select-none overflow-x-hidden">
      
      {/* NAVBAR SUPERIOR DEL MÁNAGER */}
      <header className="w-full max-w-7xl mx-auto flex flex-col sm:flex-row flex-wrap justify-between items-start sm:items-center bg-[#0A0D0F] border border-[#C5A059] sm:border-2 p-2 sm:p-3 md:p-4 shadow-2xl gap-2 sm:gap-3 md:gap-4 rounded">
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="bg-[#1A3323] border border-[#C5A059] px-2 sm:px-3 py-0.5 sm:py-1 text-center flex-shrink-0">
            <span className="font-sports text-lg sm:text-xl md:text-2xl text-[#C5A059]">LVL 12</span>
          </div>
          <div className="min-w-0">
            <span className="font-mono text-[9px] sm:text-[10px] text-[#C5A059] uppercase block truncate">
              {t('lobby.manager', { defaultValue: 'MÁNAGER' })}
            </span>
            <h2 className="font-sports text-lg sm:text-2xl md:text-3xl text-[#F7F5F0] leading-none uppercase truncate">
              {(user?.username || 'BATEADOR PRO').substring(0, 12)}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          <div className="hidden xs:flex items-center gap-2 bg-[#121619] border border-[#2C3E35] px-2 sm:px-3 py-0.5 sm:py-1.5 font-mono text-[8px] sm:text-[10px] text-[#E6DFD3]">
            <span>RÉCORD: <strong className="text-[#C5A059]">14-5</strong></span>
          </div>

          <button
            type="button"
            onClick={toggleLanguage}
            className="border border-[#C5A059] bg-[#1A3323] hover:bg-[#2D5A3F] px-2 sm:px-3 py-0.5 sm:py-1.5 font-mono text-[9px] sm:text-[10px] text-[#F7F5F0] transition-colors cursor-pointer"
          >
            🌐 {i18n.language === 'es' ? 'EN' : 'ES'}
          </button>

          <button
            type="button"
            onClick={() => { if (soundFx?.playClick) soundFx.playClick(); onLogout(); }}
            className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#0A0D0F] hover:bg-[#121619] px-2 sm:px-3 py-0.5 sm:py-1.5 font-mono text-[9px] sm:text-[10px] text-[#E6DFD3] transition-colors cursor-pointer"
          >
            {t('lobby.logout', { defaultValue: 'SALIR' })}
          </button>
        </div>
      </header>

      {/* ÁREA CENTRAL */}
      <main className="w-full max-w-7xl mx-auto my-auto py-2 sm:py-3 md:py-6 flex flex-col lg:flex-row gap-3 sm:gap-4 md:gap-6 items-stretch">
        
        {/* PANEL IZQUIERDO: PREPARACIÓN DE MI CLUB */}
        <section className="w-full lg:w-5/12 bg-[#0A0D0F] border border-[#2C3E35] sm:border-2 p-3 sm:p-4 md:p-5 flex flex-col justify-between shadow-2xl rounded">
          <div>
            <span className="font-mono text-[9px] sm:text-xs text-[#C5A059] uppercase block mb-1">MI CLUB</span>
            <h3 className="font-sports text-2xl sm:text-3xl text-[#F7F5F0] uppercase border-b border-[#2C3E35] pb-1 sm:pb-2 mb-2 sm:mb-4">
              PREPARACIÓN
            </h3>

            {userTeam ? (
              <div className="bg-[#121619] border border-[#C5A059]/40 p-2 sm:p-3 md:p-4 rounded mb-3 sm:mb-4">
                <div className="flex items-center justify-between gap-2 mb-2 sm:mb-3">
                  <div className="flex items-center gap-2 sm:gap-3 overflow-hidden min-w-0">
                    <div 
                      className="w-12 sm:w-14 h-12 sm:h-14 rounded-full flex items-center justify-center font-sports text-sm sm:text-xl text-white border-2 border-white/20 shadow flex-shrink-0"
                      style={{ backgroundColor: userTeam.primary_color }}
                    >
                      {userTeam.short_name?.substring(0, 2)}
                    </div>
                    <div className="overflow-hidden min-w-0">
                      <span className="text-[8px] sm:text-[10px] text-gray-400 block truncate font-mono">
                        {userTeam.city?.substring(0, 15)}
                      </span>
                      <h4 className="font-sports text-lg sm:text-2xl text-white truncate uppercase">{userTeam.name?.substring(0, 10)}</h4>
                    </div>
                  </div>

                  {/* BADGE DE OVR */}
                  <div className="bg-[#C5A059] text-[#121619] font-sports text-sm sm:text-lg font-extrabold px-1.5 sm:px-2 py-0.5 sm:py-1 rounded shadow border border-white flex-shrink-0">
                    {userStats.overall}
                  </div>
                </div>

                {/* MÉTRICAS */}
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#2C3E35]">
                  <div className="bg-[#0A0D0F] p-1.5 sm:p-2 border border-[#2C3E35] rounded text-center">
                    <span className="text-gray-400 block text-[8px] sm:text-[9px] font-mono">BAT</span>
                    <span className="text-[#C5A059] font-bold font-sports text-base sm:text-xl">{userStats.batOvr}</span>
                  </div>
                  <div className="bg-[#0A0D0F] p-1.5 sm:p-2 border border-[#2C3E35] rounded text-center">
                    <span className="text-gray-400 block text-[8px] sm:text-[9px] font-mono">PIT</span>
                    <span className="text-[#C5A059] font-bold font-sports text-base sm:text-xl">{userStats.pitOvr}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-[#121619] border border-[#2C3E35] p-2 sm:p-3 text-[8px] sm:text-xs text-gray-400 mb-3 sm:mb-4 text-center font-mono">
                Cargando...
              </div>
            )}
          </div>

          <div className="space-y-2 sm:space-y-3 pt-1 sm:pt-2">
            <button
              type="button"
              onClick={() => { if (soundFx?.playClick) soundFx.playClick(); if (onOpenMyTeam) onOpenMyTeam(); }}
              className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] border border-[#C5A059] sm:border-2 py-2 sm:py-3 px-3 sm:px-4 flex items-center justify-between font-sports text-lg sm:text-2xl text-[#F7F5F0] transition-all active:scale-95 shadow-md cursor-pointer"
            >
              <span className="truncate">🛡️ EQUIPO</span>
              <span className="font-mono text-[8px] sm:text-xs text-[#C5A059]">→</span>
            </button>

            <button
              type="button"
              onClick={() => { if (soundFx?.playClick) soundFx.playClick(); if (onOpenShowcase) onOpenShowcase(); }}
              className="w-full bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] py-2 sm:py-3 px-3 sm:px-4 flex items-center justify-between font-sports text-lg sm:text-2xl text-[#F7F5F0] transition-all active:scale-95 cursor-pointer"
            >
              <span className="truncate">🎴 ÁLBUM</span>
              <span className="font-mono text-[8px] sm:text-xs text-[#E6DFD3]">→</span>
            </button>
          </div>
        </section>

        {/* PANEL DERECHO: MATCHMAKING & RIVALES */}
        <section className="w-full lg:w-7/12 bg-[#121619] border border-[#C5A059] sm:border-2 p-3 sm:p-4 md:p-5 md:p-6 flex flex-col justify-between shadow-2xl rounded">
          <div>
            <span className="font-mono text-[9px] sm:text-xs text-[#C5A059] uppercase block mb-1">MATCHMAKING</span>
            <h3 className="font-sports text-2xl sm:text-3xl text-[#F7F5F0] uppercase border-b border-[#2C3E35] pb-1 sm:pb-2 mb-2 sm:mb-4">
              MODO DE JUEGO
            </h3>

            {/* SELECCIÓN DE MODO */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 md:gap-4 mb-3 sm:mb-4">
              <button
                type="button"
                onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setGameMode('PVE'); }}
                className={`p-2 sm:p-3 border transition-all text-center flex flex-col items-center justify-center cursor-pointer rounded ${
                  gameMode === 'PVE'
                    ? 'bg-[#1A3323] border-[#C5A059] sm:border-2 shadow-[0_0_15px_rgba(197,160,89,0.3)]'
                    : 'bg-[#0A0D0F] border-[#2C3E35] opacity-60 hover:opacity-100'
                }`}
              >
                <div className="font-sports text-lg sm:text-2xl text-[#F7F5F0] leading-none mb-1">
                  VS CPU
                </div>
                <p className="font-mono text-[8px] sm:text-[10px] text-[#E6DFD3] uppercase">
                  SOLITARIO
                </p>
              </button>

              <button
                type="button"
                onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setGameMode('PVP'); }}
                className={`p-2 sm:p-3 border transition-all text-center flex flex-col items-center justify-center rounded cursor-not-allowed ${
                  gameMode === 'PVP'
                    ? 'bg-[#1A3323] border-[#C5A059] sm:border-2'
                    : 'bg-[#0A0D0F] border-[#2C3E35] opacity-40'
                }`}
              >
                <div className="font-sports text-lg sm:text-2xl text-[#F7F5F0] leading-none mb-1">
                  1V1
                </div>
                <p className="font-mono text-[8px] sm:text-[10px] text-[#E6DFD3] uppercase">
                  PRÓXIMO
                </p>
              </button>
            </div>

            {/* CARRUSEL DE RIVAL CPU */}
            {gameMode === 'PVE' && (
              <>
                <div className="mb-3 sm:mb-4">
                  <div className="flex justify-between items-center mb-1 sm:mb-2">
                    <span className="font-mono text-[8px] sm:text-xs text-[#C5A059] uppercase block font-bold tracking-widest truncate">
                      ★ RIVAL CPU ★
                    </span>
                    <span className="font-mono text-[8px] sm:text-[10px] text-gray-400 flex-shrink-0">
                      {cpuRivals.length > 0 ? `${rivalIndex + 1}/${cpuRivals.length}` : '1/1'}
                    </span>
                  </div>

                  <div className="relative bg-[#0A0D0F] border border-[#2C3E35] sm:border-2 p-2 sm:p-3 md:p-4 rounded flex items-center justify-between gap-2 sm:gap-3 overflow-hidden shadow-inner">
                    
                    <button
                      type="button"
                      onClick={handlePrevRival}
                      className="w-8 sm:w-10 h-16 sm:h-24 bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] text-[#C5A059] font-sports text-lg sm:text-2xl flex items-center justify-center transition-all cursor-pointer z-10 flex-shrink-0"
                    >
                      ❮
                    </button>

                    <div className="flex-1 flex flex-col items-center text-center p-1 transition-all min-w-0">
                      <div className="relative mb-1 sm:mb-2">
                        <div
                          className="w-12 sm:w-16 h-12 sm:h-16 rounded-full flex items-center justify-center font-sports text-sm sm:text-2xl text-white border-2 border-white/30 shadow-2xl transition-transform scale-100 sm:scale-105"
                          style={{ backgroundColor: currentRival.color || '#002B66', boxShadow: `0 0 15px ${currentRival.color || '#002B66'}88` }}
                        >
                          {(currentRival.badge || currentRival.id).substring(0, 3)}
                        </div>
                        <div className="absolute -top-1 -right-2 bg-[#C5A059] text-[#121619] font-sports text-[10px] sm:text-sm font-extrabold px-1 sm:px-1.5 py-0 sm:py-0.5 rounded shadow border border-white">
                          {currentRival.ovr || 80}
                        </div>
                      </div>

                      <span className="text-[8px] sm:text-[10px] text-[#C5A059] uppercase font-mono font-bold tracking-wider">
                        {currentRival.city?.substring(0, 8)}
                      </span>
                      <h4 className="font-sports text-xl sm:text-3xl text-white uppercase leading-none my-0.5 sm:my-1 truncate">
                        {currentRival.name?.substring(0, 10)}
                      </h4>

                      <div className="flex gap-2 sm:gap-4 my-1 sm:my-2 text-[8px] sm:text-xs font-mono">
                        <div className="bg-[#121619] px-1.5 sm:px-3 py-0.5 sm:py-1 border border-[#2C3E35] rounded">
                          <span className="text-gray-400 block text-[7px] sm:text-[9px]">BAT</span>
                          <span className="text-[#C5A059] font-bold font-sports text-sm sm:text-base">{currentRival.batOvr || 80}</span>
                        </div>
                        <div className="bg-[#121619] px-1.5 sm:px-3 py-0.5 sm:py-1 border border-[#2C3E35] rounded">
                          <span className="text-gray-400 block text-[7px] sm:text-[9px]">PIT</span>
                          <span className="text-[#C5A059] font-bold font-sports text-sm sm:text-base">{currentRival.pitOvr || 80}</span>
                        </div>
                      </div>

                      <p className="text-[7px] sm:text-[10px] text-gray-400 font-mono line-clamp-2">
                        {currentRival.desc}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={handleNextRival}
                      className="w-8 sm:w-10 h-16 sm:h-24 bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] text-[#C5A059] font-sports text-lg sm:text-2xl flex items-center justify-center transition-all cursor-pointer z-10 flex-shrink-0"
                    >
                      ❯
                    </button>

                  </div>

                  <div className="flex justify-center items-center gap-1 mt-1 sm:mt-2">
                    {cpuRivals.map((r, idx) => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setRivalIndex(idx); }}
                        className={`h-1 sm:h-1.5 rounded-full transition-all cursor-pointer ${
                          idx === rivalIndex ? 'w-4 sm:w-6 bg-[#C5A059]' : 'w-1.5 sm:w-2 bg-[#2C3E35] hover:bg-gray-500'
                        }`}
                      />
                    ))}
                  </div>
                </div>

                {/* CONFIGURACIÓN (DIFICULTAD, INNINGS, POSICIÓN) */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3 mb-2 sm:mb-3">
                  
                  {/* DIFICULTAD */}
                  <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2 sm:p-2.5 rounded">
                    <span className="font-mono text-[8px] sm:text-[10px] text-[#E6DFD3] uppercase block mb-1 text-center font-bold">
                      DIFICULTAD
                    </span>
                    <div className="grid grid-cols-3 gap-1">
                      {[
                        { key: 'EASY', label: 'FÁCIL' },
                        { key: 'MEDIUM', label: 'MEDIA' },
                        { key: 'HARD', label: 'DIFÍCIL' },
                      ].map(({ key, label }) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setDifficulty(key); }}
                          className={`py-0.5 sm:py-1 font-sports text-[9px] sm:text-sm tracking-wider uppercase transition-colors rounded cursor-pointer ${
                            difficulty === key
                              ? 'bg-[#2D5A3F] text-[#F7F5F0] border border-[#C5A059]'
                              : 'text-[#E6DFD3] opacity-50 hover:opacity-100 bg-[#121619]'
                          }`}
                        >
                          {label.substring(0, 3)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* INNINGS */}
                  <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2 sm:p-2.5 rounded">
                    <span className="font-mono text-[8px] sm:text-[10px] text-[#E6DFD3] uppercase block mb-1 text-center font-bold">
                      INNINGS
                    </span>
                    <div className="grid grid-cols-3 gap-1">
                      {[3, 6, 9].map((innings) => (
                        <button
                          key={innings}
                          type="button"
                          onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setTotalInnings(innings); }}
                          className={`py-0.5 sm:py-1 font-sports text-[9px] sm:text-sm tracking-wider uppercase transition-colors rounded cursor-pointer ${
                            totalInnings === innings
                              ? 'bg-[#2D5A3F] text-[#F7F5F0] border border-[#C5A059]'
                              : 'text-[#E6DFD3] opacity-50 hover:opacity-100 bg-[#121619]'
                          }`}
                        >
                          {innings}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* POSICIÓN */}
                  <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2 sm:p-2.5 rounded">
                    <span className="font-mono text-[8px] sm:text-[10px] text-[#E6DFD3] uppercase block mb-1 text-center font-bold">
                      POSICIÓN
                    </span>
                    <div className="grid grid-cols-2 gap-1">
                      {[
                        { key: 'HOME', label: '🏠' },
                        { key: 'AWAY', label: '✈️' },
                      ].map(({ key, label }) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setPlayerPosition(key); }}
                          className={`py-0.5 sm:py-1 font-sports text-[9px] sm:text-sm tracking-wider uppercase transition-colors rounded cursor-pointer ${
                            playerPosition === key
                              ? 'bg-[#2D5A3F] text-[#F7F5F0] border border-[#C5A059]'
                              : 'text-[#E6DFD3] opacity-50 hover:opacity-100 bg-[#121619]'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* BOTÓN INICIAR PARTIDA */}
          <button
            type="button"
            onClick={handleStartGame}
            className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] text-[#C5A059] border border-[#C5A059] sm:border-2 py-2 sm:py-3 font-sports text-sm sm:text-2xl tracking-widest transition-all active:scale-95 shadow-xl mt-2 sm:mt-3 cursor-pointer uppercase"
          >
            {gameMode === 'PVE' ? `⚡ INICIAR ${totalInnings}INN` : 'BUSCAR RIVAL'}
          </button>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="font-mono text-[8px] sm:text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-1 sm:mt-2">
        KOSHIEN • RESPONSIVE
      </footer>
    </div>
  );
};