import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';

export const AuthScreen = ({ onLoginSuccess }) => {
  const { t, i18n } = useTranslation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);

  const toggleLanguage = () => {
    soundFx.playClick();
    i18n.changeLanguage(i18n.language === 'es' ? 'en' : 'es');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    soundFx.playGameStart();

    const fakeToken = "jwt_token_demo_2026";
    const userId = username.toLowerCase().replace(/\s+/g, '_') || "player_1";

    localStorage.setItem('jwt_token', fakeToken);
    localStorage.setItem('user_id', userId);

    onLoginSuccess({ userId, username: username || "Bateador Pro" });
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center p-4 bg-[#121619]">
      {/* Botón Selector de Idioma */}
      <div className="w-full max-w-md flex justify-end mb-2">
        <button
          onClick={toggleLanguage}
          className="border border-[#C5A059] bg-[#1A3323] px-3 py-1 font-mono text-xs text-[#F7F5F0] hover:bg-[#2D5A3F] transition-colors"
        >
          🌐 {i18n.language === 'es' ? 'ENGLISH' : 'ESPAÑOL'}
        </button>
      </div>

      {/* Cabecera / Logo */}
      <div className="w-full max-w-md text-center mb-6">
        <div className="inline-block border border-[#C5A059] bg-[#1A3323] px-4 py-1 mb-2">
          <span className="font-mono text-xs tracking-widest text-[#C5A059] uppercase">
            {t('app.tradition')}
          </span>
        </div>
        <h1 className="font-sports text-5xl md:text-6xl text-[#F7F5F0] tracking-wider uppercase leading-none">
          DECK AT THE PLATE
        </h1>
        <p className="font-mono text-xs text-[#E6DFD3] tracking-widest mt-1 uppercase">
          {t('app.subtitle')}
        </p>
      </div>

      {/* Formulario */}
      <div className="w-full max-w-md bg-[#121619] border-2 border-[#C5A059] p-6 shadow-2xl">
        <div className="flex border-b border-[#2C3E35] mb-6">
          <button
            type="button"
            onClick={() => { soundFx.playClick(); setIsRegister(false); }}
            className={`flex-1 py-2 font-sports text-2xl tracking-wider uppercase transition-colors ${
              !isRegister ? 'bg-[#1A3323] text-[#F7F5F0] border-b-2 border-[#C5A059]' : 'text-[#E6DFD3] opacity-60 hover:opacity-100'
            }`}
          >
            {t('auth.login_tab')}
          </button>
          <button
            type="button"
            onClick={() => { soundFx.playClick(); setIsRegister(true); }}
            className={`flex-1 py-2 font-sports text-2xl tracking-wider uppercase transition-colors ${
              isRegister ? 'bg-[#1A3323] text-[#F7F5F0] border-b-2 border-[#C5A059]' : 'text-[#E6DFD3] opacity-60 hover:opacity-100'
            }`}
          >
            {t('auth.register_tab')}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block font-mono text-xs text-[#E6DFD3] uppercase mb-1">
              {t('auth.username_label')}
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Ej. Bateador33"
              className="w-full bg-[#0A0D0F] border border-[#2C3E35] p-3 text-[#F7F5F0] focus:outline-none focus:border-[#C5A059]"
            />
          </div>

          <div>
            <label className="block font-mono text-xs text-[#E6DFD3] uppercase mb-1">
              {t('auth.password_label')}
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-[#0A0D0F] border border-[#2C3E35] p-3 text-[#F7F5F0] focus:outline-none focus:border-[#C5A059]"
            />
          </div>

          <button
            type="submit"
            onMouseEnter={() => soundFx.playCardSelect()}
            className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] text-[#F7F5F0] border-2 border-[#C5A059] py-3 font-sports text-2xl tracking-widest mt-6 transition-all active:scale-95"
          >
            {isRegister ? t('auth.submit_register') : t('auth.submit_login')}
          </button>
        </form>
      </div>
    </div>
  );
};