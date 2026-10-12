# Rarity Colors - Homologation Reference

## Overview

All card rarity colors are now **homologated** across the entire frontend:
- Onboarding Screen (PACK_UNBOX → SHOW_CARDS)
- Gameplay Stadium
- Deck management

All components use the same `RARITY_COLORS` mapping from the same source of truth.

---

## Color Mapping by Rarity

### DIAMOND (Tier 1 - Rarest)
```
borderColor:  #9966FF (Purple)
glowColor:    #9966FF
shadowColor:  rgba(153, 102, 255, 0.8)
```
**Visual**: Deep purple glow with high intensity
**UI Elements**: Border, Effects, Shadows with 80% opacity

---

### GOLD (Tier 2)
```
borderColor:  #FFD700 (Gold)
glowColor:    #FFD700
shadowColor:  rgba(255, 215, 0, 0.7)
```
**Visual**: Bright gold with medium-high intensity
**UI Elements**: Premium border, strong glow effect (70% opacity)

---

### SILVER (Tier 3)
```
borderColor:  #C0C0C0 (Silver)
glowColor:    #C0C0C0
shadowColor:  rgba(192, 192, 192, 0.6)
```
**Visual**: Silver metallic with medium intensity
**UI Elements**: Elegant silver border, moderate glow (60% opacity)

---

### BRONZE (Tier 4)
```
borderColor:  #CD7F32 (Bronze)
glowColor:    #CD7F32
shadowColor:  rgba(205, 127, 50, 0.6)
```
**Visual**: Bronze/copper tone with medium intensity
**UI Elements**: Bronze border, subtle glow (60% opacity)

---

### COMMON (Tier 5 - Most Common)
```
borderColor:  #808080 (Gray)
glowColor:    #808080
shadowColor:  rgba(128, 128, 128, 0.5)
```
**Visual**: Neutral gray with low intensity
**UI Elements**: Simple gray border, minimal glow (50% opacity)

---

## Source of Truth

### Primary Definition
**File**: `frontend/src/components/cards/PlayerCard.jsx` (Onboarding)
```javascript
const RARITY_COLORS = {
  DIAMOND: { border: '#9966FF', shadow: 'rgba(153, 102, 255, 0.8)', glow: '#9966FF' },
  GOLD: { border: '#FFD700', shadow: 'rgba(255, 215, 0, 0.7)', glow: '#FFD700' },
  SILVER: { border: '#C0C0C0', shadow: 'rgba(192, 192, 192, 0.6)', glow: '#C0C0C0' },
  BRONZE: { border: '#CD7F32', shadow: 'rgba(205, 127, 50, 0.6)', glow: '#CD7F32' },
  COMMON: { border: '#808080', shadow: 'rgba(128, 128, 128, 0.5)', glow: '#808080' },
};
```

### Mirror Definition
**File**: `frontend/src/components/stadium/constants/stadium.constants.ts` (Gameplay)
```typescript
export const RARITY_COLORS = {
  DIAMOND: { borderColor: '#9966FF', shadowColor: 'rgba(153, 102, 255, 0.8)', glowColor: '#9966FF' },
  GOLD: { borderColor: '#FFD700', shadowColor: 'rgba(255, 215, 0, 0.7)', glowColor: '#FFD700' },
  // ... (identical mapping)
} as const;
```

### Unified Implementation
**File**: `frontend/src/components/stadium/PlayerCard.tsx` (Gameplay Cards)
```typescript
const RARITY_COLOR_CONFIG = {
  DIAMOND: { accentColor: '#9966FF', glowColor: '#9966FF', shadowColor: 'rgba(153, 102, 255, 0.8)', tierLabel: 'DIAMOND' },
  // ... (unified with onboarding)
};

function getTierConfig(rarity?: string): TierConfig {
  const rarityKey = (rarity ?? 'COMMON').toUpperCase();
  return RARITY_COLOR_CONFIG[rarityKey];
}
```

---

## Component Usage

### Onboarding (PlayerCard from cards/)
```jsx
import { PlayerCard } from '../components/cards/PlayerCard';

<PlayerCard 
  card={card} 
  mode="full" 
  size="md"
/>
// Uses card.rarity property automatically
```

### Gameplay Stadium (PlayerCard from stadium/)
```tsx
import PlayerCard from '../components/stadium/PlayerCard';

<PlayerCard 
  player={playerData}
  role="BATTER"
  size="md"
/>
// Now uses player.rarity instead of overall rating
```

---

## Changes from Previous Implementation

### Before
**Stadium PlayerCard.tsx** used `getTierConfig(player?.overall)`:
- ELITE (OVR ≥ 90): #FFD700 (Gold)
- ALL-STAR (OVR ≥ 80): #C5A059 (Tan/Brass - NOT standard)
- STARTER (OVR ≥ 70): #4A90D9 (Blue - NOT standard)
- REGULAR (OVR ≥ 60): #6B7280 (Gray-blue)
- ROOKIE (OVR < 60): #9CA3AF (Light Gray)

**Problem**: Mismatch with onboarding colors. Overall rating doesn't correlate with card rarity.

### After
**Stadium PlayerCard.tsx** uses `getTierConfig(player?.rarity)`:
- DIAMOND: #9966FF (matches onboarding)
- GOLD: #FFD700 (matches onboarding)
- SILVER: #C0C0C0 (matches onboarding)
- BRONZE: #CD7F32 (matches onboarding)
- COMMON: #808080 (matches onboarding)

**Benefit**: Consistent colors across entire UI. Cards have the same visual identity everywhere.

---

## Visual Effects by Rarity

### Glow Intensity
Shadow opacity increases with rarity exclusivity:
- DIAMOND: 80% opacity → Maximum impact
- GOLD: 70% opacity
- SILVER: 60% opacity
- BRONZE: 60% opacity
- COMMON: 50% opacity → Minimal impact

### Border Styling
All rarities use consistent border patterns:
- Border color matches rarity
- Border thickness: 2-3px (responsive)
- Corner decorations optional (on epic cards)

### Animation
Glow effects pulse based on rarity (not implemented yet but reference exists in components/cards/PlayerCard.jsx):
```javascript
const getPulseIntensity = (rarity) => {
  const intensities = {
    DIAMOND: '0px 0px 20px, 0px 0px 40px',
    GOLD: '0px 0px 15px, 0px 0px 30px',
    SILVER: '0px 0px 12px, 0px 0px 25px',
    BRONZE: '0px 0px 10px, 0px 0px 20px',
    COMMON: '0px 0px 8px, 0px 0px 15px',
  };
  return intensities[rarity];
};
```

---

## Testing Checklist

- [ ] Onboarding cards display with correct rarity colors
- [ ] Gameplay stadium cards display with same colors
- [ ] Deck management shows consistent rarity colors
- [ ] Card selection/hover effects maintain rarity colors
- [ ] Mobile responsiveness preserved
- [ ] WCAG contrast ratios verified for accessibility

---

## Related Files

- `frontend/src/pages/OnboardingScreen.jsx` - Pack opening flow
- `frontend/src/components/cards/PlayerCard.jsx` - Rarity colors definition
- `frontend/src/components/stadium/PlayerCard.tsx` - UPDATED to use rarity
- `frontend/src/components/stadium/constants/stadium.constants.ts` - Mirror colors
- `frontend/src/components/stadium/constants/stadium.utils.ts` - Helper functions

---

## Migration Notes

If you're updating other components that previously used `getTierConfig(overall)`:

1. **Before**: `getTierConfig(player.overall)`
2. **After**: `getTierConfig(player.rarity)`
3. **Fallback**: `getTierConfig()` defaults to 'COMMON' if rarity not provided

Example:
```typescript
// Old approach (DON'T USE)
const colors = getTierConfig(player?.overall);

// New approach (CORRECT)
const colors = getTierConfig(player?.rarity);
```
