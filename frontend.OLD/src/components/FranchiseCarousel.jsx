import React, { useState, useEffect } from 'react';

export const FranchiseCarousel = ({ teams, selectedTeamId, onSelectTeam }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [displayTeams, setDisplayTeams] = useState([]);

  // Crear array infinito duplicando equipos
  useEffect(() => {
    if (teams.length > 0) {
      // Duplicar 3 veces para efecto infinito suave
      setDisplayTeams([...teams, ...teams, ...teams]);
      
      // Encontrar índice del equipo seleccionado (en el primer set)
      const selectedIndex = teams.findIndex(t => t.id === selectedTeamId);
      if (selectedIndex >= 0) {
        setCurrentIndex(selectedIndex);
      }
    }
  }, [teams, selectedTeamId]);

  // Efecto para notificar al padre cuando currentIndex cambia por flechas
  useEffect(() => {
    if (teams.length > 0 && displayTeams.length > 0) {
      const realIndex = currentIndex % teams.length;
      const selectedTeam = teams[realIndex];
      console.log(`[DEBUG FranchiseCarousel] currentIndex cambió a ${currentIndex}, notificando team=${selectedTeam.id}`);
      onSelectTeam(selectedTeam);
    }
  }, [currentIndex, teams, displayTeams.length, onSelectTeam]);

  const handlePrevious = () => {
    setCurrentIndex((prev) => {
      const newIndex = prev - 1 >= 0 ? prev - 1 : teams.length * 2 - 1;
      console.log(`[DEBUG FranchiseCarousel] handlePrevious: newIndex=${newIndex}`);
      return newIndex;
    });
  };

  const handleNext = () => {
    setCurrentIndex((prev) => {
      const newIndex = prev + 1 >= teams.length * 3 ? teams.length : prev + 1;
      console.log(`[DEBUG FranchiseCarousel] handleNext: newIndex=${newIndex}`);
      return newIndex;
    });
  };

  const handleTeamSelect = (index) => {
    console.log(`[DEBUG FranchiseCarousel] handleTeamSelect llamado con index=${index}`);
    
    // Actualizar currentIndex - el useEffect notificará al padre
    setCurrentIndex(index);
    console.log(`[DEBUG FranchiseCarousel] setCurrentIndex a ${index}`);
  };

  if (!displayTeams.length) return null;

  // Calcular qué equipos mostrar (5 en pantalla: 2 anteriores, 1 centro, 2 posteriores)
  const visibleIndices = [];
  for (let i = -2; i <= 2; i++) {
    visibleIndices.push((currentIndex + i + displayTeams.length) % displayTeams.length);
  }

  return (
    <div className="w-full flex flex-col items-center gap-6">
      {/* Carrusel */}
      <div className="relative w-full max-w-4xl flex items-center justify-center gap-4">
        {/* Botón anterior */}
        <button
          onClick={handlePrevious}
          className="flex-shrink-0 w-12 h-12 rounded-full bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#C5A059] font-bold text-xl cursor-pointer transition-all"
        >
          ◀
        </button>

        {/* Contenedor de tarjetas */}
        <div className="flex-1 flex justify-center items-center gap-3">
          {visibleIndices.map((idx, position) => {
            const team = displayTeams[idx];
            const isCenter = position === 2;
            const isSelected = team.id === selectedTeamId;
            const distance = Math.abs(position - 2);

            return (
              <div
                key={`${team.id}-${idx}`}
                onClick={() => handleTeamSelect(idx)}
                className={`flex-shrink-0 transition-all duration-300 cursor-pointer ${
                  isCenter
                    ? 'scale-100 opacity-100'
                    : distance === 1
                    ? 'scale-75 opacity-60 hover:scale-80 hover:opacity-75'
                    : 'scale-50 opacity-30 hover:scale-55 hover:opacity-40'
                }`}
              >
                <div
                  className={`flex flex-col items-center gap-3 p-4 rounded-xl border-2 transition-all w-40 h-48 ${
                    isSelected && isCenter
                      ? 'border-[#C5A059] bg-[#1A3323] shadow-[0_0_30px_rgba(197,160,89,0.5)]'
                      : 'border-[#2C3E35] bg-[#0A0D0F]'
                  }`}
                >
                  {/* Logo/Badge */}
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold text-white border-2 border-[#C5A059] shadow-lg flex-shrink-0"
                    style={{ backgroundColor: team.color }}
                  >
                    {team.badge}
                  </div>

                  {/* Nombre */}
                  <div className="text-center flex-1 flex flex-col items-center justify-center min-h-0">
                    <p className="font-bold text-sm text-white uppercase font-sports leading-tight line-clamp-2 break-words">
                      {team.name}
                    </p>
                    <p className="text-xs text-gray-400 line-clamp-1">
                      {team.city}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Botón siguiente */}
        <button
          onClick={handleNext}
          className="flex-shrink-0 w-12 h-12 rounded-full bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] text-[#C5A059] font-bold text-xl cursor-pointer transition-all"
        >
          ▶
        </button>
      </div>

      {/* Información del equipo seleccionado */}
      {selectedTeamId && displayTeams.length > 0 && (
        <div className="text-center">
          <p className="text-xs text-gray-400 font-mono mb-2">EQUIPO SELECCIONADO</p>
          <p className="text-lg font-bold text-[#C5A059] uppercase font-sports">
            {displayTeams[currentIndex]?.name}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {displayTeams[currentIndex]?.desc}
          </p>
        </div>
      )}
    </div>
  );
};
