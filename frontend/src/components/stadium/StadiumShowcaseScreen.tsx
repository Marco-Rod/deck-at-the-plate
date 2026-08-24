import React, { useState, useEffect } from 'react';
import { Scoreboard } from './Scoreboard';
import { PitchZoneGrid } from './PitchZoneGrid';
import { PlayerCard } from './PlayerCard';
import { TacticalHand } from './TacticalHand';
import { PlayResultOverlay } from './PlayResultOverlay';
import { GameOverModal } from './GameOverModal'; // <-- Importar el nuevo modal
import { useStadiumSocket } from '../../hooks/useStadiumSocket';
import { cards as cardsApi, user as userApi } from '../../utils/api';
import {
  PitchType,
  PlayerData,
  PlayerRole,
  TacticalCard,
} from '../../types/stadium';

interface StadiumShowcaseScreenProps {
  gameId: string | null;
  userId: string;
  onBack: () => void;
}

export const StadiumShowcaseScreen: React.FC<StadiumShowcaseScreenProps> = ({
  gameId,
  userId,
  onBack,
}) => {
  const [selectedZone, setSelectedZone] = useState<number>(5);
  const [selectedPitch, setSelectedPitch] = useState<PitchType>('4-SEAM');
  const [selectedSwing, setSelectedSwing] = useState<'NORMAL' | 'POWER' | 'TAKE' | 'BUNT'>('NORMAL');
  const [selectedTacticalId, setSelectedTacticalId] = useState<string | null>(null);

  const [pitcherCard, setPitcherCard] = useState<PlayerData | null>(null);
  const [batterCard, setBatterCard] = useState<PlayerData | null>(null);
  const [userTeam, setUserTeam] = useState<any>(null);

  const { gameState, lastResult, hasPitched, isConnected, sendPitch, sendSwing, sendTactic } =
    useStadiumSocket(gameId ?? '', userId);

  const role: PlayerRole = gameState?.isTopInning ? 'PITCHER' : 'BATTER';

  useEffect(() => {
    if (!userId) return;
    userApi.getTeam(userId).then(setUserTeam).catch(() => null);
  }, [userId]);

  useEffect(() => {
    if (gameState?.activePitcherId) {
      cardsApi.getCard(gameState.activePitcherId)
        .then((c: any) => {
          if (c) {
            setPitcherCard({
              id: c.id,
              name: c.name,
              number: c.number || '17',
              overall: c.overall || 99,
              position: c.position || 'SP',
              photo: c.photo,
              repertoire: c.repertoire || [],
              stats: [
                { label: 'VEL', val: c.velocity || 98 },
                { label: 'CTL', val: c.control || 88 },
                { label: 'MOV', val: c.movement || 92 },
                { label: 'STA', val: c.stamina || 80 },
              ]
            });
            if (c.repertoire && c.repertoire.length > 0) {
              setSelectedPitch(c.repertoire[0].pitch_type);
            }
          }
        })
        .catch(() => null);
    }

    if (gameState?.activeBatterId) {
      cardsApi.getCard(gameState.activeBatterId)
        .then((c: any) => {
          if (c) {
            setBatterCard({
              id: c.id,
              name: c.name,
              number: c.number || '17',
              overall: c.overall || 99,
              position: c.position || 'DH',
              photo: c.photo,
              stats: [
                { label: 'PWR', val: c.power || 98 },
                { label: 'CON', val: c.contact || 92 },
                { label: 'VIS', val: c.vision || 80 },
                { label: 'SPD', val: c.speed || 80 },
              ]
            });
          }
        })
        .catch(() => null);
    }
  }, [gameState?.activePitcherId, gameState?.activeBatterId]);

  const tacticalHand: TacticalCard[] = [
    {
      id: 't1',
      name: 'RECTA FUEGO',
      cost: 1,
      desc: '+10 VEL en zona alta',
      type: 'PITCH BOOST',
      color: 'border-red-500/80 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]',
      icon: '🔥',
    },
    {
      id: 't2',
      name: 'PICONAZO',
      cost: 2,
      desc: 'Provoca Whiff fuera de zona',
      type: 'SPECIAL',
      color: 'border-[#C5A059] text-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]',
      icon: '〰️',
    },
    {
      id: 't3',
      name: 'PITCHOUT',
      cost: 1,
      desc: 'Sorprende a corredor en robo',
      type: 'DEFENSE',
      color: 'border-blue-400/80 text-blue-300 shadow-[0_0_15px_rgba(96,165,250,0.3)]',
      icon: '🏃',
    },
    {
      id: 't4',
      name: 'TOQUE SUICIDA',
      cost: 2,
      desc: 'Asegura carrera desde 3B',
      type: 'OFFENSE',
      color: 'border-emerald-500/80 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]',
      icon: '🏏',
    },
  ];

  const handleSubmitPlay = async () => {
    if (role === 'PITCHER') {
      if (selectedTacticalId) {
        await sendTactic(selectedTacticalId, 'PITCHER');
        setSelectedTacticalId(null);
      }
      await sendPitch(selectedZone, selectedPitch);
    } else {
      if (selectedTacticalId) {
        await sendTactic(selectedTacticalId, 'BATTER');
        setSelectedTacticalId(null);
      }
      await sendSwing(selectedSwing, selectedZone, selectedPitch);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 bg-[#121619] text-[#F7F5F0] relative overflow-hidden select-none">
      
      {/* MODAL DE FIN DE PARTIDO */}
      {gameState?.isGameOver && (
        <GameOverModal
          winnerMessage={gameState.winnerMessage}
          homeScore={gameState.homeScore}
          awayScore={gameState.awayScore}
          homeTeamName={userTeam?.short_name || 'HOME'}
          awayTeamName="CPU"
          onReturnToLobby={onBack}
        />
      )}

      {/* Header */}
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
            onClick={onBack}
            className="bg-[#0A0D0F] border border-[#C5A059] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold cursor-pointer hover:bg-[#1A3323]"
          >
            ⚙️ LOBBY
          </button>
        </div>
      </header>

      {/* Marcador */}
      {gameState && (
        <Scoreboard 
          gameState={gameState} 
          role={role} 
          homeTeamName={userTeam?.short_name || 'HOME'}
          awayTeamName="CPU"
        />
      )}

      {/* Campo Principal */}
      <main className="w-full max-w-6xl mx-auto border-2 border-[#C5A059]/50 p-6 relative flex justify-between items-center min-h-[500px] shadow-2xl overflow-hidden rounded-sm bg-[#0A0D0F]">
        <PlayerCard player={pitcherCard} role="PITCHER" />
        
        <PitchZoneGrid
          role={role}
          selectedZone={selectedZone}
          selectedPitch={selectedPitch}
          onSelectZone={setSelectedZone}
          onSelectPitch={setSelectedPitch}
          repertoire={pitcherCard?.repertoire}
        />
        
        <PlayerCard player={batterCard} role="BATTER" />

        {hasPitched && role === 'BATTER' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-[#C5A059] text-[#0A0D0F] px-4 py-1 font-mono text-xs font-bold z-20 animate-bounce">
            ¡El lanzador ya pichó! Selecciona tu swing.
          </div>
        )}
      </main>

      {/* Overlay de resultado de jugada */}
      <PlayResultOverlay resultText={lastResult} />

      {/* Mazo táctico en mano */}
      <TacticalHand
        tacticalHand={tacticalHand}
        selectedTacticalId={selectedTacticalId}
        role={role}
        isIBB={selectedPitch === 'IBB'}
        onSelectTactical={(id: string) =>
          setSelectedTacticalId(selectedTacticalId === id ? null : id)
        }
        onSubmitPlay={handleSubmitPlay}
      />
    </div>
  );
};