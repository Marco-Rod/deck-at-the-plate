/**
 * StadiumShowcaseScreen — Pantalla principal de juego en tiempo real
 * ===================================================================
 * Compone todos los subcomponentes del estadio y los conecta al backend
 * mediante el hook useStadiumSocket (WebSocket + REST).
 *
 * Props:
 *   gameId  — ID real de la partida creada en el backend (ej. "game_a1b2c3d4").
 *             Se pasa desde App.jsx tras confirmar el roster.
 *   userId  — ID del usuario autenticado. El servidor lo usa para aplicar
 *             el Fog of War (ocultar el pitch al bateador).
 *   onBack  — Callback para volver al Lobby.
 */

import React, { useState } from 'react';
import { Scoreboard } from './Scoreboard';
import { PitchZoneGrid } from './PitchZoneGrid';
import { PlayerCard } from './PlayerCard';
import { TacticalHand } from './TacticalHand';
import { PlayResultOverlay } from './PlayResultOverlay';
import { useStadiumSocket } from '../../hooks/useStadiumSocket';
import {
  PitchType,
  PlayerData,
  PlayerRole,
  TacticalCard,
} from '../../types/stadium';

interface StadiumShowcaseScreenProps {
  /** ID real de la partida (ej. "game_a1b2c3d4"). Requerido para WS y REST. */
  gameId: string | null;
  /** ID del usuario autenticado. Determina el Fog of War en el servidor. */
  userId: string;
  onBack: () => void;
}

export const StadiumShowcaseScreen: React.FC<StadiumShowcaseScreenProps> = ({
  gameId,
  userId,
  onBack,
}) => {
  const [role, setRole] = useState<PlayerRole>('PITCHER');
  const [selectedZone, setSelectedZone] = useState<number>(5);
  const [selectedPitch, setSelectedPitch] = useState<PitchType>('FF');
  const [selectedTacticalId, setSelectedTacticalId] = useState<string | null>(null);

  // Hook de comunicación con el backend (WS + REST)
  const { gameState, lastResult, hasPitched, isConnected, sendPitch, sendSwing, sendTactic } =
    useStadiumSocket(gameId ?? '', userId);

  // Datos demo del pitcher (se reemplazarán con datos reales del gameState)
  const pitcherCard: PlayerData = {
    id: 'p1',
    name: 'Y. YAMAMOTO',
    number: '18',
    overall: 91,
    position: 'SP',
    photo: 'https://a.espncdn.com/combiner/i?img=/i/headshots/mlb/players/full/4982607.png&w=350&h=254',
    stats: [
      { label: 'VEL', val: 96 },
      { label: 'CTL', val: 92 },
      { label: 'MOV', val: 88 },
      { label: 'STA', val: 85 },
    ],
  };

  const batterCard: PlayerData = {
    id: 'b1',
    name: 'AARON JUDGE',
    number: '99',
    overall: 96,
    position: 'CF',
    photo: 'https://a.espncdn.com/combiner/i?img=/i/headshots/mlb/players/full/33192.png&w=350&h=254',
    stats: [
      { label: 'PWR', val: 99 },
      { label: 'CON', val: 86 },
      { label: 'VIS', val: 82 },
      { label: 'SPD', val: 74 },
    ],
  };

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
      await sendSwing('NORMAL', selectedZone, selectedPitch);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 bg-[#121619] text-[#F7F5F0] relative overflow-hidden select-none">
      {/* Header */}
      <header className="w-full flex justify-between items-center border-b-2 border-[#C5A059]/40 pb-3 mb-3 z-30">
        <div>
          <h2 className="font-sports text-3xl text-[#F7F5F0] uppercase tracking-wider leading-none">
            CAMPO DE JUEGO
          </h2>
          <span className={`font-mono text-[10px] ${isConnected ? 'text-emerald-400' : 'text-red-400'}`}>
            {isConnected ? '● CONECTADO EN VIVO' : '○ DESCONECTADO'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* Selector de rol temporal — en PvP real el rol lo determina el servidor */}
          <button
            type="button"
            onClick={() => setRole(r => r === 'PITCHER' ? 'BATTER' : 'PITCHER')}
            className="bg-[#1A3323] border border-[#C5A059] px-3 py-1.5 font-mono text-xs text-[#C5A059]"
          >
            ROL: {role}
          </button>
          <button
            type="button"
            onClick={onBack}
            className="bg-[#0A0D0F] border border-[#C5A059] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold"
          >
            ⚙️ LOBBY
          </button>
        </div>
      </header>

      {/* Marcador */}
      {gameState && <Scoreboard gameState={gameState} role={role} />}

      {/* Campo Principal */}
      <main className="w-full max-w-6xl mx-auto border-2 border-[#C5A059]/50 p-6 relative flex justify-between items-center min-h-[500px] shadow-2xl overflow-hidden rounded-sm bg-[#0A0D0F]">
        <PlayerCard player={pitcherCard} role="PITCHER" />
        <PitchZoneGrid
          role={role}
          selectedZone={selectedZone}
          selectedPitch={selectedPitch}
          onSelectZone={setSelectedZone}
          onSelectPitch={setSelectedPitch}
        />
        <PlayerCard player={batterCard} role="BATTER" />

        {/* Aviso visible solo para el bateador cuando el pitcher ya pichó */}
        {hasPitched && role === 'BATTER' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-[#C5A059] text-[#0A0D0F] px-4 py-1 font-mono text-xs font-bold z-20">
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
