import React, { useState } from 'react';
import { soundFx } from '../utils/audioManager';
import { PlayerCard } from '../components/cards/PlayerCard';

export const RosterSelectionScreen = ({ onConfirmRoster, onBack }) => {
  // Datos simulados (Se conectarán con GET /api/v1/cards/players)
  const mockPitchers = [
    { id: "p1", name: "S. Ohtani", number: "17", overall: 94, velocity: 99, control: 88 },
    { id: "p2", name: "Y. Yamamoto", number: "18", overall: 91, velocity: 96, control: 92 },
  ];

  const mockBatters = [
    { id: "b1", name: "Ichiro S.", number: "51", overall: 93, contact: 98, power: 65, position: "OF" },
    { id: "b2", name: "H. Matsui", number: "55", overall: 90, contact: 82, power: 94, position: "DH" },
    { id: "b3", name: "K. Takahashi", number: "1", overall: 85, contact: 85, power: 78, position: "SS" },
    { id: "b4", name: "S. Suzuki", number: "27", overall: 87, contact: 88, power: 81, position: "RF" },
  ];

  const [selectedPitcher, setSelectedPitcher] = useState(mockPitchers[0]);
  const [lineup, setLineup] = useState(mockBatters);

  const handleStartGame = () => {
    soundFx.playGameStart();
    onConfirmRoster({
      pitcherId: selectedPitcher.id,
      lineupIds: lineup.map(b => b.id),
      tacticsDeck: ["t1", "t2", "t3", "t4", "t5"]
    });
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-between p-4 bg-[#121619]">
      {/* Cabecera */}
      <div className="w-full max-w-4xl flex justify-between items-center border-b-2 border-[#C5A059] pb-3 mb-4">
        <div>
          <span className="font-mono text-xs text-[#C5A059] uppercase block">PREPARACIÓN DE ESCUADRA</span>
          <h2 className="font-sports text-4xl text-[#F7F5F0] uppercase leading-none">SELECCIÓN DE ROSTER</h2>
        </div>
        <button
          onClick={() => { soundFx.playClick(); onBack(); }}
          className="border border-[#2C3E35] hover:border-[#C5A059] px-4 py-2 font-mono text-xs text-[#E6DFD3] transition-colors"
        >
          VOLVER AL LOBBY
        </button>
      </div>

      {/* Contenido Principal */}
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6 my-auto">
        {/* Selección de Pícher Abridor */}
        <div className="bg-[#121619] border-2 border-[#C5A059] p-4 shadow-2xl">
          <h3 className="font-sports text-2xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-4">
            LANZADOR ABRIDOR
          </h3>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {mockPitchers.map((pitcher) => (
              <PlayerCard
                key={pitcher.id}
                player={pitcher}
                role="PITCHER"
                isSelected={selectedPitcher?.id === pitcher.id}
                onClick={(p) => setSelectedPitcher(p)}
              />
            ))}
          </div>
        </div>

        {/* Selección de Bateadores / Lineup */}
        <div className="bg-[#121619] border-2 border-[#C5A059] p-4 shadow-2xl">
          <h3 className="font-sports text-2xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-4">
            LINEUP ACTIVO ({lineup.length}/9)
          </h3>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {lineup.map((batter) => (
              <PlayerCard
                key={batter.id}
                player={batter}
                role="BATTER"
                isSelected={true}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Botón de Confirmación */}
      <div className="w-full max-w-4xl mt-6">
        <button
          onClick={handleStartGame}
          onMouseEnter={() => soundFx.playCardSelect()}
          className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] text-[#F7F5F0] border-2 border-[#C5A059] py-4 font-sports text-3xl tracking-widest transition-all active:scale-95 shadow-2xl"
        >
          CONFIRMAR ROSTER Y SALIR AL CAMPO
        </button>
      </div>
    </div>
  );
};