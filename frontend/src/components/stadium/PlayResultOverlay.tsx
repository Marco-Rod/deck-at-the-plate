import React, { useState, useEffect } from 'react';

interface PlayResultOverlayProps {
  resultText: string | null;
}

export const PlayResultOverlay: React.FC<PlayResultOverlayProps> = ({ resultText }) => {
  const [visibleText, setVisibleText] = useState<string | null>(null);

  useEffect(() => {
    if (resultText) {
      setVisibleText(resultText);
      // Ocultar la superposición automáticamente tras 3 segundos
      const timer = setTimeout(() => {
        setVisibleText(null);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [resultText]);

  if (!visibleText) return null;

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-xs pointer-events-none transition-all">
      <div className="bg-[#0A0D0F] border-2 border-[#C5A059] px-8 py-4 shadow-[0_0_30px_rgba(197,160,89,0.5)] transform animate-bounce">
        <h3 className="font-sports text-3xl md:text-4xl text-[#F7F5F0] tracking-widest text-center uppercase">
          {visibleText}
        </h3>
      </div>
    </div>
  );
};