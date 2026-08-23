import React, { useState, useEffect } from 'react';
import { soundFx } from '../utils/audioManager';
import { PlayerCard } from '../components/cards/PlayerCard';
import { user as userApi, games as gamesApi } from '../utils/api';

export const RosterSelectionScreen = ({ user, gameConfig, onRosterConfirmed, onBack }) => {
  const [pitchers, setPitchers] = useState([]);
  const [batters, setBatters] = useState([]);
  const [selectedPitcher, setSelectedPitcher] = useState(null);
  const [lineup, setLineup] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Cargar inventario real del usuario para poblar la selección
  useEffect(() => {
    if (!user?.userId) return;

    userApi.getInventory(user.userId)
      .then((data) => {
        const allCards = (data.inventory || []).map(item => item.card);
        const pitcherCards = allCards.filter(c => c && ['SP', 'RP', 'TWP'].includes(c.position));
        const batterCards  = allCards.filter(c => c && !['SP', 'RP'].includes(c.position));

        setPitchers(pitcherCards);
        setBatters(batterCards);

        // Pre-seleccionar el primer pitcher disponible
        if (pitcherCards.length > 0) setSelectedPitcher(pitcherCards[0]);
        // Pre-seleccionar los primeros 9 bateadores
        setLineup(batterCards.slice(0, 9));
      })
      .catch((err) => {
        console.error('Error cargando inventario:', err);
        setError('No se pudo cargar tu inventario. Verifica tu conexión.');
      })
      .finally(() => setLoading(false));
  }, [user?.userId]);

  const toggleBatter = (card) => {
    setLineup(prev => {
      const isSelected = prev.find(b => b.id === card.id);
      if (isSelected) return prev.filter(b => b.id !== card.id);
      if (prev.length >= 9) return prev; // Máximo 9 bateadores
      return [...prev, card];
    });
  };

  const handleStartGame = async () => {
    if (!selectedPitcher || lineup.length < 9) {
      setError('Necesitas un lanzador y 9 bateadores para iniciar.');
      return;
    }

    soundFx.playGameStart();
    setSubmitting(true);
    setError(null);

    try {
      // Crear la partida en el backend con el roster seleccionado
      const gameData = await gamesApi.create({
        home_user_id: user.userId,
        away_user_id: 'CPU_BOT',
        game_mode: gameConfig?.mode || 'PVE',
        difficulty: gameConfig?.difficulty || 'MEDIUM',
        home_pitcher_id: selectedPitcher.id,
        away_pitcher_id: selectedPitcher.id, // CPU usa el mismo pitcher como placeholder
        home_lineup: lineup.map(b => b.id),
        away_lineup: lineup.map(b => b.id),  // CPU lineup placeholder
        home_tactics_deck: ["tac_vision_boost", "tac_power_boost", "tac_contact_boost", "tac_slider_break", "tac_velocity_boost"],
        away_tactics_deck: ["tac_vision_boost", "tac_debuff_vision", "tac_slider_break", "tac_velocity_boost", "tac_power_boost"],
      });

      onRosterConfirmed(gameData.id);
    } catch (err) {
      setError(`Error al crear la partida: ${err.message}`);
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-between p-4 bg-[#121619]">
      {/* Cabecera */}
      <div className="w-full max-w-4xl flex justify-between items-center border-b-2 border-[#C5A059] pb-3 mb-4">
        <div>
          <span className="font-mono text-xs text-[#C5A059] uppercase block">PREPARACIÓN DE ESCUADRA</span>
          <h2 className="font-sports text-4xl text-[#F7F5F0] uppercase leading-none">SELECCIÓN DE ROSTER</h2>
          {gameConfig && (
            <span className="font-mono text-[10px] text-[#E6DFD3]">
              MODO: {gameConfig.mode} | DIFICULTAD: {gameConfig.difficulty}
            </span>
          )}
        </div>
        <button
          onClick={() => { soundFx.playClick(); onBack(); }}
          className="border border-[#2C3E35] hover:border-[#C5A059] px-4 py-2 font-mono text-xs text-[#E6DFD3] transition-colors"
        >
          VOLVER AL LOBBY
        </button>
      </div>

      {/* Estado de carga / error */}
      {loading && (
        <p className="font-mono text-xs text-[#C5A059] my-auto">Cargando tu inventario...</p>
      )}
      {error && (
        <p className="font-mono text-xs text-red-400 text-center my-4 border border-red-400/30 p-3 w-full max-w-4xl">{error}</p>
      )}

      {/* Contenido Principal */}
      {!loading && (
        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6 my-auto">
          {/* Selección de Pitcher Abridor */}
          <div className="bg-[#121619] border-2 border-[#C5A059] p-4 shadow-2xl">
            <h3 className="font-sports text-2xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              LANZADOR ABRIDOR
            </h3>
            {pitchers.length === 0 ? (
              <p className="font-mono text-xs text-[#E6DFD3] opacity-60 text-center py-4">
                Sin lanzadores en inventario. Abre un sobre primero.
              </p>
            ) : (
              <div className="flex gap-4 overflow-x-auto pb-2">
                {pitchers.map((pitcher) => (
                  <PlayerCard
                    key={pitcher.id}
                    player={pitcher}
                    role="PITCHER"
                    isSelected={selectedPitcher?.id === pitcher.id}
                    onClick={(p) => setSelectedPitcher(p)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Selección de Lineup */}
          <div className="bg-[#121619] border-2 border-[#C5A059] p-4 shadow-2xl">
            <h3 className="font-sports text-2xl text-[#C5A059] uppercase border-b border-[#2C3E35] pb-2 mb-4">
              LINEUP ACTIVO ({lineup.length}/9)
            </h3>
            {batters.length === 0 ? (
              <p className="font-mono text-xs text-[#E6DFD3] opacity-60 text-center py-4">
                Sin bateadores en inventario.
              </p>
            ) : (
              <div className="flex gap-4 overflow-x-auto pb-2 flex-wrap">
                {batters.map((batter) => (
                  <PlayerCard
                    key={batter.id}
                    player={batter}
                    role="BATTER"
                    isSelected={!!lineup.find(b => b.id === batter.id)}
                    onClick={toggleBatter}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Botón de Confirmación */}
      <div className="w-full max-w-4xl mt-6">
        <button
          onClick={handleStartGame}
          disabled={submitting || !selectedPitcher || lineup.length < 9}
          onMouseEnter={() => soundFx.playCardSelect()}
          className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] disabled:opacity-40 disabled:cursor-not-allowed text-[#F7F5F0] border-2 border-[#C5A059] py-4 font-sports text-3xl tracking-widest transition-all active:scale-95 shadow-2xl"
        >
          {submitting ? 'CREANDO PARTIDA...' : 'CONFIRMAR ROSTER Y SALIR AL CAMPO'}
        </button>
        {lineup.length < 9 && !loading && (
          <p className="font-mono text-[10px] text-[#C5A059] text-center mt-2">
            Selecciona {9 - lineup.length} bateador(es) más para completar el lineup.
          </p>
        )}
      </div>
    </div>
  );
};