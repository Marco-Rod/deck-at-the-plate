import React from 'react';
import { GameIntroModal } from './GameIntroModal';
import { GameOverModal } from './GameOverModal';
import { InningTransitionModal } from './InningTransitionModal';

interface GameplayModalsProps {
  // Intro Modal
  showGameIntro: boolean;
  gameState: any;
  userTeam: any;
  userLineupCards: any[];
  pitcherCard: any;
  cpuPitcherCard: any;
  cpuLineupCards: any[];
  onPlayBall: () => void;

  // Game Over Modal
  showGameOverModal: boolean;
  userRole: 'HOME' | 'AWAY';
  getWinningPitcherInfo: () => { name?: string; strikeouts: number };
  onReturnToLobby: () => void;

  // Inning Transition Modal
  inningTransition: any;
  displayedGameState: any;
}

export const GameplayModals: React.FC<GameplayModalsProps> = ({
  showGameIntro,
  gameState,
  userTeam,
  userLineupCards,
  pitcherCard,
  cpuPitcherCard,
  cpuLineupCards,
  onPlayBall,
  showGameOverModal,
  userRole,
  getWinningPitcherInfo,
  onReturnToLobby,
  inningTransition,
  displayedGameState,
}) => {
  return (
    <>
      {/* MODAL INTRO DEL JUEGO */}
      {showGameIntro && gameState && (
        <GameIntroModal
          userTeamName={userTeam?.name || 'USUARIO'}
          userTeamLogo={userTeam?.logo}
          userPitcher={pitcherCard ? {
            name: pitcherCard.name,
            number: pitcherCard.number,
            photo: pitcherCard.photo,
            overall: pitcherCard.overall,
            position: pitcherCard.position,
          } : undefined}
          userLineup={userLineupCards}
          cpuTeamName={gameState?.rivalTeamName ? `${gameState.rivalTeamName}` : 'CPU'}
          cpuTeamLogo={undefined}
          cpuPitcher={cpuPitcherCard ? {
            name: cpuPitcherCard.name,
            number: cpuPitcherCard.number,
            photo: cpuPitcherCard.photo,
            overall: cpuPitcherCard.overall,
            position: cpuPitcherCard.position,
          } : undefined}
          cpuLineup={cpuLineupCards}
          onPlayBall={onPlayBall}
        />
      )}

      {/* MODAL DE FIN DE PARTIDO */}
      {showGameOverModal && gameState?.isGameOver && (() => {
        const homeTeamDisplay = userRole === 'HOME' ? userTeam?.short_name : `${gameState?.rivalTeamName || 'YANKEES'} (CPU)`;
        const awayTeamDisplay = userRole === 'HOME' ? `${gameState?.rivalTeamName || 'YANKEES'} (CPU)` : userTeam?.short_name;
        const { name: winningPitcherName, strikeouts: winningPitcherSO } = getWinningPitcherInfo();
        return (
          <GameOverModal
            winnerMessage={gameState.winnerMessage}
            homeScore={gameState.homeScore}
            awayScore={gameState.awayScore}
            homeTeamName={homeTeamDisplay}
            awayTeamName={awayTeamDisplay}
            userRole={userRole}
            winningPitcherName={winningPitcherName}
            winningPitcherSO={winningPitcherSO}
            onReturnToLobby={onReturnToLobby}
          />
        );
      })()}

      {/* MODAL DE TRANSICIÓN DE INNING */}
      {inningTransition?.visible && (
        <InningTransitionModal
          completedInning={inningTransition.completedInning}
          completedHalf={inningTransition.completedHalf}
          nextInning={inningTransition.nextInning}
          nextHalf={inningTransition.nextHalf}
          homeScore={displayedGameState?.homeScore ?? 0}
          awayScore={displayedGameState?.awayScore ?? 0}
          userRole={userRole}
        />
      )}
    </>
  );
};
