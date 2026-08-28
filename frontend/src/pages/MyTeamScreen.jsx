import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { soundFx } from '../utils/audioManager';
import { user as userApi } from '../utils/api';
import { PlayerCard } from '../components/cards/PlayerCard';

// Categorización por sectores del campo
const FIELD_SECTORS = [
  {
    name: 'OUTFIELD (JARDINES)',
    slots: [
      { id: 'LF', name: 'LEFT FIELD' },
      { id: 'CF', name: 'CENTER FIELD' },
      { id: 'RF', name: 'RIGHT FIELD' },
    ],
  },
  {
    name: 'INFIELD (CUADRO INTERIOR)',
    slots: [
      { id: '3B', name: 'TERCERA BASE' },
      { id: 'SS', name: 'SHORTSTOP' },
      { id: '2B', name: 'SEGUNDA BASE' },
      { id: '1B', name: 'PRIMERA BASE' },
    ],
  },
  {
    name: 'BATERÍA & DH',
    slots: [
      { id: 'P', name: 'PITCHER' },
      { id: 'C', name: 'CATCHER' },
      { id: 'DH', name: 'BATEADOR DESIGNADO' },
    ],
  },
];

export const MyTeamScreen = ({ user, onBack }) => {
  const { t } = useTranslation();
  const [inventory, setInventory] = useState([]);
  const [userTeam, setUserTeam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingStatus, setSavingStatus] = useState(null);

  const [fieldLineup, setFieldLineup] = useState({});
  const [activeSlot, setActiveSlot] = useState('P');

  // Cargar inventario, lineup y datos del club
  useEffect(() => {
    if (!user?.userId) return;

    setLoading(true);
    
    // 1. Obtener la identidad del club
    userApi.getTeam(user.userId)
      .then(data => setUserTeam(data))
      .catch(err => console.error("El usuario no tiene club registrado:", err));

    // 2. Cargar inventario y lineup desde el Backend
    userApi.getInventory(user.userId)
      .then(async (data) => {
        const rawInventory = (data.inventory || []).map(i => i.card || i).filter(c => c && c.id);
        setInventory(rawInventory);

        try {
          const remoteLineup = await userApi.getLineup(user.userId);
          if (remoteLineup && remoteLineup.slots && Object.keys(remoteLineup.slots).length > 0) {
            setFieldLineup(remoteLineup.slots);
          } else {
            autoAssignLineup(rawInventory);
          }
        } catch {
          autoAssignLineup(rawInventory);
        }

        setError(null);
      })
      .catch((err) => {
        console.error('Error cargando datos:', err);
        setError('No se pudo cargar la información del usuario.');
      })
      .finally(() => setLoading(false));
  }, [user?.userId]);

  // Persistir alineación en Backend (PostgreSQL) y localStorage
  const syncLineup = async (updatedLineup) => {
    setFieldLineup(updatedLineup);
    localStorage.setItem(`user_lineup_${user?.userId}`, JSON.stringify(updatedLineup));

    try {
      setSavingStatus('GUARDANDO...');
      await userApi.updateLineup(user.userId, updatedLineup);
      setSavingStatus('✓ GUARDADO EN DB');
      setTimeout(() => setSavingStatus(null), 2000);
    } catch (err) {
      console.error('Error al sincronizar con el backend:', err);
      setSavingStatus('⚠️ ERROR AL GUARDAR');
    }
  };

  const autoAssignLineup = (cards = inventory) => {
    if (soundFx?.playClick) soundFx.playClick();

    const assigned = {};
    const usedCardIds = new Set();

    FIELD_SECTORS.flatMap(s => s.slots).forEach((slot) => {
      if (slot.id === 'DH' || slot.id === 'P') return;

      const candidates = cards.filter(
        c => !usedCardIds.has(c.id) && c.position === slot.id
      );

      candidates.sort((a, b) => (b.overall || 0) - (a.overall || 0));
      if (candidates[0]) {
        assigned[slot.id] = candidates[0];
        usedCardIds.add(candidates[0].id);
      }
    });

    const pitcherCandidates = cards.filter(
      c => ['SP', 'RP', 'CP', 'TWP'].includes(c.position) || c.is_two_way
    );
    pitcherCandidates.sort((a, b) => (b.overall || 0) - (a.overall || 0));

    if (pitcherCandidates[0]) {
      assigned['P'] = pitcherCandidates[0];
      if (pitcherCandidates[0].position !== 'TWP' && !pitcherCandidates[0].is_two_way) {
        usedCardIds.add(pitcherCandidates[0].id);
      }
    }

    const dhCandidates = cards.filter(
      c => (!usedCardIds.has(c.id) || c.position === 'TWP' || c.is_two_way) && !['SP', 'RP', 'CP'].includes(c.position)
    );
    dhCandidates.sort((a, b) => (b.overall || 0) - (a.overall || 0));

    if (dhCandidates[0]) {
      assigned['DH'] = dhCandidates[0];
    }

    syncLineup(assigned);
  };

  const assignedCardIds = useMemo(() => {
    return new Set(Object.values(fieldLineup).map(c => c?.id).filter(Boolean));
  }, [fieldLineup]);

  const availableForSelectedSlot = useMemo(() => {
    if (!activeSlot) return [];
    
    return inventory.filter(card => {
      const isTWP = card.position === 'TWP' || card.is_two_way;

      if (!isTWP && assignedCardIds.has(card.id) && fieldLineup[activeSlot]?.id !== card.id) {
        return false;
      }

      if (activeSlot === 'P') {
        return ['SP', 'RP', 'CP', 'TWP'].includes(card.position) || isTWP;
      }

      if (activeSlot === 'DH') {
        return !['SP', 'RP', 'CP'].includes(card.position) || isTWP;
      }

      return card.position === activeSlot;
    }).sort((a, b) => (b.overall || 0) - (a.overall || 0));
  }, [inventory, activeSlot, assignedCardIds, fieldLineup]);

  const handleSelectCardForSlot = (card) => {
    if (soundFx?.playCardSelect) soundFx.playCardSelect();
    const updated = {
      ...fieldLineup,
      [activeSlot]: card
    };
    syncLineup(updated);
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between p-6 text-[#F7F5F0] font-mono select-none">
      
      {/* CABECERA SUPERIOR PERSONALIZADA DEL CLUB */}
      <div className="w-full flex justify-between items-center border-b-2 border-[#C5A059] pb-3 mb-4">
        <div className="flex items-center gap-4">
          {userTeam && (
            <div 
              className="w-14 h-14 rounded-full flex items-center justify-center font-sports text-xl text-white border-2 border-white/20 shadow-lg shrink-0"
              style={{ backgroundColor: userTeam.primary_color }}
            >
              {userTeam.short_name}
            </div>
          )}
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-xs text-[#C5A059] uppercase block font-mono tracking-widest">
                {userTeam ? `${userTeam.city} • ${userTeam.stadium_name}` : 'ESTRATEGIA & ALINEACIÓN'}
              </span>
              {savingStatus && (
                <span className="text-[9px] bg-[#1A3323] text-[#C5A059] px-2 py-0.5 border border-[#C5A059] rounded animate-pulse">
                  {savingStatus}
                </span>
              )}
            </div>
            <h2 className="font-sports text-4xl uppercase leading-none text-white tracking-wide">
              {userTeam ? userTeam.name : 'MI EQUIPO'}
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => autoAssignLineup()}
            className="bg-[#1A3323] hover:bg-[#2D5A3F] border border-[#C5A059] text-[#C5A059] px-4 py-3 text-xs uppercase tracking-wider transition-all cursor-pointer active:scale-95 font-sports"
          >
            ⚡ AUTO-LINEUP ÓPTIMO
          </button>
          <button
            type="button"
            onClick={onBack}
            className="border border-[#2C3E35] hover:border-[#C5A059] bg-[#0A0D0F] px-5 py-3 text-xs text-[#F7F5F0] transition-colors cursor-pointer font-mono"
          >
            VOLVER AL LOBBY
          </button>
        </div>
      </div>

      {/* VISTA PRINCIPAL (9 COLS CAMPO / 3 COLS CANDIDATOS) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 my-auto">
        
        {/* VISTA DEL CAMPO */}
        <div className="lg:col-span-9 bg-[#0A0D0F] border-2 border-[#2C3E35] p-6 shadow-2xl relative min-h-[520px] flex flex-col justify-around overflow-hidden">
          
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-20 select-none">
            <svg viewBox="0 0 400 400" className="w-[480px] h-[480px]">
              <path d="M 200 350 L 50 150 A 210 210 0 0 1 350 150 Z" fill="none" stroke="#C5A059" strokeWidth="2" strokeDasharray="4 4" />
              <line x1="200" y1="350" x2="30" y2="130" stroke="#C5A059" strokeWidth="2" />
              <line x1="200" y1="350" x2="370" y2="130" stroke="#C5A059" strokeWidth="2" />
              <polygon points="200,350 280,270 200,190 120,270" fill="none" stroke="#C5A059" strokeWidth="2" />
              <circle cx="200" cy="270" r="18" fill="none" stroke="#C5A059" strokeWidth="1.5" />
              <polygon points="200,352 193,345 193,340 207,340 207,345" fill="#C5A059" />
            </svg>
          </div>

          <span className="text-[10px] text-[#C5A059] uppercase font-bold block mb-2 relative z-10">
            ★ Haz clic en una posición para seleccionar candidatos ★
          </span>

          {FIELD_SECTORS.map((sector, sIdx) => (
            <div key={sIdx} className="w-full mb-3 relative z-10">
              <span className="text-[9px] text-[#C5A059]/80 font-mono tracking-widest block mb-1 border-b border-[#2C3E35]/60 pb-0.5 uppercase">
                {sector.name}
              </span>
              <div className="flex flex-wrap justify-center gap-4">
                {sector.slots.map((slot) => {
                  const assignedPlayer = fieldLineup[slot.id];
                  const isSelected = activeSlot === slot.id;
                  const isTWP = assignedPlayer?.position === 'TWP' || assignedPlayer?.is_two_way;

                  return (
                    <button
                      key={slot.id}
                      type="button"
                      onClick={() => { if (soundFx?.playClick) soundFx.playClick(); setActiveSlot(slot.id); }}
                      className={`flex-1 min-w-[170px] max-w-[220px] p-3 border-2 transition-all cursor-pointer flex flex-col justify-between min-h-[85px] rounded backdrop-blur-md ${
                        isSelected
                          ? 'border-[#C5A059] bg-[#1A3323]/90 scale-105 shadow-[0_0_15px_rgba(197,160,89,0.4)]'
                          : assignedPlayer
                          ? 'border-[#2C3E35] bg-[#121619]/85 hover:border-gray-400'
                          : 'border-dashed border-red-500/50 bg-red-950/20'
                      }`}
                    >
                      <div className="w-full flex justify-between items-center text-[10px] text-[#C5A059] font-bold border-b border-white/10 pb-0.5">
                        <div className="flex items-center gap-1">
                          <span>{slot.id}</span>
                          {isTWP && (
                            <span className="bg-[#C5A059] text-[#121619] text-[8px] px-1 rounded font-extrabold">
                              TWP
                            </span>
                          )}
                        </div>
                        <span className="text-[9px] text-gray-400 truncate">{slot.name}</span>
                      </div>

                      {assignedPlayer ? (
                        <div className="my-auto text-left w-full mt-1">
                          <div className="font-sports text-lg text-white truncate leading-tight uppercase">
                            {assignedPlayer.name}
                          </div>
                          <span className="text-[10px] text-gray-400 block font-mono">
                            {assignedPlayer.overall} OVR | C:{assignedPlayer.contact} P:{assignedPlayer.power}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-red-400 my-auto uppercase font-bold text-center block py-1">
                          [ VACÍO ]
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* CANDIDATOS POR POSICIÓN */}
        <div className="lg:col-span-3 bg-[#0A0D0F] border-2 border-[#2C3E35] p-3 shadow-2xl flex flex-col">
          <div className="border-b border-[#2C3E35] pb-2 mb-3">
            <span className="text-[10px] text-gray-400 block uppercase font-mono">CANDIDATOS PARA</span>
            <h3 className="font-sports text-xl text-[#C5A059] uppercase">
              POSICIÓN: {activeSlot}
            </h3>
          </div>

          <div className="space-y-2 overflow-y-auto max-h-[50vh] pr-1">
            {availableForSelectedSlot.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-8 font-mono">
                No tienes cartas disponibles para la posición {activeSlot}.
              </p>
            ) : (
              availableForSelectedSlot.map((card) => {
                const isEquippedInCurrentSlot = fieldLineup[activeSlot]?.id === card.id;

                return (
                  <PlayerCard
                    key={card.id}
                    card={card}
                    mode="compact"
                    size="sm"
                    isSelected={isEquippedInCurrentSlot}
                    onClick={() => handleSelectCardForSlot(card)}
                    role={card.position === 'SP' || card.position === 'RP' || card.position === 'CP' ? 'PITCHER' : 'BATTER'}
                  />
                );
              })
            )}
          </div>
        </div>

      </div>

      <div className="text-[10px] text-[#2C3E35] uppercase tracking-widest text-center mt-4 font-mono">
        KOSHIEN LINEUP & FIELD ENGINE • 2026
      </div>
    </div>
  );
};