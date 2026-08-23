import React from 'react';

interface PlayResultOverlayProps {
  resultText: string | null;
}

export const PlayResultOverlay: React.FC<PlayResultOverlayProps> = ({ resultText }) => {
  if (!resultText) return null;

  return (
    <div className="z-40 absolute inset-0 pointer-events-none flex items-center justify-center">
      <div className="bg-[#0A0D0F]/90 border-2 border-[#C5A059] px-8 py-4 rounded-xl shadow-[0_0_50px_rgba(197,160,89,0.8)] backdrop-blur-md animate-bounce">
        <h3 className="font-sports text-5xl text-[#F7F5F0] tracking-widest uppercase text-center">
          {resultText}
        </h3>
      </div>
    </div>
  );
};