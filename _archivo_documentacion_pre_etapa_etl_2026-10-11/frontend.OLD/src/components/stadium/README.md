# Stadium Components Architecture

## ✅ Status: Implementation Complete

All 6 phases of refactoring and Propuesta 1 visual improvements have been successfully implemented.

**See `IMPLEMENTATION_SUMMARY.md` for detailed completion status.**

---

## 📁 Project Structure

```
stadium/
├── README.md (this file - architecture overview)
├── IMPLEMENTATION_SUMMARY.md (completion details ✅)
├── index.ts (main entry point - barrel exports)
├── types/
│   └── stadium.types.ts (centralized interfaces)
├── constants/
│   └── stadium.constants.ts (colors, sizes, animations)
├── hooks/
│   └── useStadiumLayout.ts (shared layout logic)
├── components/
│   ├── index.ts (barrel exports all below)
│   ├── base/ (GameHeader, Scoreboard, GameInfo)
│   ├── pitch/ (PitchSelector, StrikeZoneGrid, PitchZoneGrid)
│   ├── stats/ (LineupPanel, StrikeoutCounter, GameStatsPanel)
│   ├── tactical/ (TacticalCardItem, SubmitPlayButton, TacticalHand)
│   └── layouts/ (CentralField)
└── StadiumShowcaseScreen.tsx (main screen - fully integrated)
```

---

## ✨ Propuesta 1 Improvements

### Visual Enhancements (All Implemented)
- ✅ **Header:** 2-line layout, text-3xl → text-4xl (+33%)
- ✅ **Scoreboard:** B/S/O text-lg → text-2xl (+43%)
- ✅ **GameInfo:** padding +50%, fonts +25-43%
- ✅ **SO Counter:** text-2xl → text-6xl (+200%!)
- ✅ **Central Gap:** gap-4 → gap-6 (+50% spacing)
- ✅ **Stats Panels:** Dual-mode (lineup/strikeouts)

### Code Organization (All Implemented)
- ✅ Modular component structure
- ✅ Barrel exports at each level
- ✅ Centralized types and constants
- ✅ Clean import patterns
- ✅ TypeScript strict mode
- ✅ JSDoc documentation

---

## 🚀 Quick Start for New Developers

### Import Pattern
```typescript
// From main entry point
import {
  GameHeader,
  Scoreboard,
  GameInfo,
  PitchZoneGrid,
  GameStatsPanel,
  CentralField,
  TacticalHand,
} from '@/components/stadium';

// Also available
import {
  COLORS,
  TYPOGRAPHY,
  SPACING,
  useStadiumLayout,
} from '@/components/stadium';
```

### Component Hierarchy
```
StadiumShowcaseScreen (main)
├── GameHeader (top, 2-line layout)
├── Scoreboard (game score, inning, B/S/O)
├── CentralField (central gameplay area)
│   ├── GameInfo (B/S/O, bases, inning)
│   ├── PitchZoneGrid (pitch selection)
│   ├── PlayerCards (pitcher + batter)
├── GameStatsPanel (left/right dual-mode)
│   ├── LineupPanel (left side - batting lineup)
│   └── StrikeoutCounter (right side - SO counter)
└── TacticalHand (bottom - tactical cards)
```

---

## 📚 Documentation

- **IMPLEMENTATION_SUMMARY.md** - Project completion status
- **index.ts comments** - Usage examples for all exports
- **Component JSDoc** - Detailed documentation in each file

---

## 🎯 Implementation Complete

For detailed information about what was implemented, see `IMPLEMENTATION_SUMMARY.md`.

**Status:** Ready for testing and deployment ✅
- [x] **StadiumShowcaseScreen.tsx** - Orquestador principal (REFACTORIZADO)

---

## 📋 Convenciones de Código

### TypeScript
- ✅ Strict mode enabled
- ✅ Tipos exportados desde `types/stadium.types.ts`
- ✅ Interfaces separadas del componente (en types/)
- ✅ Props interface siempre nombrada `{ComponentName}Props`

### React
- ✅ Functional components con hooks
- ✅ React.FC<Props> tipado explícitamente
- ✅ Props destructuradas en función
- ✅ Callbacks nombrados `on{Event}` (onSelectZone, onSubmitPlay, etc)

### Tailwind CSS
- ✅ Clases en orden: display → positioning → sizing → spacing → colors → effects
- ✅ Responsive prefix cuando sea necesario (md:, lg:)
- ✅ Nombrar clases complejas como constantes si se reutilizan

### Estructura de Archivo
```tsx
// 1. Imports (types, libs, componentes)
import React from 'react';
import { motion } from 'framer-motion';
import type { SomeType } from '../types/stadium.types';
import { COLORS } from '../constants/stadium.constants';

// 2. Tipos/Interfaces
interface ComponentProps {
  prop1: string;
  prop2?: number;
  onEvent: (value: string) => void;
}

// 3. Componente principal
export const ComponentName: React.FC<ComponentProps> = ({
  prop1,
  prop2 = 0,
  onEvent,
}) => {
  // Lógica del componente
  return (
    <div>
      {/* JSX */}
    </div>
  );
};

// 4. Exports nombrados
export default ComponentName;
```

---

## 🎨 Paleta de Colores (Exportada desde constants/)

```
PRIMARY_DARK: #0A0D0F      (Background principal)
SECONDARY_DARK: #121619    (Backgrounds secundarios)
TEXT_PRIMARY: #F7F5F0      (Texto principal - muy claro)
TEXT_SECONDARY: #E6DFD3    (Texto secundario - claro)
ACCENT_GOLD: #C5A059       (Oro - interactivos, borders)
ACCENT_GREEN: #1A3323      (Verde oscuro - selected states)
BORDER_SUBTLE: #2C3E35     (Bordes sutiles)
BORDER_STRONG: #C5A059     (Bordes activos - oro)

RARITY_COLORS: {
  DIAMOND: #9966FF,
  GOLD: #FFD700,
  SILVER: #C0C0C0,
  BRONZE: #CD7F32,
  COMMON: #808080
}
```

---

## 📐 Tamaños Estándar

### Tipografía
- **Titles (H1):** `font-sports text-4xl` - Headers principales
- **Titles (H2):** `font-sports text-2xl` - Subtítulos
- **Body (Regular):** `font-mono text-base` - Contenido
- **Body (Small):** `font-mono text-sm` - Info secundaria
- **Label:** `font-mono text-[10px]` - Etiquetas pequeñas
- **Tiny:** `font-mono text-[8px]` - Datos comprimidos

### Espaciado
- **Padding Interior:** `p-3` (12px), `p-4` (16px), `p-6` (24px)
- **Margin/Gap:** `gap-3`, `gap-4`, `gap-6`
- **Separadores:** `my-2`, `py-2` (8px vertical)

### Componentes
- **Cards Pequeñas:** w-56 h-80 (PlayerCard)
- **Grid Elementos:** w-16 h-16 (Zonas de strike)
- **Botones:** px-3 py-1.5 (pequeños), px-4 py-2 (medianos)

---

## 🔄 Flujo de Datos (Props Drilling)

```
StadiumShowcaseScreen (State Manager)
├── GameHeader (title, connection status)
├── Scoreboard (gameState)
├── CentralField (gameState, selectedZone, selectedPitch, callbacks)
│   ├── GameInfo (balls, strikes, outs, etc)
│   ├── PlayerCard (pitcher) + PitchZoneGrid + PlayerCard (batter)
│   └── TacticalHand (tacticalCards, selectedTacticalId, callbacks)
└── GameStatsPanel (lineup, stats, strikeouts)
```

---

## 🧪 Testing Strategy

Cada componente debe ser:
- ✅ **Independiente:** Funciona sin context externo
- ✅ **Testeable:** Props claras, callbacks documentados
- ✅ **Reutilizable:** Lógica separada de UI

---

## 📚 Documentación por Componente

Cada componente debe incluir JSDoc:

```tsx
/**
 * Scoreboard - Displays game score and inning information
 * 
 * @component
 * @example
 * <Scoreboard gameState={gameState} role="PITCHER" />
 * 
 * @param {ScoreboardProps} props
 * @returns {React.ReactElement}
 */
export const Scoreboard: React.FC<ScoreboardProps> = ({ ... }) => { ... }
```

---

## 🚀 Checklist para Cada Componente

- [ ] TypeScript types en `types/stadium.types.ts`
- [ ] Constantes en `constants/stadium.constants.ts` si aplica
- [ ] Componente en directorio apropiado (base/, pitch/, stats/, etc)
- [ ] JSDoc en componente
- [ ] Props interface clara y documentada
- [ ] Compila sin errores: `npm run build`
- [ ] Exports nombrado y default
- [ ] Listo para integración

---

## 📖 Cómo Leer esta Arquitectura

1. **Nuevo developer?** Lee este README primero
2. **Necesitas un componente?** Busca en la sección por tema (pitch/, stats/, etc)
3. **Tipos compartidos?** Están en `types/stadium.types.ts`
4. **Colores/Constantes?** Están en `constants/stadium.constants.ts`
5. **Integración final?** Mira `StadiumShowcaseScreen.tsx`

---

## 🔧 Próximos Pasos

Comenzar con FASE 1:
1. Crear `types/stadium.types.ts` (consolidar tipos)
2. Crear `constants/stadium.constants.ts` (colores, tamaños)
3. Refactorizar `Scoreboard.tsx` (números +33%)
4. Refactorizar `GameInfo.tsx` (padding +50%, fuentes mejoradas)
5. Crear `GameHeader.tsx` (2-line layout)
6. Crear `CentralField.tsx` (organizador del campo central)

**Duración estimada FASE 1:** 45 minutos - 1 hora
**Complejidad:** Baja (reorganización, sin lógica nueva)

