import React from 'react';

interface GameOverModalProps {
  winnerMessage?: string;
  homeScore: number;
  awayScore: number;
  homeTeamName: string;
  awayTeamName: string;
  userRole?: 'HOME' | 'AWAY'; // ⭐ NUEVO: posición del usuario
  onReturnToLobby: () => void;
}

export const GameOverModal: React.FC<GameOverModalProps> = ({
  winnerMessage,
  homeScore,
  awayScore,
  homeTeamName,
  awayTeamName,
  userRole = 'HOME', // ⭐ NUEVO: por defecto HOME
  onReturnToLobby,
}) => {
  // ⭐ ARREGLADO: Intercambiar scores según userRole (igual que Scoreboard)
  const userScore = userRole === 'HOME' ? homeScore : awayScore;
  const cpuScore = userRole === 'HOME' ? awayScore : homeScore;
  const userTeamName = userRole === 'HOME' ? homeTeamName : awayTeamName;
  const cpuTeamName = userRole === 'HOME' ? awayTeamName : homeTeamName;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md">
      <div className="bg-[#0A0D0F] border-2 border-[#C5A059] p-8 max-w-md w-full shadow-[0_0_50px_rgba(197,160,89,0.4)] text-center font-mono">
        <span className="text-xs text-[#C5A059] font-bold tracking-widest uppercase block mb-2">
          FIN DEL PARTIDO • STADIUM MATCH
        </span>
        
        <h2 className="font-sports text-4xl text-[#F7F5F0] mb-4 uppercase tracking-wider">
          {winnerMessage || '¡PARTIDO FINALIZADO!'}
        </h2>

        {/* Resumen Final de Carreras */}
        <div className="bg-[#121619] border border-[#2C3E35] p-4 my-6 flex justify-around items-center">
          <div className="flex flex-col items-center">
            <span className="text-xs text-gray-400 mb-1">{userTeamName}</span>
            <span className="font-sports text-3xl text-[#C5A059]">{userScore}</span>
          </div>
          <span className="font-sports text-2xl text-gray-600">-</span>
          <div className="flex flex-col items-center">
            <span className="text-xs text-gray-400 mb-1">{cpuTeamName}</span>
            <span className="font-sports text-3xl text-[#F7F5F0]">{cpuScore}</span>
          </div>
        </div>

        <p className="text-xs text-gray-400 mb-6">
          Se han registrado las estadísticas y las recompensas del encuentro en tu perfil.
        </p>

        <button
          type="button"
          onClick={onReturnToLobby}
          className="w-full bg-[#1A3323] hover:bg-[#2D5A3F] border-2 border-[#C5A059] py-3 font-sports text-xl text-[#C5A059] tracking-widest uppercase cursor-pointer transition-all shadow-lg active:scale-95"
        >
          REGRESAR AL LOBBY 🏟️
        </button>
      </div>
    </div>
  );
};