import React from 'react';
import {
  Scoreboard,
  GameInfo,
  PitchZoneGrid,
  GameStatsPanel,
  TacticalHand,
  CentralField,
  PitcherStaminaBar,
} from './index';
import { PlayResultOverlay } from './PlayResultOverlay';
import { QuitGameModal } from './QuitGameModal';
import { RivalPitcherChangeModal } from './RivalPitcherChangeModal';

interface GameplayInterfaceProps {
  showGameIntro: boolean;
  gameState: any;
  displayedGameState: any;
  userTeam: any;
  userId: string;
  gameId: string | null;
  userRole: 'HOME' | 'AWAY';
  role: 'PITCHER' | 'BATTER';
  pitcherCard: any;
  batterCard: any;
  cpuPitcherCard: any;
  userLineupCards: any[];
  cpuLineupCards: any[];
  lastResult: any;
  inningTransition: any;
  isConnected: boolean;
  wsError: string | null;
  onBack: () => void;
  
  // Selection states
  selectedZone: string;
  selectedPitch: string;
  selectedSwing: string;
  selectedTacticalId: string | null;
  hasPitched: boolean;
  
  // Handlers
  setSelectedZone: (z: string) => void;
  setSelectedPitch: (p: string) => void;
  setSelectedSwing: (s: string) => void;
  setSelectedTacticalId: (id: string | null) => void;
  setPitcherCard: (c: any) => void;
  
  // Status
  isAwaitingResult: boolean;
  isProcessing: boolean;
  
  // Control handlers
  handleSubmitPlay: () => void;
  showQuitModal: boolean;
  setShowQuitModal: (v: boolean) => void;
  handleQuitGame: () => void;
  isQuittingGame: boolean;
  
  // Getters
  getBattingLineup: () => any[];
  getBattingLineupLabel: () => string;
  getPitcherStrikeouts: () => number;
  getActivePitcherName: () => string;
  
  // Other
  tacticalHand: any[];
  rivalPitcherChangeData: any;
  showRivalPitcherChangeModal: boolean;
  setShowRivalPitcherChangeModal: (v: boolean) => void;
  onClickRivalPitcher?: () => void; // ⭐ NUEVO: Handler para abrir modal de cambio de pitcher
}

export const GameplayInterface: React.FC<GameplayInterfaceProps> = ({
  showGameIntro,
  gameState,
  displayedGameState,
  userTeam,
  userId,
  gameId,
  userRole,
  role,
  pitcherCard,
  batterCard,
  cpuPitcherCard,
  userLineupCards,
  cpuLineupCards,
  lastResult,
  inningTransition,
  isConnected,
  wsError,
  onBack,
  selectedZone,
  selectedPitch,
  selectedSwing,
  selectedTacticalId,
  hasPitched,
  setSelectedZone,
  setSelectedPitch,
  setSelectedSwing,
  setSelectedTacticalId,
  setPitcherCard,
  isAwaitingResult,
  isProcessing,
  handleSubmitPlay,
  showQuitModal,
  setShowQuitModal,
  handleQuitGame,
  isQuittingGame,
  getBattingLineup,
  getBattingLineupLabel,
  getPitcherStrikeouts,
  getActivePitcherName,
  tacticalHand,
  rivalPitcherChangeData,
  showRivalPitcherChangeModal,
  setShowRivalPitcherChangeModal,
  onClickRivalPitcher, // ⭐ NUEVO
}) => {
  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 text-[#F7F5F0] relative overflow-hidden select-none">
      {/* Error banner */}
      {wsError && (
        <div className="mb-4 p-3 bg-red-800 border border-red-600 rounded text-white">
          <p className="font-semibold">Error de Conexión</p>
          <p className="text-sm">{wsError}</p>
        </div>
      )}

      {/* Header */}
      {!showGameIntro && (
        <header className="w-full flex justify-between items-center border-b-2 border-[#C5A059]/40 pb-3 mb-3 z-30">
          <div>
            <h2 className="font-sports text-3xl text-[#F7F5F0] uppercase tracking-wider leading-none">
              {userTeam ? `${userTeam.name} VS CPU` : 'CAMPO DE JUEGO'}
            </h2>
            <span className={`font-mono text-[10px] ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
              {isConnected ? '● CONECTADO EN VIVO' : '○ DESCONECTADO'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowQuitModal(true)}
              className="bg-[#0A0D0F] border border-red-600 px-4 py-2 font-mono text-xs text-red-500 font-bold cursor-pointer hover:bg-red-600/10 transition-colors"
              title="Finalizar el partido actual"
            >
              🚪 FINALIZAR
            </button>
          </div>
        </header>
      )}

      {/* Marcador */}
      {!showGameIntro && gameState && (() => {
        const homeTeamDisplay = userRole === 'HOME' ? userTeam?.short_name : `${displayedGameState?.rivalTeamName || 'YANKEES'} (CPU)`;
        const awayTeamDisplay = userRole === 'HOME' ? `${displayedGameState?.rivalTeamName || 'YANKEES'} (CPU)` : userTeam?.short_name;
        
        return (
          <Scoreboard 
            gameState={displayedGameState} 
            role={role}
            userRole={userRole}
            homeTeamName={homeTeamDisplay}
            awayTeamName={awayTeamDisplay}
            totalInnings={displayedGameState?.totalInnings}
            homeHits={displayedGameState?.homeHits || 0}
            awayHits={displayedGameState?.awayHits || 0}
            inningRuns={displayedGameState?.inning_runs || {}}
          />
        );
      })()}

      {/* Campo Principal */}
      {!showGameIntro && (
        <main className="w-full sm:w-[95%] mx-auto border border-[#C5A059]/30 sm:border-2 sm:border-[#C5A059]/50 p-0.5 sm:p-1 md:p-2 relative flex flex-col md:flex-row justify-start md:justify-between items-start md:items-center min-h-auto md:min-h-[500px] shadow-2xl overflow-x-hidden md:overflow-hidden rounded-sm gap-1 md:gap-2 mt-0.5 sm:mt-1">
          <div className="absolute inset-0 bg-[#0A0D0F]/60 pointer-events-none" />

          {/* PANEL IZQUIERDO - Lineup del bateador */}
          <div className="relative z-10 w-full md:w-[450px] md:flex-shrink-0 order-1 md:order-1 overflow-y-auto max-h-[40vh] md:max-h-full">
            <div className="bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded p-1 sm:p-2 md:p-3 text-xs md:text-sm">
              <div className="text-[9px] sm:text-xs text-[#C5A059] font-bold mb-0.5 sm:mb-1 px-1 truncate">
                {getBattingLineupLabel()}
              </div>
              <GameStatsPanel
                lineup={getBattingLineup()}
                stats={gameState?.batter_stats || {}}
                isPitcher={false}
              />
            </div>
          </div>

          {/* CONTENEDOR CENTRAL - Campo de juego */}
          <div className="w-full md:flex-1 order-3 md:order-2 px-0.5 sm:px-1 md:px-2">
            <CentralField
              role={role}
              pitcherCard={pitcherCard}
              batterCard={batterCard}
              selectedZone={selectedZone}
              selectedPitch={selectedPitch}
              repertoire={pitcherCard?.repertoire}
              hasPitched={hasPitched}
              isAwaitingResult={isAwaitingResult || isProcessing}
              inningTransition={inningTransition}
              onSelectZone={setSelectedZone}
              onSelectPitch={setSelectedPitch}
              balls={displayedGameState?.balls ?? 0}
              strikes={displayedGameState?.strikes ?? 0}
              outs={displayedGameState?.outs ?? 0}
              currentInning={displayedGameState?.currentInning ?? 1}
              totalInnings={displayedGameState?.totalInnings ?? 9}
              isTopInning={displayedGameState?.isTopInning ?? true}
              runners={displayedGameState?.runners ?? { b1: null, b2: null, b3: null }}
              gameId={gameId}
              userId={userId}
              fatigueLevel={displayedGameState?.active_pitcher?.fatigue_level ?? 0}
              pitchCount={displayedGameState?.active_pitcher?.pitch_count ?? 0}
              onPitcherChanged={(newPitcher) => {
                if (!newPitcher) return;
                setPitcherCard({
                  id: newPitcher.id,
                  name: newPitcher.name,
                  number: newPitcher.number,
                  overall: newPitcher.overall,
                  position: newPitcher.position,
                  rarity: newPitcher.rarity || 'COMMON',
                  team: newPitcher.team || '',
                  role: 'PITCHER',
                  photo: newPitcher.photo,
                  repertoire: newPitcher.repertoire || [],
                  stats: newPitcher.stats || [],
                  pitch_count: 0,
                  fatigue_level: 0,
                });
                const rep = newPitcher.repertoire || [];
                if (rep.length > 0 && rep[0]?.pitch_type) {
                  setSelectedPitch(rep[0].pitch_type);
                }
              }}
            />
          </div>

          {/* PANEL DERECHO - Strikeouts del pitcher */}
          <div className="relative z-10 w-full md:w-[450px] md:flex-shrink-0 order-2 md:order-3 overflow-y-auto max-h-[40vh] md:max-h-full">
            <div className="bg-[#0A0D0F]/90 border border-[#C5A059]/30 rounded p-1 sm:p-2 md:p-3 text-xs md:text-sm flex flex-col gap-2 sm:gap-3">
              <PitcherStaminaBar
                pitchCount={displayedGameState?.active_pitcher?.pitch_count || 0}
                fatigueLevel={displayedGameState?.active_pitcher?.fatigue_level || 0}
                totalInnings={displayedGameState?.totalInnings || 9}
                basePitcherStats={{
                  velocidad: displayedGameState?.active_pitcher?.stats?.find((s: any) => s.label === 'VELO')?.val || 75,
                  control: displayedGameState?.active_pitcher?.stats?.find((s: any) => s.label === 'CTRL')?.val || 75,
                  movimiento: displayedGameState?.active_pitcher?.stats?.find((s: any) => s.label === 'MVTO')?.val || 75,
                }}
              />

              <div>
                <div className="text-[9px] sm:text-xs text-[#C5A059] font-bold mb-0.5 sm:mb-1 px-1">
                  🔥 K's
                </div>
                <GameStatsPanel
                  lineup={[]}
                  stats={{}}
                  isPitcher={true}
                  pitcherStrikeouts={getPitcherStrikeouts()}
                  pitcherName={getActivePitcherName()}
                />
              </div>
            </div>
          </div>
        </main>
      )}

      {/* Overlay de resultado */}
      {!showGameIntro && (
        <PlayResultOverlay
          resultText={lastResult?.text ?? null}
          resultEvent={lastResult?.event ?? null}
          resultTs={lastResult?.ts ?? null}
          delayMs={1000}
        />
      )}

      {/* Mazo táctico */}
      {!showGameIntro && (
        <TacticalHand
          tacticalHand={tacticalHand}
          selectedTacticalId={selectedTacticalId}
          role={role}
          isIBB={selectedPitch === 'IBB'}
          disabled={isAwaitingResult || isProcessing || inningTransition?.visible || (role === 'PITCHER' && !pitcherCard)}
          onSelectTactical={(id: string) =>
            setSelectedTacticalId(selectedTacticalId === id ? null : id)
          }
          onSubmitPlay={handleSubmitPlay}
        />
      )}

      {/* Modal de Finalizar Partido */}
      <QuitGameModal
        isOpen={showQuitModal}
        onConfirm={handleQuitGame}
        onCancel={() => setShowQuitModal(false)}
        isLoading={isQuittingGame}
      />

      {/* Modal de Cambio de Pitcher del Rival */}
      {rivalPitcherChangeData && (
        <RivalPitcherChangeModal
          isOpen={showRivalPitcherChangeModal}
          oldPitcher={rivalPitcherChangeData.oldPitcher}
          newPitcher={rivalPitcherChangeData.newPitcher}
          availablePitchers={rivalPitcherChangeData.availablePitchers}
          onSelectPitcher={async (pitcherId) => {
            // TODO: Send pitcher change request to backend
            console.log('🎯 Selected rival pitcher:', pitcherId);
          }}
          onAccept={() => {
            setShowRivalPitcherChangeModal(false);
          }}
        />
      )}
    </div>
  );
};
