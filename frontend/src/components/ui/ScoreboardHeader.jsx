import React from 'react';

export const ScoreboardHeader = ({ homeScore = 0, awayScore = 0, inning = "LOBBY", outs = 0 }) => {
  return (
    <div className="w-full max-w-xl mx-auto bg-[#121619] border-2 border-[#C5A059] p-3 rounded-none shadow-2xl">
      <div className="text-center font-sports text-[#C5A059] text-2xl tracking-widest uppercase mb-1 border-b border-[#2C3E35] pb-1">
        ★ KOSHIEN BASEBALL PARK ★
      </div>
      
      <div className="grid grid-cols-3 gap-2 text-center my-2">
        <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2">
          <div className="text-[10px] font-mono text-[#E6DFD3] uppercase">VISITA</div>
          <div className="font-sports text-4xl leading-none text-[#F7F5F0]">{awayScore}</div>
        </div>
        
        <div className="bg-[#1A3323] border border-[#C5A059] p-2">
          <div className="text-[10px] font-mono text-[#C5A059] uppercase">INNING</div>
          <div className="font-sports text-3xl leading-none text-[#F7F5F0]">{inning}</div>
        </div>

        <div className="bg-[#0A0D0F] border border-[#2C3E35] p-2">
          <div className="text-[10px] font-mono text-[#E6DFD3] uppercase">LOCAL</div>
          <div className="font-sports text-4xl leading-none text-[#F7F5F0]">{homeScore}</div>
        </div>
      </div>

      <div className="flex justify-center items-center gap-4 mt-2 pt-2 border-t border-[#2C3E35]">
        <span className="text-[10px] font-mono text-[#E6DFD3]">OUTS:</span>
        <div className="flex gap-2">
          {[1, 2, 3].map((num) => (
            <div 
              key={num}
              className={`w-3 h-3 rounded-full border border-[#F7F5F0] ${
                num <= outs ? 'bg-red-700 shadow-[0_0_8px_#b91c1c]' : 'bg-[#121619]'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default ScoreboardHeader;