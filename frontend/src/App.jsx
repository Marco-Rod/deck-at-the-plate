import React, { useState, useEffect } from 'react';
import { AuthScreen } from './pages/AuthScreen';
import { LobbyScreen } from './pages/LobbyScreen';
import { CardShowcaseScreen } from './pages/CardShowcaseScreen';

export default function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('LOBBY'); // 'LOBBY' o 'SHOWCASE'
  const [activeGameConfig, setActiveGameConfig] = useState(null);

  useEffect(() => {
    const savedUserId = localStorage.getItem('user_id');
    if (savedUserId) {
      setUser({ userId: savedUserId, username: savedUserId });
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_id');
    setUser(null);
    setActiveGameConfig(null);
    setCurrentView('LOBBY');
  };

  return (
    <div className="min-h-screen text-[#F7F5F0] bg-[#121619]">
      {!user ? (
        <AuthScreen onLoginSuccess={(userData) => setUser(userData)} />
      ) : currentView === 'SHOWCASE' ? (
        <CardShowcaseScreen onBack={() => setCurrentView('LOBBY')} />
      ) : !activeGameConfig ? (
        <LobbyScreen
          user={user}
          onStartGame={(config) => setActiveGameConfig(config)}
          onOpenShowcase={() => setCurrentView('SHOWCASE')}
          onLogout={handleLogout}
        />
      ) : (
        <div className="min-h-screen flex flex-col items-center justify-center p-4">
          <div className="bg-[#121619] border-2 border-[#C5A059] p-8 text-center max-w-lg w-full shadow-2xl">
            <h2 className="font-sports text-4xl text-[#C5A059] mb-2 uppercase">
              PARTIDA LISTA
            </h2>
            <p className="font-mono text-sm text-[#E6DFD3] mb-6 uppercase">
              MODO: {activeGameConfig.mode} {activeGameConfig.difficulty && `(${activeGameConfig.difficulty})`}
            </p>
            <button
              onClick={() => setActiveGameConfig(null)}
              className="bg-[#1A3323] hover:bg-[#2D5A3F] border border-[#C5A059] px-6 py-2 text-2xl font-sports text-[#F7F5F0] transition-colors"
            >
              VOLVER AL LOBBY
            </button>
          </div>
        </div>
      )}
    </div>
  );
}