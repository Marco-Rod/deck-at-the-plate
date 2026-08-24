/**
 * App.jsx — Punto de entrada y enrutador de vistas
 * ==================================================
 * Gestiona la navegación entre pantallas mediante un estado `currentView`.
 *
 * Flujo de navegación:
 *   AUTH ──(Login)────> LOBBY ──> ROSTER_SELECTION ──> STADIUM (Partida)
 *        └──(Register)─> ONBOARDING ──(Complete)──> LOBBY
 */

import React, { useState, useEffect } from 'react';
import { AuthScreen } from './pages/AuthScreen';
import OnboardingScreen from './pages/OnboardingScreen'; // Importamos el nuevo onboarding
import { LobbyScreen } from './pages/LobbyScreen';
import { CardShowcaseScreen } from './pages/CardShowcaseScreen';
import { MyTeamScreen } from './pages/MyTeamScreen';
import { RosterSelectionScreen } from './pages/RosterSelectionScreen';
import { StadiumShowcaseScreen } from './components/stadium/StadiumShowcaseScreen';
import { auth as authApi } from './utils/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState('LOBBY');
  
  // Estado para capturar el userId tras el registro y enviarlo a OnboardingScreen
  const [pendingOnboardingUserId, setPendingOnboardingUserId] = useState(null);

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

  /**
   * Llamado desde AuthScreen tras un registro exitoso.
   * Cambia la vista a ONBOARDING para que el usuario elija equipo y abra su starter pack.
   */
  const handleRegisterSuccess = (userId) => {
    setPendingOnboardingUserId(userId);
    setCurrentView('ONBOARDING');
  };

  /**
   * Llamado desde OnboardingScreen al presionar "Ir al Menú Principal".
   */
  const handleOnboardingComplete = () => {
    const currentUser = authApi.getCurrentUser();
    if (currentUser) {
      setUser(currentUser);
    }
    setPendingOnboardingUserId(null);
    setCurrentView('LOBBY');
  };

  const handleLogout = () => {
    authApi.logout();
    setUser(null);
    setActiveGameId(null);
    setPendingGameConfig(null);
    setPendingOnboardingUserId(null);
    setCurrentView('LOBBY');
  };

  const handleStartGame = (config) => {
    setPendingGameConfig(config);
    setCurrentView('ROSTER_SELECTION');
  };

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
      {/* VISTA 1: AUTENTICACIÓN (LOGIN O REGISTRO) */}
      {!user && currentView !== 'ONBOARDING' ? (
        <AuthScreen
          onLoginSuccess={handleLoginSuccess}
          onRegisterSuccess={handleRegisterSuccess}
        />

      ) : /* VISTA 2: ONBOARDING DE REGISTRO (ELECCIÓN DE FRANCHISE Y APERTURA DE SOBRE) */
      currentView === 'ONBOARDING' ? (
        <OnboardingScreen
          userId={pendingOnboardingUserId || user?.userId}
          onComplete={handleOnboardingComplete}
        />

      ) : /* VISTA 3: PANTALLA DE JUEGO (ESTADIO 1V1) */
      currentView === 'STADIUM' ? (
        <StadiumShowcaseScreen
          gameId={activeGameId}
          userId={user.userId}
          onBack={handleLeaveGame}
        />

      ) : /* VISTA 4: SELECCIÓN DE ROSTER */
      currentView === 'ROSTER_SELECTION' ? (
        <RosterSelectionScreen
          user={user}
          gameConfig={pendingGameConfig}
          onRosterConfirmed={handleRosterConfirmed}
          onBack={() => setCurrentView('LOBBY')}
        />

      ) : /* VISTA 5: MI EQUIPO Y GESTIÓN DE ROSTER */
      currentView === 'MY_TEAM' ? (
        <MyTeamScreen
          user={user}
          onBack={() => setCurrentView('LOBBY')}
        />

      ) : /* VISTA 6: ÁLBUM / SHOWCASE */
      currentView === 'SHOWCASE' ? (
        <CardShowcaseScreen onBack={() => setCurrentView('LOBBY')} />

      ) : /* VISTA DEFAULT: LOBBY PRINCIPAL */ (
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