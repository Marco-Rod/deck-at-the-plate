import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';
import { PlayerCard } from '../components/cards/PlayerCard';

export const CardShowcaseScreen = ({ onBack }) => {
  const { t } = useTranslation();

  // Datos simulados estructurados por posición en el Diamante
  const teamRoster = {
    P: { id: "p1", name: "S. Ohtani", number: "17", overall: 95, velocity: 99, control: 88, position: "P", role: "PITCHER" },
    C: { id: "b5", name: "K. Johjima", number: "2", overall: 86, contact: 80, power: 84, position: "C", role: "BATTER" },
    "1B": { id: "b2", name: "H. Matsui", number: "55", overall: 92, contact: 84, power: 96, position: "1B", role: "BATTER" },
    "2B": { id: "b6", name: "M. Iwamura", number: "1", overall: 84, contact: 82, power: 75, position: "2B", role: "BATTER" },
    "3B": { id: "b7", name: "N. Nakamura", number: "5", overall: 88, contact: 78, power: 90, position: "3B", role: "BATTER" },
    SS: { id: "b3", name: "K. Takahashi", number: "6", overall: 85, contact: 85, power: 78, position: "SS", role: "BATTER" },
    LF: { id: "b8", name: "Y. Tsutsugo", number: "25", overall: 83, contact: 75, power: 88, position: "LF", role: "BATTER" },
    CF: { id: "b1", name: "Ichiro S.", number: "51", overall: 94, contact: 99, power: 68, position: "CF", role: "BATTER" },
    RF: { id: "b4", name: "S. Suzuki", number: "27", overall: 87, contact: 88, power: 81, position: "RF", role: "BATTER" },
  };

  const [selectedPos, setSelectedPos] = useState("P");
  const selectedPlayer = teamRoster[selectedPos];

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-6 bg-[#121619]">
      {/* Cabecera Superior */}
      <div className="w-full flex justify-between items-center border-b-2 border-[#C5A059] pb-3 mb-4">
        <div>
          <span className="font-mono text-xs text-[#C5A059] uppercase block">SCOUTING & DEPTH CHART</span>
          <h2 className="font-sports text-4xl text-[#F7F5F0] uppercase leading-none">ROSTER DEL EQUIPO & DIAGRAMA DE CAMPO</h2>
        </div>
        <button
          onClick={() => { soundFx.playClick(); onBack(); }}
          className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#1A3323] px-5 py-2 font-mono text-xs text-[#F7F5F0] transition-colors"
        >
          VOLVER AL LOBBY
        </button>
      </div>

      {/* Grid Principal de 2 Columnas (Diamante a la izquierda, Carta/Detalles a la derecha) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 my-auto items-center">
        
        {/* Lado Izquierdo: Representación del Diamante de Béisbol (7 columnas en LG) */}
        <div className="lg:col-span-7 bg-[#0A0D0F] border-2 border-[#2C3E35] p-6 relative min-h-[480px] flex flex-col justify-between shadow-2xl">
          <div className="absolute top-3 left-4 font-mono text-xs text-[#C5A059] uppercase">
            ★ ALINEACIÓN DEFENSIVA (DIAMANTE KOSHIEN)
          </div>

          {/* Esquema Posicional del Campo */}
          <div className="relative w-full h-[400px] mt-6 flex flex-col justify-between items-center bg-[#14291D]/30 border border-[#2C3E35]">
            
            {/* Outfield (LF, CF, RF) */}
            <div className="w-full flex justify-around pt-4 px-8">
              {["LF", "CF", "RF"].map((pos) => (
                <PositionTile
                  key={pos}
                  pos={pos}
                  player={teamRoster[pos]}
                  isSelected={selectedPos === pos}
                  onSelect={(p) => setSelectedPos(p)}
                />
              ))}
            </div>

            {/* Infield (3B, SS, 2B, 1B) */}
            <div className="w-full flex justify-between items-center px-16">
              <PositionTile pos="3B" player={teamRoster["3B"]} isSelected={selectedPos === "3B"} onSelect={(p) => setSelectedPos(p)} />
              <div className="flex gap-12">
                <PositionTile pos="SS" player={teamRoster["SS"]} isSelected={selectedPos === "SS"} onSelect={(p) => setSelectedPos(p)} />
                <PositionTile pos="2B" player={teamRoster["2B"]} isSelected={selectedPos === "2B"} onSelect={(p) => setSelectedPos(p)} />
              </div>
              <PositionTile pos="1B" player={teamRoster["1B"]} isSelected={selectedPos === "1B"} onSelect={(p) => setSelectedPos(p)} />
            </div>

            {/* Batería (P, C) */}
            <div className="w-full flex flex-col items-center gap-3 pb-4">
              <PositionTile pos="P" player={teamRoster["P"]} isSelected={selectedPos === "P"} onSelect={(p) => setSelectedPos(p)} />
              <PositionTile pos="C" player={teamRoster["C"]} isSelected={selectedPos === "C"} onSelect={(p) => setSelectedPos(p)} />
            </div>
          </div>
        </div>

        {/* Lado Derecho: Inspección Detallada del Jugador (5 columnas en LG) */}
        <div className="lg:col-span-5 bg-[#121619] border-2 border-[#C5A059] p-6 flex flex-col items-center justify-between shadow-2xl min-h-[480px]">
          <span className="font-mono text-xs text-[#C5A059] uppercase tracking-widest mb-2">
            DETALLE DEL JUGADOR SELECCIONADO
          </span>

          {/* PlayerCard Ampliada */}
          <div className="transform scale-110 my-4">
            <PlayerCard
              player={selectedPlayer}
              role={selectedPlayer.role}
              isSelected={true}
            />
          </div>

          {/* Panel de Estadísticas / Scouting Report */}
          <div className="w-full bg-[#0A0D0F] border border-[#2C3E35] p-4 mt-2">
            <div className="flex justify-between items-center border-b border-[#2C3E35] pb-2 mb-3">
              <h3 className="font-sports text-3xl text-[#F7F5F0] leading-none uppercase">
                {selectedPlayer.name}
              </h3>
              <span className="font-sports text-2xl text-[#C5A059]">
                #{selectedPlayer.number}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 font-mono text-xs text-[#E6DFD3]">
              <div>
                <span className="text-[#C5A059] block">POSICIÓN:</span>
                <span>{selectedPlayer.position}</span>
              </div>
              <div>
                <span className="text-[#C5A059] block">VALORACIÓN GENERAL:</span>
                <span>{selectedPlayer.overall} OVR</span>
              </div>
              {selectedPlayer.role === "PITCHER" ? (
                <>
                  <div>
                    <span className="text-[#C5A059] block">VELOCIDAD:</span>
                    <span>{selectedPlayer.velocity} MPH</span>
                  </div>
                  <div>
                    <span className="text-[#C5A059] block">CONTROL:</span>
                    <span>{selectedPlayer.control} / 99</span>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <span className="text-[#C5A059] block">PODER (PWR):</span>
                    <span>{selectedPlayer.power} / 99</span>
                  </div>
                  <div>
                    <span className="text-[#C5A059] block">CONTACTO (CON):</span>
                    <span>{selectedPlayer.contact} / 99</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

      </div>

      {/* Pie de Página */}
      <div className="font-mono text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-4">
        KOSHIEN DEPTH CHART SYSTEM • 2026
      </div>
    </div>
  );
};

// Componente auxiliar para las casillas en el diamante
const PositionTile = ({ pos, player, isSelected, onSelect }) => {
  return (
    <button
      type="button"
      onClick={() => { soundFx.playCardSelect(); onSelect(pos); }}
      className={`px-3 py-1.5 border transition-all text-center flex flex-col items-center justify-center min-w-[70px] ${
        isSelected
          ? 'bg-[#1A3323] border-[#C5A059] shadow-[0_0_12px_rgba(197,160,89,0.5)] scale-105'
          : 'bg-[#0A0D0F] border-[#2C3E35] opacity-80 hover:opacity-100 hover:border-[#E6DFD3]'
      }`}
    >
      <span className="font-mono text-[9px] text-[#C5A059] uppercase leading-none">{pos}</span>
      <span className="font-sports text-lg text-[#F7F5F0] leading-none mt-0.5">{player?.name.split(' ')[0] || pos}</span>
      <span className="font-mono text-[8px] text-[#E6DFD3]">{player?.overall} OVR</span>
    </button>
  );
};