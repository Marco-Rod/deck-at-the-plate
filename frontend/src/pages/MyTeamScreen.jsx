import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';
import { user as userApi } from '../utils/api';

export const MyTeamScreen = ({ user, onBack }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('LINEUP');
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Cargar inventario real del usuario desde la API
  useEffect(() => {
    if (!user?.userId) return;

    setLoading(true);
    userApi.getInventory(user.userId)
      .then((data) => {
        setInventory(data.inventory || []);
        setError(null);
      })
      .catch((err) => {
        console.error('Error cargando inventario:', err);
        setError('No se pudo cargar el inventario. Verifica tu conexión.');
      })
      .finally(() => setLoading(false));
  }, [user?.userId]);

  // Separar cartas de pitcher y bateadores del inventario
  const pitchers = inventory
    .map(item => item.card)
    .filter(card => ['SP', 'RP', 'TWP'].includes(card?.position));

  const batters = inventory
    .map(item => item.card)
    .filter(card => card && !['SP', 'RP'].includes(card.position));

  // Mazo táctico (datos mock hasta que el endpoint de inventario los incluya)
  const tacticalDeck = [
    { id: "t1", name: "Batazo de Contacto", cost: 1, desc: "+15 CON en conteos de 2 Strikes", type: "BOOST" },
    { id: "t2", name: "Toque Suicida", cost: 2, desc: "Ejecuta toque con corredor en 3B sin importar vel.", type: "PLAY" },
    { id: "t3", name: "Recta de Fuego", cost: 1, desc: "+10 VEL al pichear arriba de la zona", type: "BOOST" },
    { id: "t4", name: "Robo Agresivo", cost: 2, desc: "+20 Velocidad de salto para el corredor", type: "PLAY" },
  ];

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-6 bg-[#121619]">
      {/* Cabecera Superior */}
      <div className="w-full flex justify-between items-center border-b-2 border-[#C5A059] pb-3 mb-4">
        <div>
          <span className="font-mono text-xs text-[#C5A059] uppercase block">GESTIÓN DE INVENTARIO Y ESTRATEGIA</span>
          <h2 className="font-sports text-4xl text-[#F7F5F0] uppercase leading-none">MI EQUIPO</h2>
        </div>
        <button
          onClick={() => { soundFx.playClick(); onBack(); }}
          className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#1A3323] px-5 py-2 font-mono text-xs text-[#F7F5F0] transition-colors"
        >
          VOLVER AL LOBBY
        </button>
      </div>

      {/* Pestañas Principales */}
      <div className="flex border-b border-[#2C3E35] mb-6">
        <button
          onClick={() => { soundFx.playClick(); setActiveTab('LINEUP'); }}
          className={`flex-1 py-3 font-sports text-2xl uppercase tracking-wider transition-colors ${
            activeTab === 'LINEUP'
              ? 'bg-[#1A3323] text-[#F7F5F0] border-b-2 border-[#C5A059]'
              : 'text-[#E6DFD3] opacity-60 hover:opacity-100'
          }`}
        >
          ⚾ ROSTER & PITCHEO
        </button>
        <button
          onClick={() => { soundFx.playClick(); setActiveTab('DECK'); }}
          className={`flex-1 py-3 font-sports text-2xl uppercase tracking-wider transition-colors ${
            activeTab === 'DECK'
              ? 'bg-[#1A3323] text-[#F7F5F0] border-b-2 border-[#C5A059]'
              : 'text-[#E6DFD3] opacity-60 hover:opacity-100'
          }`}
        >
          🃏 MAZO TÁCTICO & BOOSTS
        </button>
      </div>

      {/* Pestaña 1: Lineup y Pitcheo */}
      {activeTab === 'LINEUP' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 my-auto">
          {/* Bateadores del inventario */}
          <div className="lg:col-span-7 bg-[#0A0D0F] border-2 border-[#2C3E35] p-4 shadow-2xl">
            <h3 className="font-sports text-2xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-3">
              BATEADORES EN INVENTARIO
            </h3>
            {loading && (
              <p className="font-mono text-xs text-[#C5A059] text-center py-8">Cargando inventario...</p>
            )}
            {error && (
              <p className="font-mono text-xs text-red-400 text-center py-8">{error}</p>
            )}
            {!loading && !error && batters.length === 0 && (
              <p className="font-mono text-xs text-[#E6DFD3] text-center py-8 opacity-60">
                No tienes bateadores en tu inventario. Abre un sobre en la tienda.
              </p>
            )}
            <div className="space-y-2">
              {batters.map((card, idx) => (
                <div
                  key={card.id}
                  className="flex justify-between items-center bg-[#121619] border border-[#2C3E35] p-2 hover:border-[#C5A059] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-sports text-2xl text-[#C5A059] w-6 text-center">
                      #{idx + 1}
                    </span>
                    <div>
                      <div className="font-sports text-xl text-[#F7F5F0] leading-none uppercase">
                        {card.name}
                      </div>
                      <span className="font-mono text-[10px] text-[#E6DFD3]">
                        CON: {card.contact} | POW: {card.power}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-xs bg-[#1A3323] border border-[#C5A059] px-2 py-0.5 text-[#F7F5F0]">
                      {card.position}
                    </span>
                    <span className="font-sports text-2xl text-[#F7F5F0]">
                      {card.overall} <span className="text-[10px] font-mono text-[#C5A059]">OVR</span>
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pitchers del inventario */}
          <div className="lg:col-span-5 bg-[#0A0D0F] border-2 border-[#2C3E35] p-4 shadow-2xl">
            <h3 className="font-sports text-2xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-3">
              ROTACIÓN & BULLPEN
            </h3>
            {!loading && !error && pitchers.length === 0 && (
              <p className="font-mono text-xs text-[#E6DFD3] text-center py-8 opacity-60">
                No tienes lanzadores en tu inventario.
              </p>
            )}
            <div className="space-y-3">
              {pitchers.map((pitcher) => (
                <div
                  key={pitcher.id}
                  className="bg-[#121619] border border-[#2C3E35] p-3 flex justify-between items-center"
                >
                  <div>
                    <span className="font-mono text-[10px] text-[#C5A059] block font-bold">
                      {pitcher.position}
                    </span>
                    <div className="font-sports text-2xl text-[#F7F5F0] leading-none uppercase">
                      {pitcher.name}
                    </div>
                    <span className="font-mono text-[10px] text-[#E6DFD3]">
                      VEL: {pitcher.velocity} | CTL: {pitcher.control} | MOV: {pitcher.movement}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-sports text-2xl text-[#C5A059]">{pitcher.overall} OVR</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Pestaña 2: Mazo Táctico */}
      {activeTab === 'DECK' && (
        <div className="bg-[#0A0D0F] border-2 border-[#2C3E35] p-6 shadow-2xl my-auto">
          <div className="flex justify-between items-center border-b border-[#2C3E35] pb-3 mb-6">
            <h3 className="font-sports text-3xl text-[#C5A059] uppercase">
              CARTAS DE ESTRATEGIA Y BOOSTS DE PARTIDO (4/15 EQUIPADAS)
            </h3>
            <span className="font-mono text-xs text-[#E6DFD3]">PUNTOS DE MAZO: 6 / 20</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {tacticalDeck.map((card) => (
              <div
                key={card.id}
                className="bg-[#121619] border-2 border-[#C5A059] p-4 flex flex-col justify-between shadow-lg"
              >
                <div>
                  <div className="flex justify-between items-center border-b border-[#2C3E35] pb-1 mb-2">
                    <span className="font-mono text-[9px] text-[#C5A059] uppercase">
                      {card.type}
                    </span>
                    <span className="font-sports text-lg text-[#F7F5F0]">
                      COSTO: {card.cost}
                    </span>
                  </div>
                  <h4 className="font-sports text-2xl text-[#F7F5F0] leading-tight uppercase mb-2">
                    {card.name}
                  </h4>
                  <p className="font-mono text-xs text-[#E6DFD3] leading-relaxed">
                    {card.desc}
                  </p>
                </div>
                <button
                  onClick={() => soundFx.playCardSelect()}
                  className="mt-4 w-full border border-[#2C3E35] hover:border-[#C5A059] bg-[#1A3323] py-1 font-mono text-xs text-[#F7F5F0] transition-colors"
                >
                  REMOVER DEL MAZO
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pie de Página */}
      <div className="font-mono text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-4">
        KOSHIEN TEAM MANAGEMENT ENGINE • 2026
      </div>
    </div>
  );
};