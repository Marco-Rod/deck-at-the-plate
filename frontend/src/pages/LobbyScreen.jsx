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
    userApi.getTeam(user.userId)
      .then(data => setUserTeam(data))
      .catch(err => console.error('Sin club activo:', err));

    // 2. Obtener métricas calculadas del club del usuario (OVR, BAT, PIT)
    if (userApi.getTeamStats) {
      userApi.getTeamStats(user.userId)
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
    onStartGame({
      mode: gameMode,
      difficulty,
      totalInnings,
      playerPosition,  // ⭐ NUEVO: incluir posición elegida
      rival: currentRival
    });
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 md:p-6 font-mono select-none">
      
      {/* NAVBAR SUPERIOR DEL MÁNAGER */}
      <header className="w-full max-w-6xl mx-auto flex flex-wrap justify-between items-center bg-[#0A0D0F] border-2 border-[#C5A059] p-3 md:p-4 shadow-2xl gap-3 rounded">
        <div className="flex items-center gap-3">
          <div className="bg-[#1A3323] border border-[#C5A059] px-3 py-1 text-center">
            <span className="font-sports text-2xl text-[#C5A059]">LVL 12</span>
          </div>
          <div>
            <span className="font-mono text-[10px] text-[#C5A059] uppercase block">
              {t('lobby.manager', { defaultValue: 'MÁNAGER ACTIVO' })}
            </span>
            <h2 className="font-sports text-2xl md:text-3xl text-[#F7F5F0] leading-none uppercase">
              {user?.username || 'BATEADOR PRO'}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-3 bg-[#121619] border border-[#2C3E35] px-3 py-1.5 font-mono text-xs text-[#E6DFD3] mr-2">
            <span>RÉCORD: <strong className="text-[#C5A059]">14-5</strong></span>
          </div>

          <button
            type="button"
            onClick={toggleLanguage}
            className="border border-[#C5A059] bg-[#1A3323] hover:bg-[#2D5A3F] px-3 py-1.5 font-mono text-xs text-[#F7F5F0] transition-colors cursor-pointer"
          >
            🌐 {i18n.language === 'es' ? 'EN' : 'ES'}
          </button>

          <button
            type="button"
            onClick={() => { if (soundFx?.playClick) soundFx.playClick(); onLogout(); }}
            className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#0A0D0F] hover:bg-[#121619] px-3 py-1.5 font-mono text-xs text-[#E6DFD3] transition-colors cursor-pointer"
          >
            {t('lobby.logout', { defaultValue: 'SALIR' })}
          </button>
        </div>
      </header>

      {/* ÁREA CENTRAL */}
      <main className="w-full max-w-6xl mx-auto my-auto py-4 md:py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* PANEL IZQUIERDO: PREPARACIÓN DE MI CLUB (5 COLS) */}
        <section className="lg:col-span-5 bg-[#0A0D0F] border-2 border-[#2C3E35] p-5 flex flex-col justify-between shadow-2xl rounded">
          <div>
            <span className="font-mono text-xs text-[#C5A059] uppercase block mb-1">MI CLUB & ROSTER</span>
            <h3 className="font-sports text-3xl text-[#F7F5F0] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              PREPARACIÓN
            </h3>

            {userTeam ? (
              <div className="bg-[#121619] border border-[#C5A059]/40 p-4 rounded mb-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div 
                      className="w-14 h-14 rounded-full flex items-center justify-center font-sports text-xl text-white border-2 border-white/20 shadow shrink-0"
                      style={{ backgroundColor: userTeam.primary_color }}
                    >
                      {userTeam.short_name}
                    </div>
                    <div className="overflow-hidden">
                      <span className="text-[10px] text-gray-400 block truncate font-mono">
                        {userTeam.city} • {userTeam.stadium_name}
                      </span>
                      <h4 className="font-sports text-2xl text-white truncate uppercase">{userTeam.name}</h4>
                    </div>
                  </div>

                  {/* BADGE DE OVR GENERAL DEL USUARIO */}
                  <div className="bg-[#C5A059] text-[#121619] font-sports text-lg font-extrabold px-2 py-1 rounded shadow border border-white shrink-0">
                    {userStats.overall} OVR
                  </div>
                </div>

                {/* MÉTRICAS DE BATEO Y PITCHEO DEL USUARIO */}
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[#2C3E35]">
                  <div className="bg-[#0A0D0F] p-2 border border-[#2C3E35] rounded text-center">
                    <span className="text-gray-400 block text-[9px] font-mono">BATEO (BAT)</span>
                    <span className="text-[#C5A059] font-bold font-sports text-xl">{userStats.batOvr}</span>
                  </div>
                  <div className="bg-[#0A0D0F] p-2 border border-[#2C3E35] rounded text-center">
                    <span className="text-gray-400 block text-[9px] font-mono">PITCHEO (PIT)</span>
                    <span className="text-[#C5A059] font-bold font-sports text-xl">{userStats.pitOvr}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-[#121619] border border-[#2C3E35] p-4 text-xs text-gray-400 mb-4 text-center font-mono">
                Cargando datos del club...
              </div>
            )}
          </div>

          <div className="space-y-3 pt-2">
            <button
              type="button"
              onClick={() => { if (soundFx?.playClick) soundFx.playClick(); if (onOpenMyTeam) onOpenMyTeam(); }}
              className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] py-3.5 px-4 flex items-center justify-between font-sports text-2xl text-[#F7F5F0] transition-all active:scale-95 shadow-md cursor-pointer"
            >
              <span>🛡️ GESTIONAR MI EQUIPO</span>
              <span className="font-mono text-xs text-[#C5A059]">→</span>
            </button>

            <button
              type="button"
              onClick={() => { if (soundFx?.playClick) soundFx.playClick(); if (onOpenShowcase) onOpenShowcase(); }}
              className="w-full bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] py-3 px-4 flex items-center justify-between font-sports text-2xl text-[#F7F5F0] transition-all active:scale-95 cursor-pointer"
            >
              <span>🎴 ÁLBUM DE CARTAS</span>
              <span className="font-mono text-xs text-[#E6DFD3]">→</span>
            </button>
          </div>
        </section>

        {/* PANEL DERECHO: MATCHMAKING & CARRUSEL DE RIVALES (7 COLS) */}
        <section className="lg:col-span-7 bg-[#121619] border-2 border-[#C5A059] p-5 md:p-6 flex flex-col justify-between shadow-2xl rounded">
          <div>
            <span className="font-mono text-xs text-[#C5A059] uppercase block mb-1">MATCHMAKING</span>
            <h3 className="font-sports text-3xl text-[#F7F5F0] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              {t('lobby.select_mode', { defaultValue: 'SELECCIONAR MODO DE JUEGO' })}
            </h3>

            {/* SELECCIÓN DE MODO */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <button
                type="button"
                onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setGameMode('PVE'); }}
                className={`p-3 border-2 transition-all text-center flex flex-col items-center justify-center cursor-pointer rounded ${
                  gameMode === 'PVE'
                    ? 'bg-[#1A3323] border-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]'
                    : 'bg-[#0A0D0F] border-[#2C3E35] opacity-60 hover:opacity-100'
                }`}
              >
                <div className="font-sports text-2xl text-[#F7F5F0] leading-none mb-1">
                  VS CPU
                </div>
                <p className="font-mono text-[10px] text-[#E6DFD3] uppercase">
                  PARTIDA RÁPIDA SOLITARIO
                </p>
              </button>

              <button
                type="button"
                onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setGameMode('PVP'); }}
                className={`p-3 border-2 transition-all text-center flex flex-col items-center justify-center rounded cursor-not-allowed ${
                  gameMode === 'PVP'
                    ? 'bg-[#1A3323] border-[#C5A059]'
                    : 'bg-[#0A0D0F] border-[#2C3E35] opacity-40'
                }`}
              >
                <div className="font-sports text-2xl text-[#F7F5F0] leading-none mb-1">
                  1V1 ONLINE
                </div>
                <p className="font-mono text-[10px] text-[#E6DFD3] uppercase">
                  DESAFÍO MULTIJUGADOR (PRÓXIMAMENTE)
                </p>
              </button>
            </div>

            {/* CARRUSEL DE RIVAL CPU */}
            {gameMode === 'PVE' && (
              <>
                <div className="mb-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-mono text-xs text-[#C5A059] uppercase block font-bold tracking-widest">
                      ★ SELECCIONA TU RIVAL CPU ★
                    </span>
                    <span className="font-mono text-[10px] text-gray-400">
                      {cpuRivals.length > 0 ? `${rivalIndex + 1} / ${cpuRivals.length}` : '1 / 1'}
                    </span>
                  </div>

                  <div className="relative bg-[#0A0D0F] border-2 border-[#2C3E35] p-4 rounded flex items-center justify-between gap-3 overflow-hidden shadow-inner">
                    
                    <button
                      type="button"
                      onClick={handlePrevRival}
                      className="w-10 h-24 bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] text-[#C5A059] font-sports text-2xl flex items-center justify-center transition-all cursor-pointer z-10 shrink-0"
                    >
                      ❮
                    </button>

                    <div className="flex-1 flex flex-col items-center text-center p-1 transition-all">
                      <div className="relative mb-2">
                        <div
                          className="w-16 h-16 rounded-full flex items-center justify-center font-sports text-2xl text-white border-2 border-white/30 shadow-2xl transition-transform scale-105"
                          style={{ backgroundColor: currentRival.color || '#002B66', boxShadow: `0 0 25px ${currentRival.color || '#002B66'}88` }}
                        >
                          {currentRival.badge || currentRival.id}
                        </div>
                        <div className="absolute -top-2 -right-3 bg-[#C5A059] text-[#121619] font-sports text-sm font-extrabold px-1.5 py-0.5 rounded shadow border border-white">
                          {currentRival.ovr || 80} OVR
                        </div>
                      </div>

                      <span className="text-[10px] text-[#C5A059] uppercase font-mono font-bold tracking-wider">
                        {currentRival.city}
                      </span>
                      <h4 className="font-sports text-3xl text-white uppercase leading-none my-1">
                        {currentRival.name}
                      </h4>

                      <div className="flex gap-4 my-2 text-xs font-mono">
                        <div className="bg-[#121619] px-3 py-1 border border-[#2C3E35] rounded">
                          <span className="text-gray-400 block text-[9px]">BAT:</span>
                          <span className="text-[#C5A059] font-bold font-sports text-base">{currentRival.batOvr || 80}</span>
                        </div>
                        <div className="bg-[#121619] px-3 py-1 border border-[#2C3E35] rounded">
                          <span className="text-gray-400 block text-[9px]">PIT:</span>
                          <span className="text-[#C5A059] font-bold font-sports text-base">{currentRival.pitOvr || 80}</span>
                        </div>
                      </div>

                      <p className="text-[10px] text-gray-400 font-mono">
                        {currentRival.desc}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={handleNextRival}
                      className="w-10 h-24 bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] text-[#C5A059] font-sports text-2xl flex items-center justify-center transition-all cursor-pointer z-10 shrink-0"
                    >
                      ❯
                    </button>

                  </div>

                  <div className="flex justify-center items-center gap-1.5 mt-2">
                    {cpuRivals.map((r, idx) => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setRivalIndex(idx); }}
                        className={`h-1.5 rounded-full transition-all cursor-pointer ${
                          idx === rivalIndex ? 'w-6 bg-[#C5A059]' : 'w-2 bg-[#2C3E35] hover:bg-gray-500'
                        }`}
                      />
                    ))}
                  </div>
                </div>

                {/* CONTENEDOR DE CONFIGURACIÓN (DIFICULTAD, INNINGS Y POSICIÓN) */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-2">
                  
                  {/* DIFICULTAD */}
                  <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2.5 rounded">
                    <span className="font-mono text-[10px] text-[#E6DFD3] uppercase block mb-1.5 text-center font-bold">
                      DIFICULTAD DE LA CPU
                    </span>
                    <div className="grid grid-cols-3 gap-1.5">
                      {[
                        { key: 'EASY', label: 'FÁCIL' },
                        { key: 'MEDIUM', label: 'MEDIA' },
                        { key: 'HARD', label: 'DIFÍCIL' },
                      ].map(({ key, label }) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setDifficulty(key); }}
                          className={`py-1 font-sports text-sm tracking-wider uppercase transition-colors rounded cursor-pointer ${
                            difficulty === key
                              ? 'bg-[#2D5A3F] text-[#F7F5F0] border border-[#C5A059]'
                              : 'text-[#E6DFD3] opacity-50 hover:opacity-100 bg-[#121619]'
                          }`}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* INNINGS JUGADOS (3, 6, 9) */}
                  <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2.5 rounded">
                    <span className="font-mono text-[10px] text-[#E6DFD3] uppercase block mb-1.5 text-center font-bold">
                      INNINGS DEL PARTIDO
                    </span>
                    <div className="grid grid-cols-3 gap-1.5">
                      {[3, 6, 9].map((innings) => (
                        <button
                          key={innings}
                          type="button"
                          onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setTotalInnings(innings); }}
                          className={`py-1 font-sports text-sm tracking-wider uppercase transition-colors rounded cursor-pointer ${
                            totalInnings === innings
                              ? 'bg-[#2D5A3F] text-[#F7F5F0] border border-[#C5A059]'
                              : 'text-[#E6DFD3] opacity-50 hover:opacity-100 bg-[#121619]'
                          }`}
                        >
                          {innings} INN
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* ⭐ NUEVO: POSICIÓN (LOCAL/VISITANTE) */}
                  <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2.5 rounded">
                    <span className="font-mono text-[10px] text-[#E6DFD3] uppercase block mb-1.5 text-center font-bold">
                      TU POSICIÓN
                    </span>
                    <div className="grid grid-cols-2 gap-1.5">
                      {[
                        { key: 'HOME', label: '🏠 LOCAL' },
                        { key: 'AWAY', label: '✈️ VISITANTE' },
                      ].map(({ key, label }) => (
                        <button
                          key={key}
                          type="button"
                          onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setPlayerPosition(key); }}
                          className={`py-1 font-sports text-sm tracking-wider uppercase transition-colors rounded cursor-pointer ${
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
            className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] text-[#C5A059] border-2 border-[#C5A059] py-3.5 font-sports text-2xl tracking-widest transition-all active:scale-95 shadow-xl mt-3 cursor-pointer uppercase"
          >
            {gameMode === 'PVE' ? `⚡ INICIAR PARTIDA DE ${totalInnings} INN VS ${currentRival.id}` : 'ENCONTRAR RIVAL ONLINE'}
          </button>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="font-mono text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-2">
        KOSHIEN BASEBALL ENGINE • RESPONSIVE LOBBY V3
      </footer>
    </div>
  );
};