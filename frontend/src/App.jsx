/**
 * App.jsx — Punto de entrada y enrutador de vistas
 * ==================================================
 * Gestiona la navegación entre pantallas mediante un estado `currentView`.
 * No usa React Router: el flujo es lineal y predecible para un juego 1v1.
 *
 * Flujo de navegación:
 *   AUTH → LOBBY → ROSTER_SELECTION → STADIUM (partida en curso)
 *                ↘ MY_TEAM
 *                ↘ SHOWCASE
 *
 * Estados de `currentView`:
 *   'LOBBY'             → Pantalla principal con matchmaking
 *   'ROSTER_SELECTION'  → Selección de pitcher y lineup antes de la partida
 *   'STADIUM'           → Pantalla de juego en tiempo real (TSX componentizado)
 *   'MY_TEAM'           → Gestión de roster y mazo táctico
 *   'SHOWCASE'          → Álbum de cartas coleccionadas
 */

import React, { useState, useEffect } from 'react';
import { AuthScreen } from './pages/AuthScreen';
import { LobbyScreen } from './pages/LobbyScreen';
import { CardShowcaseScreen } from './pages/CardShowcaseScreen';
import { MyTeamScreen } from './pages/MyTeamScreen';
import { RosterSelectionScreen } from './pages/RosterSelectionScreen';
import { StadiumShowcaseScreen } from './components/stadium/StadiumShowcaseScreen';
import { auth as authApi } from './utils/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('LOBBY');
  // Configuración pendiente del modo/dificultad elegida en el Lobby
  const [pendingGameConfig, setPendingGameConfig] = useState(null);
  // ID real de la partida creada en el backend tras confirmar el roster
  const [activeGameId, setActiveGameId] = useState(null);

  // Restaurar sesión desde localStorage al cargar la app
  useEffect(() => {
    const currentUser = authApi.getCurrentUser();
    if (currentUser) {
      setUser(currentUser);
    }
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setCurrentView('LOBBY');
  };

  const handleLogout = () => {
    authApi.logout();
    setUser(null);
    setActiveGameId(null);
    setPendingGameConfig(null);
    setCurrentView('LOBBY');
  };

  /**
   * Llamado desde LobbyScreen cuando el usuario pulsa "Iniciar partida".
   * Guarda la configuración (modo/dificultad) y navega a la selección de roster.
   */
  const handleStartGame = (config) => {
    setPendingGameConfig(config);
    setCurrentView('ROSTER_SELECTION');
  };

  /**
   * Llamado desde RosterSelectionScreen cuando el usuario confirma su roster.
   * El `gameId` es el ID real retornado por POST /api/v1/games/create.
   */
  const handleRosterConfirmed = (gameId) => {
    setActiveGameId(gameId);
    setCurrentView('STADIUM');
  };

  const handleLeaveGame = () => {
    setActiveGameId(null);
    setPendingGameConfig(null);
    setCurrentView('LOBBY');
  };

  return (
    <div className="min-h-screen text-[#F7F5F0] bg-[#121619]">
      {!user ? (
        <AuthScreen onLoginSuccess={handleLoginSuccess} />

      ) : currentView === 'STADIUM' ? (
        <StadiumShowcaseScreen
          gameId={activeGameId}
          userId={user.userId}
          onBack={handleLeaveGame}
        />

      ) : currentView === 'ROSTER_SELECTION' ? (
        <RosterSelectionScreen
          user={user}
          gameConfig={pendingGameConfig}
          onRosterConfirmed={handleRosterConfirmed}
          onBack={() => setCurrentView('LOBBY')}
        />

      ) : currentView === 'MY_TEAM' ? (
        <MyTeamScreen
          user={user}
          onBack={() => setCurrentView('LOBBY')}
        />

      ) : currentView === 'SHOWCASE' ? (
        <CardShowcaseScreen onBack={() => setCurrentView('LOBBY')} />

      ) : (
        <LobbyScreen
          user={user}
          onStartGame={handleStartGame}
          onOpenMyTeam={() => setCurrentView('MY_TEAM')}
          onOpenShowcase={() => setCurrentView('SHOWCASE')}
          onLogout={handleLogout}
        />
      )}
    </div>
  );
}
