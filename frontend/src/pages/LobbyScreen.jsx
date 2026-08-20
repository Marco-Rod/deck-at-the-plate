import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';
import { ScoreboardHeader } from '../components/ui/ScoreboardHeader';

export const LobbyScreen = ({ user, onStartGame, onOpenShowcase, onLogout }) => {
  const { t, i18n } = useTranslation();
  const [gameMode, setGameMode] = useState('PVE');
  const [difficulty, setDifficulty] = useState('MEDIUM');

  const toggleLanguage = () => {
    soundFx.playClick();
    const nextLang = i18n.language === 'es' ? 'en' : 'es';
    i18n.changeLanguage(nextLang);
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-between p-4 bg-[#121619]">
      {/* Selector de Idioma */}
      <div className="w-full max-w-xl flex justify-end mb-2">
        <button
          onClick={toggleLanguage}
          className="border border-[#C5A059] bg-[#1A3323] px-3 py-1 font-mono text-xs text-[#F7F5F0] hover:bg-[#2D5A3F] transition-colors"
        >
          🌐 {i18n.language === 'es' ? 'ENGLISH' : 'ESPAÑOL'}
        </button>
      </div>

      {/* Marcador Superior */}
      <div className="w-full max-w-xl my-2">
        <ScoreboardHeader homeScore={0} awayScore={0} inning="LOBBY" outs={0} />
      </div>

      {/* Tarjeta del Lobby */}
      <div className="w-full max-w-xl bg-[#121619] border-2 border-[#C5A059] p-6 shadow-2xl my-4">
        {/* Cabecera del Mánager con botón de Álbum */}
        <div className="flex justify-between items-center border-b border-[#2C3E35] pb-4 mb-6">
          <div>
            <span className="font-mono text-xs text-[#C5A059] uppercase block">
              {t('lobby.manager')}
            </span>
            <h2 className="font-sports text-3xl text-[#F7F5F0] leading-none uppercase">
              {user?.username || 'BATEADOR PRO'}
            </h2>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { soundFx.playClick(); if (onOpenShowcase) onOpenShowcase(); }}
              className="border border-[#C5A059] bg-[#1A3323] hover:bg-[#2D5A3F] px-3 py-1 font-mono text-xs text-[#F7F5F0] transition-colors"
            >
              🎴 ÁLBUM DE CARTAS
            </button>
            <button
              onClick={() => { soundFx.playClick(); onLogout(); }}
              className="border border-[#2C3E35] hover:border-[#C5A059] px-3 py-1 font-mono text-xs text-[#E6DFD3] transition-colors"
            >
              {t('lobby.logout')}
            </button>
          </div>
        </div>

        {/* Selección de Modo */}
        <h3 className="font-sports text-2xl text-[#C5A059] mb-3 uppercase tracking-wider text-center">
          {t('lobby.select_mode')}
        </h3>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <button
            type="button"
            onClick={() => { soundFx.playClick(); setGameMode('PVE'); }}
            className={`p-4 border-2 transition-all text-center ${
              gameMode === 'PVE'
                ? 'bg-[#1A3323] border-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]'
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
            className={`p-4 border-2 transition-all text-center ${
              gameMode === 'PVP'
                ? 'bg-[#1A3323] border-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]'
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

        {/* Selector de Niveles de Dificultad (Visible solo en VS CPU) */}
        {gameMode === 'PVE' && (
          <div className="bg-[#0A0D0F] border border-[#2C3E35] p-3 mb-6">
            <span className="font-mono text-xs text-[#E6DFD3] uppercase block mb-2 text-center">
              {t('lobby.cpu_difficulty')}
            </span>
            <div className="flex gap-2">
              {[
                { key: 'EASY', label: t('lobby.diff_easy') },
                { key: 'MEDIUM', label: t('lobby.diff_medium') },
                { key: 'HARD', label: t('lobby.diff_hard') },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => { soundFx.playClick(); setDifficulty(key); }}
                  className={`flex-1 py-1 font-sports text-lg tracking-wider uppercase transition-colors ${
                    difficulty === key
                      ? 'bg-[#2D5A3F] text-[#F7F5F0] border border-[#C5A059]'
                      : 'text-[#E6DFD3] opacity-50 hover:opacity-100'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Botón Principal de Acción */}
        <button
          onClick={() => {
            soundFx.playGameStart();
            onStartGame({ mode: gameMode, difficulty });
          }}
          className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] text-[#F7F5F0] border-2 border-[#C5A059] py-4 font-sports text-3xl tracking-widest transition-all active:scale-95 shadow-lg"
        >
          {gameMode === 'PVE' ? t('lobby.start') : t('lobby.start_pvp')}
        </button>
      </div>
    </div>
  );
};