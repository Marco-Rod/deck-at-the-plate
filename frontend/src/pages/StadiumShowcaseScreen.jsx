import React, { useState } from 'react';
import { soundFx } from '../utils/audioManager';

export const StadiumShowcaseScreen = ({ onBack }) => {
  const [role, setRole] = useState('PITCHER');
  const [selectedZone, setSelectedZone] = useState(5);
  const [selectedPitch, setSelectedPitch] = useState('4-SEAM');
  const [selectedTactical, setSelectedTactical] = useState(null);
  const [hoveredBase, setHoveredBase] = useState(null);

  // Estados de Menús, Reacciones y Lineups
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isEmoteOpen, setIsEmoteOpen] = useState(false);
  const [isLineupOpen, setIsLineupOpen] = useState(false);
  const [activeEmote, setActiveEmote] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);

  const runnersData = {
    b1: { name: "Ichiro Suzuki", number: "51", speed: 99, pos: "CF", active: true },
    b2: { name: "Shohei Ohtani", number: "17", speed: 92, pos: "DH", active: false },
    b3: { name: "Mookie Betts", number: "50", speed: 88, pos: "SS", active: true },
  };

  const homeLineup = [
    { order: 1, name: "M. Betts", pos: "SS", ovr: 90, status: "ON_BASE" },
    { order: 2, name: "S. Ohtani", pos: "DH", ovr: 99, status: "OUT" },
    { order: 3, name: "F. Freeman", pos: "1B", ovr: 91, status: "ON_BASE" },
    { order: 4, name: "A. Judge", pos: "CF", ovr: 96, status: "AT_BAT" },
    { order: 5, name: "J. Soto", pos: "RF", ovr: 93, status: "ON_DECK" },
    { order: 6, name: "G. Stanton", pos: "LF", ovr: 85, status: "WAITING" },
    { order: 7, name: "A. Volpe", pos: "2B", ovr: 81, status: "WAITING" },
    { order: 8, name: "A. Wells", pos: "C", ovr: 79, status: "WAITING" },
    { order: 9, name: "J. Chisholm", pos: "3B", ovr: 83, status: "WAITING" },
  ];

  const tacticalHand = [
    {
      id: "t1", name: "RECTA FUEGO", cost: 1, desc: "+10 MPH en zona alta", type: "PITCH BOOST",
      color: "border-red-500/80 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]",
      icon: "🔥"
    },
    {
      id: "t2", name: "PICONAZO", cost: 2, desc: "Provoca Whiff fuera de zona", type: "SPECIAL",
      color: "border-[#C5A059] text-[#C5A059] shadow-[0_0_15px_rgba(197,160,89,0.3)]",
      icon: "〰️"
    },
    {
      id: "t3", name: "PITCHOUT", cost: 1, desc: "Sorprende a corredor en robo", type: "DEFENSE",
      color: "border-blue-400/80 text-blue-300 shadow-[0_0_15px_rgba(96,165,250,0.3)]",
      icon: "🏃"
    },
    {
      id: "t4", name: "TOQUE SUICIDA", cost: 2, desc: "Asegura carrera desde 3B", type: "OFFENSE",
      color: "border-emerald-500/80 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]",
      icon: "🏏"
    },
  ];

  const emotesList = [
    { id: 'fire', emoji: '🔥', label: '¡FUEGO!' },
    { id: 'power', emoji: '💥', label: '¡PODER!' },
    { id: 'paint', emoji: '🎯', label: '¡PINTADA!' },
    { id: 'whiff', emoji: '😱', label: '¡WHIFF!' },
    { id: 'clap', emoji: '👏', label: '¡BUENA!' },
    { id: 'popcorn', emoji: '🍿', label: '¡DRAMA!' },
  ];

  // Datos simulados con métricas detalladas estilo réplica
  const pitcherCard = {
    name: "Y. YAMAMOTO", number: "18", ovr: 91, pos: "SP",
    photo: "https://a.espncdn.com/combiner/i?img=/i/headshots/mlb/players/full/4982607.png&w=350&h=254",
    stats: [
      { label: "VEL", val: 96 },
      { label: "CTL", val: 92 },
      { label: "MOV", val: 88 },
      { label: "STA", val: 85 },
    ]
  };

  const batterCard = {
    name: "AARON JUDGE", number: "99", ovr: 96, pos: "CF",
    photo: "https://a.espncdn.com/combiner/i?img=/i/headshots/mlb/players/full/33192.png&w=350&h=254",
    stats: [
      { label: "PWR", val: 99 },
      { label: "CON", val: 86 },
      { label: "VIS", val: 82 },
      { label: "SPD", val: 74 },
    ]
  };

  const sendEmote = (emote, senderRole = role) => {
    soundFx.playClick();
    setActiveEmote({ ...emote, sender: senderRole });
    setIsEmoteOpen(false);
    setTimeout(() => setActiveEmote(null), 3500);
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-4 bg-[#121619] text-[#F7F5F0] relative overflow-hidden select-none">
      
      {/* Header Limpio */}
      <header className="w-full flex flex-wrap justify-between items-center border-b-2 border-[#C5A059]/40 pb-3 mb-3 gap-3 z-30">
        <div>
          <h2 className="font-sports text-3xl text-[#F7F5F0] uppercase tracking-wider leading-none">CAMPO DE JUEGO & CARTAS EN MANO</h2>
        </div>

        <div className="flex items-center gap-3">
          {/* Selector de Rol */}
          <div className="flex items-center gap-2 bg-[#0A0D0F] p-1.5 border border-[#2C3E35]">
            <span className="font-mono text-[10px] text-[#C5A059]">ROL:</span>
            <button
              onClick={() => { soundFx.playClick(); setRole('PITCHER'); }}
              className={`px-2 py-0.5 font-mono text-[10px] uppercase ${role === 'PITCHER' ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059]' : 'text-[#E6DFD3] opacity-50'}`}
            >
              ⚾ Pitching
            </button>
            <button
              onClick={() => { soundFx.playClick(); setRole('BATTER'); }}
              className={`px-2 py-0.5 font-mono text-[10px] uppercase ${role === 'BATTER' ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059]' : 'text-[#E6DFD3] opacity-50'}`}
            >
              💥 Batting
            </button>
          </div>

          <button
            onClick={() => { soundFx.playClick(); setIsLineupOpen(!isLineupOpen); }}
            className="bg-[#0A0D0F] border border-[#2C3E35] hover:border-[#C5A059] px-3 py-2 font-mono text-xs text-[#E6DFD3] flex items-center gap-2 transition-colors"
          >
            📋 LINEUPS
          </button>

          <div className="relative">
            <button
              onClick={() => { soundFx.playClick(); setIsEmoteOpen(!isEmoteOpen); }}
              className="bg-[#0A0D0F] border border-[#C5A059] hover:bg-[#1A3323] px-3 py-2 font-mono text-xs text-[#F7F5F0] flex items-center gap-2 transition-colors"
            >
              💬 REACCIONES
            </button>

            {isEmoteOpen && (
              <div className="absolute top-12 right-0 bg-[#0A0D0F]/95 border border-[#C5A059] p-2 flex flex-col gap-1 z-50 shadow-2xl w-44 backdrop-blur-md">
                {emotesList.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => sendEmote(e)}
                    className="p-2 border border-[#2C3E35] hover:border-[#C5A059] hover:bg-[#1A3323] flex items-center gap-3 font-mono text-xs text-left transition-all hover:pl-3"
                  >
                    <span className="text-xl">{e.emoji}</span>
                    <span className="text-[#E6DFD3] font-bold">{e.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="relative">
            <button
              onClick={() => { soundFx.playClick(); setIsMenuOpen(!isMenuOpen); }}
              className="bg-[#0A0D0F] border border-[#C5A059] hover:bg-[#1A3323] px-4 py-2 font-mono text-xs text-[#C5A059] font-bold transition-colors flex items-center gap-1"
            >
              ⚙️ MENÚ ▾
            </button>

            {isMenuOpen && (
              <div className="absolute top-12 right-0 bg-[#0A0D0F]/95 border border-[#C5A059] p-2 flex flex-col gap-2 z-50 shadow-2xl w-56 backdrop-blur-md font-mono text-xs">
                <button
                  onClick={() => { setSoundEnabled(!soundEnabled); soundFx.playClick(); }}
                  className="p-2.5 border border-[#2C3E35] hover:border-[#C5A059] hover:bg-[#1A3323] flex justify-between items-center text-left"
                >
                  <span>SONIDO (SFX)</span>
                  <span>{soundEnabled ? '🔊 ON' : '🔇 MUTE'}</span>
                </button>
                <button
                  onClick={() => { soundFx.playClick(); setIsMenuOpen(false); }}
                  className="p-2.5 border border-[#2C3E35] hover:border-[#C5A059] hover:bg-[#1A3323] text-left"
                >
                  ▶ REANUDAR PARTIDO
                </button>
                <button
                  onClick={() => { soundFx.playClick(); onBack(); }}
                  className="p-2.5 border border-red-500/50 hover:border-red-500 bg-red-950/30 text-red-400 text-left font-bold"
                >
                  🏳️ SALIR AL LOBBY
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Scoreboard Superior Exacto al Boceto */}
      <div className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 px-6 py-2.5 grid grid-cols-3 items-center shadow-2xl mb-3">
        
        {/* Columna 1: Entrada y Rol */}
        <div className="flex flex-col justify-center items-start font-mono">
          <span className="text-sm text-[#C5A059] font-bold uppercase tracking-wider">
            4TH BOT • {role === 'PITCHER' ? 'DEFENSA' : 'ATAQUE'}
          </span>
          <span className="text-[10px] text-[#E6DFD3]/60 uppercase tracking-widest">
            STADIUM MATCH
          </span>
        </div>

        {/* Columna 2 (Centro): Marcador Grande */}
        <div className="text-center mx-auto">
          <div className="font-sports text-4xl tracking-widest text-[#F7F5F0]">
            LAD <strong className="text-[#C5A059]">3</strong> - <strong className="text-[#F7F5F0]">1</strong> NYY
          </div>
        </div>

        {/* Columna 3: Conteos + Mini Rombos */}
        <div className="font-mono text-sm flex gap-4 text-[#E6DFD3] font-bold justify-end items-center">
          <span>B: <strong className="text-[#C5A059]">2</strong></span>
          <span>S: <strong className="text-[#C5A059]">1</strong></span>
          <span>O: <strong className="text-[#C5A059]">2</strong></span>
          
          <div className="flex gap-1 ml-2">
            <div className="w-3 h-3 rotate-45 border border-[#C5A059] bg-[#C5A059]" />
            <div className="w-3 h-3 rotate-45 border border-[#2C3E35] bg-[#121619]" />
            <div className="w-3 h-3 rotate-45 border border-[#C5A059] bg-[#C5A059]" />
          </div>
        </div>
      </div>

      {/* Main Field Area con Fondo de Estadio HD */}
      <main className="w-full max-w-6xl mx-auto border-2 border-[#C5A059]/50 p-6 relative flex justify-between items-center min-h-[500px] shadow-2xl overflow-hidden rounded-sm bg-[#0A0D0F]">
        
        {/* Fondo de Estadio con Depth-of-Field */}
        <div 
          className="absolute inset-0 opacity-30 bg-cover bg-center mix-blend-luminosity pointer-events-none scale-105"
          style={{ backgroundImage: `url('https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop')` }}
        />

        {/* LADO IZQUIERDO: Carta del Pitcher HD con Barras de Stats */}
        <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl backdrop-blur-sm">
          <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
            <span className="font-mono text-[10px] text-[#C5A059] font-bold">PÍCHER</span>
            <span className="font-sports text-xl text-[#F7F5F0]">91</span>
          </div>

          <div className="relative h-44 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2">
            <img src={pitcherCard.photo} alt="Picher" className="w-full h-full object-cover object-top" />
            <span className="absolute bottom-1 left-2 font-sports text-2xl text-[#C5A059] drop-shadow-md">#{pitcherCard.number}</span>
            <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">{pitcherCard.pos}</span>
          </div>

          <h4 className="font-sports text-xl text-[#F7F5F0] leading-none mb-1">{pitcherCard.name}</h4>
          <div className="font-mono text-[10px] text-[#E6DFD3] flex gap-3 mb-3 border-b border-[#2C3E35] pb-2">
            <span>VEL: 96</span>
            <span>CTL: 92</span>
          </div>

          {/* Barras de Atributos */}
          <div className="space-y-1.5 font-mono text-[9px]">
            <span className="text-[#C5A059] font-bold block mb-1">ESTADÍSTICAS</span>
            {pitcherCard.stats.map(s => (
              <div key={s.label} className="flex items-center justify-between gap-2">
                <span className="w-6 text-[#E6DFD3]">{s.label}</span>
                <div className="flex-1 h-1.5 bg-[#121619] border border-[#2C3E35]">
                  <div className="h-full bg-[#C5A059]" style={{ width: `${s.val}%` }} />
                </div>
                <span className="w-5 text-right">{s.val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* REACCIÓN FLOTANTE LADO IZQUIERDO */}
        {activeEmote && activeEmote.sender === 'PITCHER' && (
          <div className="z-30 absolute left-[26%] top-1/2 -translate-y-1/2 animate-bounce flex items-center">
            <div className="bg-[#0A0D0F]/95 border-2 border-[#C5A059] rounded-2xl px-5 py-3 flex items-center gap-3 shadow-[0_0_30px_rgba(197,160,89,0.9)] backdrop-blur-md">
              <span className="text-5xl">{activeEmote.emoji}</span>
              <span className="font-sports text-2xl text-[#F7F5F0] tracking-wide whitespace-nowrap">{activeEmote.label}</span>
            </div>
          </div>
        )}

        {/* CENTRO: Widget de Bases + Selector + Grilla 3x3 */}
        <div className="z-10 flex flex-col items-center gap-3 my-auto">
          
          {/* Widget del Diamante */}
          <div className="bg-[#0A0D0F]/95 border border-[#C5A059] px-5 py-1.5 flex items-center gap-3 shadow-xl">
            <div className="relative w-8 h-8 flex items-center justify-center">
              <div
                onMouseEnter={() => setHoveredBase('b2')}
                onMouseLeave={() => setHoveredBase(null)}
                className={`absolute top-0 w-3 h-3 rotate-45 border transition-colors cursor-pointer ${runnersData.b2.active ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`}
              />
              <div
                onMouseEnter={() => setHoveredBase('b3')}
                onMouseLeave={() => setHoveredBase(null)}
                className={`absolute left-0 w-3 h-3 rotate-45 border transition-colors cursor-pointer ${runnersData.b3.active ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`}
              />
              <div
                onMouseEnter={() => setHoveredBase('b1')}
                onMouseLeave={() => setHoveredBase(null)}
                className={`absolute right-0 w-3 h-3 rotate-45 border transition-colors cursor-pointer ${runnersData.b1.active ? 'bg-[#C5A059] border-[#F7F5F0]' : 'border-[#2C3E35] bg-[#121619]'}`}
              />
              <div className="absolute bottom-0 w-2 h-2 rotate-45 border border-[#2C3E35] bg-[#0A0D0F] pointer-events-none" />
            </div>

            <div className="font-mono text-[9px]">
              {hoveredBase && runnersData[hoveredBase].active ? (
                <div className="text-[#F7F5F0]">
                  <span className="text-[#C5A059] font-bold block leading-tight">{runnersData[hoveredBase].name}</span>
                  <span>SPD: {runnersData[hoveredBase].speed}</span>
                </div>
              ) : (
                <span className="text-[#C5A059] block font-bold text-center">BASES: 1B, 3B</span>
              )}
            </div>
          </div>

          {/* Selector de Pitcheo */}
          {role === 'PITCHER' && (
            <div className="flex gap-1 bg-[#0A0D0F] p-1 border border-[#2C3E35]">
              {['4-SEAM', 'SLIDER', 'CURVE', 'CHANGE'].map((pitch) => (
                <button
                  key={pitch}
                  onClick={() => { soundFx.playClick(); setSelectedPitch(pitch); }}
                  className={`px-3 py-1 font-mono text-[10px] uppercase transition-colors ${
                    selectedPitch === pitch ? 'bg-[#1A3323] text-[#C5A059] border border-[#C5A059]' : 'text-[#E6DFD3] opacity-60'
                  }`}
                >
                  {pitch}
                </button>
              ))}
              <button
                onClick={() => { soundFx.playClick(); setSelectedPitch('IBB'); }}
                className={`px-2 py-1 font-mono text-[10px] uppercase transition-colors ${
                  selectedPitch === 'IBB' ? 'bg-[#C5A059] text-[#121619] font-bold border border-[#F7F5F0]' : 'text-[#C5A059] border border-[#C5A059]/40 opacity-80'
                }`}
              >
                IBB (INTENC.)
              </button>
            </div>
          )}

          {/* Grid 3x3 */}
          <div className={`bg-[#0A0D0F]/95 p-4 border-2 border-[#C5A059] shadow-2xl text-center transition-all ${selectedPitch === 'IBB' ? 'opacity-40 pointer-events-none' : ''}`}>
            <span className="font-mono text-[10px] text-[#C5A059] uppercase block mb-2 font-bold">
              {role === 'PITCHER' ? `UBICACIÓN: ZONA Z${selectedZone}` : 'PREDICE LA ZONA DE SWING'}
            </span>
            <div className="grid grid-cols-3 gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((z) => (
                <button
                  key={z}
                  onClick={() => { soundFx.playClick(); setSelectedZone(z); }}
                  className={`w-16 h-16 border flex items-center justify-center font-mono text-xs transition-all ${
                    selectedZone === z
                      ? 'border-[#C5A059] bg-[#1A3323] text-[#C5A059] font-bold shadow-[0_0_15px_rgba(197,160,89,0.6)]'
                      : 'border-[#2C3E35] text-[#E6DFD3] hover:border-[#C5A059]/60'
                  }`}
                >
                  Z{z}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* REACCIÓN FLOTANTE LADO DERECHO */}
        {activeEmote && activeEmote.sender === 'BATTER' && (
          <div className="z-30 absolute right-[26%] top-1/2 -translate-y-1/2 animate-bounce flex items-center">
            <div className="bg-[#0A0D0F]/95 border-2 border-[#C5A059] rounded-2xl px-5 py-3 flex items-center gap-3 shadow-[0_0_30px_rgba(197,160,89,0.9)] backdrop-blur-md">
              <span className="text-5xl">{activeEmote.emoji}</span>
              <span className="font-sports text-2xl text-[#F7F5F0] tracking-wide whitespace-nowrap">{activeEmote.label}</span>
            </div>
          </div>
        )}

        {/* LADO DERECHO: Carta del Bateador HD con Barras de Stats */}
        <div className="z-10 bg-[#0A0D0F]/90 border border-[#C5A059] p-3 w-60 shadow-2xl backdrop-blur-sm">
          <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
            <span className="font-mono text-[10px] text-[#C5A059] font-bold">BATEADOR</span>
            <span className="font-sports text-xl text-[#F7F5F0]">96</span>
          </div>

          <div className="relative h-44 w-full bg-[#121619] border border-[#2C3E35] overflow-hidden mb-2">
            <img src={batterCard.photo} alt="Bateador" className="w-full h-full object-cover object-top" />
            <span className="absolute bottom-1 left-2 font-sports text-2xl text-[#C5A059] drop-shadow-md">#{batterCard.number}</span>
            <span className="absolute bottom-1 right-2 font-mono text-[10px] text-[#E6DFD3]">{batterCard.pos}</span>
          </div>

          <h4 className="font-sports text-xl text-[#F7F5F0] leading-none mb-1">{batterCard.name}</h4>
          <div className="font-mono text-[10px] text-[#E6DFD3] flex gap-3 mb-3 border-b border-[#2C3E35] pb-2">
            <span>PWR: 99</span>
            <span>CON: 86</span>
          </div>

          {/* Barras de Atributos */}
          <div className="space-y-1.5 font-mono text-[9px]">
            <span className="text-[#C5A059] font-bold block mb-1">ESTADÍSTICAS</span>
            {batterCard.stats.map(s => (
              <div key={s.label} className="flex items-center justify-between gap-2">
                <span className="w-6 text-[#E6DFD3]">{s.label}</span>
                <div className="flex-1 h-1.5 bg-[#121619] border border-[#2C3E35]">
                  <div className="h-full bg-[#C5A059]" style={{ width: `${s.val}%` }} />
                </div>
                <span className="w-5 text-right">{s.val}</span>
              </div>
            ))}
          </div>
        </div>

      </main>

      {/* Dock Inferior Exacto con Iconos Ilustrados */}
      <footer className="w-full max-w-6xl mx-auto bg-[#0A0D0F] border border-[#C5A059]/60 p-3.5 flex flex-col md:flex-row justify-between items-center gap-4 mt-3 shadow-2xl">
        <div className="flex flex-col">
          <span className="font-mono text-xs text-[#C5A059] uppercase font-bold">CARTAS TÁCTICAS EN MANO</span>
          <span className="font-mono text-[10px] text-[#E6DFD3]/70">SELECCIONA PARA ACTIVAR TÁCTICA EN LA JUGADA</span>
        </div>

        {/* Despliegue de Cartas Tácticas con Iluminación */}
        <div className="flex gap-3 overflow-x-auto py-1">
          {tacticalHand.map((card) => (
            <div
              key={card.id}
              onClick={() => {
                soundFx.playCardSelect();
                setSelectedTactical(selectedTactical === card.id ? null : card.id);
              }}
              className={`bg-[#0A0D0F] border-2 ${card.color} ${
                selectedTactical === card.id ? 'ring-2 ring-[#C5A059] -translate-y-2' : ''
              } hover:-translate-y-1 p-3 w-40 text-center cursor-pointer transition-all shadow-xl flex flex-col justify-between h-36`}
            >
              <div>
                <div className="flex justify-between items-center font-mono text-[9px] border-b border-[#2C3E35] pb-1 mb-2">
                  <span className="font-bold">{card.type}</span>
                  <span>⚡{card.cost}</span>
                </div>
                <div className="text-3xl my-1">{card.icon}</div>
                <h5 className="font-sports text-base text-[#F7F5F0] leading-tight uppercase font-bold">
                  {card.name}
                </h5>
              </div>
              <p className="font-mono text-[9px] text-[#E6DFD3] leading-tight mt-1">
                {card.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Botón Lanzar con Etiqueta Inferior */}
        <div className="flex flex-col items-center">
          <button
            onClick={() => soundFx.playGameStart()}
            className="bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] px-8 py-3.5 font-sports text-3xl text-[#F7F5F0] tracking-widest shadow-xl transition-all active:scale-95 flex items-center gap-3"
          >
            {role === 'PITCHER' ? 'LANZAR ⚾' : 'BATEAR 💥'}
          </button>
          <span className="font-mono text-[9px] text-[#C5A059] uppercase tracking-wider mt-1">
            CONFIRMA LA JUGADA
          </span>
        </div>
      </footer>

      {/* Drawer de Lineups */}
      {isLineupOpen && (
        <div className="fixed inset-0 bg-[#0A0D0F]/85 backdrop-blur-sm z-50 flex justify-end">
          <div className="bg-[#121619] border-l-2 border-[#C5A059] w-full max-w-sm p-5 flex flex-col justify-between shadow-2xl animate-fade-in">
            <div>
              <div className="flex justify-between items-center border-b border-[#2C3E35] pb-3 mb-4">
                <h3 className="font-sports text-2xl text-[#F7F5F0] uppercase">📋 ORDEN AL BATE</h3>
                <button
                  onClick={() => setIsLineupOpen(false)}
                  className="text-[#C5A059] font-mono text-xl"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-2 font-mono text-xs">
                {homeLineup.map((player) => (
                  <div
                    key={player.order}
                    className={`p-2.5 border flex justify-between items-center transition-colors ${
                      player.status === 'AT_BAT'
                        ? 'bg-[#1A3323] border-[#C5A059] text-[#C5A059] font-bold'
                        : player.status === 'ON_DECK'
                        ? 'bg-[#121619] border-[#C5A059]/60 text-[#F7F5F0]'
                        : 'bg-[#0A0D0F] border-[#2C3E35] text-[#E6DFD3] opacity-70'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-5 text-center text-[#C5A059] font-bold">#{player.order}</span>
                      <div>
                        <span className="block">{player.name} ({player.pos})</span>
                        <span className="text-[9px] text-[#E6DFD3]">OVR {player.ovr}</span>
                      </div>
                    </div>
                    
                    <span className="text-[9px] uppercase px-1.5 py-0.5 border border-[#2C3E35]">
                      {player.status === 'AT_BAT' ? '🏏 AL BATE' : player.status === 'ON_DECK' ? '⚾ EN ESPERA' : player.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => setIsLineupOpen(false)}
              className="w-full bg-[#1A3323] border border-[#C5A059] py-2.5 font-mono text-xs text-[#F7F5F0] mt-4"
            >
              CERRAR LINEUP
            </button>
          </div>
        </div>
      )}

    </div>
  );
};