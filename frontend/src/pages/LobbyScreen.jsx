import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';

export const LobbyScreen = ({ user, onStartGame, onOpenMyTeam, onOpenShowcase, onLogout }) => {
  const { t, i18n } = useTranslation();
  const [gameMode, setGameMode] = useState('PVE');
  const [difficulty, setDifficulty] = useState('MEDIUM');

  const toggleLanguage = () => {
    soundFx.playClick();
    const nextLang = i18n.language === 'es' ? 'en' : 'es';
    i18n.changeLanguage(nextLang);
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 md:p-6 bg-[#121619]">
      {/* Top Navbar del Mánager (Sustituye la pizarra estática) */}
      <header className="w-full max-w-5xl mx-auto flex flex-wrap justify-between items-center bg-[#0A0D0F] border-2 border-[#C5A059] p-3 md:p-4 shadow-2xl gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-[#1A3323] border border-[#C5A059] px-3 py-1 text-center">
            <span className="font-sports text-2xl text-[#C5A059]">LVL 12</span>
          </div>
          <div>
            <span className="font-mono text-[10px] text-[#C5A059] uppercase block">{t('lobby.manager')}</span>
            <h2 className="font-sports text-2xl md:text-3xl text-[#F7F5F0] leading-none uppercase">
              {user?.username || 'BATEADOR PRO'}
            </h2>
          </div>
        </div>

        {/* Métricas e Idioma */}
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-3 bg-[#121619] border border-[#2C3E35] px-3 py-1.5 font-mono text-xs text-[#E6DFD3] mr-2">
            <span>RÉCORD: <strong className="text-[#C5A059]">14-5</strong></span>
          </div>

          <button
            onClick={toggleLanguage}
            className="border border-[#C5A059] bg-[#1A3323] hover:bg-[#2D5A3F] px-3 py-1.5 font-mono text-xs text-[#F7F5F0] transition-colors"
          >
            🌐 {i18n.language === 'es' ? 'EN' : 'ES'}
          </button>

          <button
            onClick={() => { soundFx.playClick(); onLogout(); }}
            className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#0A0D0F] hover:bg-[#121619] px-3 py-1.5 font-mono text-xs text-[#E6DFD3] transition-colors"
          >
            {t('lobby.logout')}
          </button>
        </div>
      </header>

      {/* Cuerpo Central Responsivo (Grid de 2 cols en Desktop / 1 col en Móvil) */}
      <main className="w-full max-w-5xl mx-auto my-auto py-4 md:py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Columna 1: Panel del Club y Accesos a Gestión (5 cols en LG) */}
        <section className="lg:col-span-5 bg-[#0A0D0F] border-2 border-[#2C3E35] p-5 flex flex-col justify-between shadow-2xl">
          <div>
            <span className="font-mono text-xs text-[#C5A059] uppercase block mb-1">MI CLUB & ROSTER</span>
            <h3 className="font-sports text-3xl text-[#F7F5F0] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              PREPARACIÓN
            </h3>

            {/* Resumen rápido del Roster Activo */}
            <div className="bg-[#121619] border border-[#2C3E35] p-3 space-y-2 mb-4">
              <div className="flex justify-between items-center font-mono text-xs">
                <span className="text-[#E6DFD3]">ABRIDOR AS:</span>
                <span className="font-sports text-xl text-[#C5A059]">S. OHTANI #17</span>
              </div>
              <div className="flex justify-between items-center font-mono text-xs border-t border-[#2C3E35] pt-2">
                <span className="text-[#E6DFD3]">4TO BATE:</span>
                <span className="font-sports text-xl text-[#F7F5F0]">H. MATSUI #55</span>
              </div>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <button
              onClick={() => { soundFx.playClick(); if (onOpenMyTeam) onOpenMyTeam(); }}
              className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] py-3 px-4 flex items-center justify-between font-sports text-2xl text-[#F7F5F0] transition-all active:scale-95 shadow-md"
            >
              <span>🛡️ GESTIONAR MI EQUIPO</span>
              <span className="font-mono text-xs text-[#C5A059]">→</span>
            </button>

            <button
              onClick={() => { soundFx.playClick(); if (onOpenShowcase) onOpenShowcase(); }}
              className="w-full bg-[#121619] hover:bg-[#1A3323] border border-[#2C3E35] hover:border-[#C5A059] py-3 px-4 flex items-center justify-between font-sports text-2xl text-[#F7F5F0] transition-all active:scale-95"
            >
              <span>🎴 ÁLBUM DE CARTAS</span>
              <span className="font-mono text-xs text-[#E6DFD3]">→</span>
            </button>
          </div>
        </section>

        {/* Columna 2: Selección de Modo y Matchmaking (7 cols en LG) */}
        <section className="lg:col-span-7 bg-[#121619] border-2 border-[#C5A059] p-5 md:p-6 flex flex-col justify-between shadow-2xl">
          <div>
            <span className="font-mono text-xs text-[#C5A059] uppercase block mb-1">MATCHMAKING</span>
            <h3 className="font-sports text-3xl text-[#F7F5F0] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              {t('lobby.select_mode')}
            </h3>

            {/* Tarjetas de Selección de Modo */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <button
                type="button"
                onClick={() => { soundFx.playClick(); setGameMode('PVE'); }}
                className={`p-4 border-2 transition-all text-center flex flex-col items-center justify-center ${
                  gameMode === 'PVE'
                    ? 'bg-[#1A3323] border-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)] scale-[1.02]'
                    : 'bg-[#0A0D0F] border-[#2C3E35] opacity-60 hover:opacity-100'
                }`}
              >
                <div className="font-sports text-3xl text-[#F7F5F0] leading-none mb-1">
                  {t('lobby.vs_cpu')}
                </div>
                <p className="font-mono text-[10px] text-[#E6DFD3] uppercase">
                  {t('lobby.vs_cpu_desc')}
                </p>
              </button>

              <button
                type="button"
                onClick={() => { soundFx.playClick(); setGameMode('PVP'); }}
                className={`p-4 border-2 transition-all text-center flex flex-col items-center justify-center ${
                  gameMode === 'PVP'
                    ? 'bg-[#1A3323] border-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)] scale-[1.02]'
                    : 'bg-[#0A0D0F] border-[#2C3E35] opacity-60 hover:opacity-100'
                }`}
              >
                <div className="font-sports text-3xl text-[#F7F5F0] leading-none mb-1">
                  {t('lobby.pvp')}
                </div>
                <p className="font-mono text-[10px] text-[#E6DFD3] uppercase">
                  {t('lobby.pvp_desc')}
                </p>
              </button>
            </div>

            {/* Ajuste de Dificultad (PvE) */}
            {gameMode === 'PVE' && (
              <div className="bg-[#0A0D0F] border border-[#2C3E35] p-3 mb-6">
                <span className="font-mono text-xs text-[#E6DFD3] uppercase block mb-2 text-center">
                  {t('lobby.cpu_difficulty')}
                </span>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: 'EASY', label: t('lobby.diff_easy') },
                    { key: 'MEDIUM', label: t('lobby.diff_medium') },
                    { key: 'HARD', label: t('lobby.diff_hard') },
                  ].map(({ key, label }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => { soundFx.playClick(); setDifficulty(key); }}
                      className={`py-1.5 font-sports text-lg tracking-wider uppercase transition-colors ${
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
            )}
          </div>

          {/* Botón Principal de Lanzamiento */}
          <button
            onClick={() => {
              soundFx.playGameStart();
              onStartGame({ mode: gameMode, difficulty });
            }}
            className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] text-[#F7F5F0] border-2 border-[#C5A059] py-4 font-sports text-3xl tracking-widest transition-all active:scale-95 shadow-xl mt-2"
          >
            {gameMode === 'PVE' ? t('lobby.start') : t('lobby.start_pvp')}
          </button>
        </section>
      </main>

      {/* Footer */}
      <footer className="font-mono text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-2">
        KOSHIEN BASEBALL ENGINE • RESPONSIVE LOBBY V2
      </footer>
    </div>
  );
};