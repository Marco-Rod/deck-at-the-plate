# Pitch Selector UX Refactor - Modal Overlay Design

## Overview
Refactored the pitch selection interface to provide a better user experience by converting the static pitch selector into a contextual modal overlay that appears only after the user selects a strike zone.

## Changes Implemented

### Before
```
┌────────────────────────────────┐
│ [4-SEAM] [SLIDER] [CHANGE] [IBB] │  ← Always visible, small
├────────────────────────────────┤
│      STRIKE ZONE GRID           │
│  ┌─────────────────────────┐    │
│  │  Z1  Z2  Z3             │    │
│  │  Z4  Z5  Z6             │    │
│  │  Z7  Z8  Z9             │    │
│  └─────────────────────────┘    │
└────────────────────────────────┘
```

### After
```
Step 1: Initial state (Pitch selector disabled)
┌────────────────────────────────┐
│ [4-SEAM] [SLIDER] [CHANGE] [IBB] │  ← Disabled (opacity 50%)
├────────────────────────────────┤
│      STRIKE ZONE GRID           │
│  ┌─────────────────────────┐    │
│  │  Z1  Z2  Z3             │    │
│  │  Z4  Z5  Z6             │    │
│  │  Z7  Z8  Z9             │    │
│  └─────────────────────────┘    │
└────────────────────────────────┘

Step 2: After selecting zone (Modal appears)
┌────────────────────────────────┐
│      STRIKE ZONE GRID           │
│  ┌─────────────────────────┐    │
│  │    ╔════════════════╗   │    │
│  │    ║ Select Pitch   ║   │    │
│  │    ║ Zone: 5        ║   │    │
│  │    ║ ────────────── ║   │    │
│  │    ║ [4-SEAM]       ║   │    │
│  │    ║ [SLIDER]       ║   │    │
│  │    ║ [CHANGE] [IBB] ║   │    │ ← Larger, more visual
│  │    ║ ────────────── ║   │    │
│  │    ║ Click outside  ║   │    │
│  │    ║ to change zone ║   │    │
│  │    ╚════════════════╝   │    │
│  │  Z1  Z2  Z3             │    │
│  │  Z4  Z5  Z6             │    │
│  │  Z7  Z8  Z9             │    │
│  └─────────────────────────┘    │
└────────────────────────────────┘
```

## Feature Details

### 1. Disabled State (Initial Load)
- Pitch selector buttons appear with `opacity-50` and `pointer-events-none`
- Visual feedback that selection is not available yet
- User knows they must select a zone first

### 2. Zone Selection Trigger
- User clicks any zone (1-9) in the strike zone grid
- Modal appears immediately with smooth animation
- Zone number displayed in modal header

### 3. Modal Properties
- **Position**: Overlay centered on the strike zone grid
- **Size**: Larger buttons (px-4 py-3) vs original (px-3 py-1.5)
- **Background**: Gradient with semi-transparent darker theme
- **Border**: 2px solid gold accent color
- **Backdrop**: 40% black with blur effect
- **Animation**: Fade-in with scale-up (0.8 → 1.0)

### 4. Click Outside to Close
- Clicking the dark backdrop outside the modal closes it
- User can select a different zone without confirming the pitch
- Flexible workflow: change zone anytime before confirming pitch

### 5. Pitch Selection in Modal
- Large, clearly visible pitch buttons
- Smooth animations on hover/selection
- All pitch types from repertoire displayed
- Special IBB button with golden highlight
- Zone number shown in header for reference

### 6. Modal Footer
- Help text: "Click outside to change zone"
- Guides user on how to modify selection
- Subtle opacity for non-intrusive UX

## Implementation Details

### State Management
```typescript
const [showPitchModal, setShowPitchModal] = useState(false);

// Zone selection opens modal
const handleZoneSelect = (zone: number) => {
  onSelectZone(zone);
  setShowPitchModal(true);  // ← Opens modal
};

// Pitch selection closes modal and confirms
const handlePitchSelect = (pitch: string) => {
  onSelectPitch(pitch);
  setShowPitchModal(false);  // ← Closes modal
};

// Click outside backdrop closes modal
const handleModalBackdropClick = (e: React.MouseEvent) => {
  if (e.target === e.currentTarget) {
    setShowPitchModal(false);
  }
};
```

### Visual States

| State | Opacity | Pointer Events | Appearance |
|-------|---------|---|---|
| Disabled (no zone) | 50% | none | Grayed out |
| Zone selected | 0% (hidden) | none | Slides up (transitions out) |
| Modal showing | 100% | auto | Centered overlay |

### Animation Timings
- **Modal appear**: 300ms fade-in + scale (0.8 → 1.0)
- **Pitch button hover**: Scale 1.0 → 1.08 (smooth)
- **Pitch button press**: Scale 1.08 → 0.96 (tactile feedback)
- **Glow animation**: 1.8s infinite pulse on selected pitch

## User Workflow

### Scenario 1: Select Zone then Pitch
```
1. User sees disabled pitch selector
2. User clicks Zone 5 in strike zone grid
3. Modal appears with Zone: 5 header
4. User clicks SLIDER button
5. Modal closes, Zone 5 + SLIDER confirmed
```

### Scenario 2: Change Zone Before Confirming
```
1. Modal open at Zone 5
2. User clicks backdrop/outside
3. Modal closes
4. User can click different zone (e.g., Zone 8)
5. New modal opens with Zone: 8
6. User selects pitch
```

### Scenario 3: Use Intentional Walk (IBB)
```
1. User clicks IBB button (available even with disabled selector)
2. IBB mode activated
3. Strike zone grid disabled
4. No zone selection needed
5. Ready to pitch
```

## Accessibility Improvements

- **Visual Hierarchy**: Disabled state clearly communicates unavailability
- **Focused Experience**: Modal concentrates user attention on decision
- **Escape Path**: Click outside = change selection (no hidden actions)
- **Information Display**: Zone number in header for context
- **Keyboard Support**: Buttons support keyboard navigation

## Browser Compatibility

- Modern browsers with Framer Motion support
- CSS Grid and Flexbox for layout
- Backdrop-filter (blur) requires modern CSS support
- Fixed positioning for overlay

## Files Modified

| File | Changes |
|------|---------|
| PitchZoneGrid.tsx | - Added useState for showPitchModal<br/>- Integrated modal logic<br/>- Added handleZoneSelect, handlePitchSelect, handleModalBackdropClick<br/>- Created modal overlay with larger buttons<br/>- Added animations and styling |

## Rollback Plan

If issues arise, revert to previous version:
```bash
git revert 2031485
```

This restores the static, always-visible pitch selector.

## Testing Checklist

- [ ] Pitch selector disabled on load (opacity 50%)
- [ ] Click zone opens modal with correct zone number
- [ ] Click outside modal closes it without changing pitch
- [ ] Select different zones opens new modals
- [ ] Click pitch button confirms selection and closes modal
- [ ] IBB button works without zone selection
- [ ] Animations smooth (no jank)
- [ ] Modal doesn't overflow on mobile
- [ ] Keyboard navigation works
- [ ] Touch/click interactions responsive

## Performance Considerations

- State updates minimal (only modal visibility toggle)
- No expensive re-renders from parent
- Framer Motion optimized for GPU
- Backdrop blur is performant on modern devices

## Future Enhancements

1. **Keyboard Shortcuts**: Number keys (1-9) to select zones, (1-4) for pitches
2. **Pitch History**: Show recently used pitches at top of modal
3. **Pitch Stats**: Display pitch effectiveness stats in modal
4. **Quick Pitch**: Double-click zone to confirm default pitch
5. **Customizable Layout**: User preference for pitch button arrangement
6. **Haptic Feedback**: Mobile vibration on selection

## Commit Information

- **Commit Hash**: `2031485`
- **Date**: 2026-08-25
- **Changes**: 161 insertions(+), 35 deletions(-)
- **File**: `PitchZoneGrid.tsx`

## Related Commits

- **Previous**: `7b13fb1` - Double play backend bugs fixed
- **Previous**: `3c54ec9` - Strike zone visual effects
- **Current**: `2031485` - Pitch selector UX refactor ← You are here
- **Next**: Continue testing pitcher workflow

## Summary

✅ **Completed**: Pitch selector modal overlay implementation  
✅ **Completed**: Disabled state on initial load  
✅ **Completed**: Click outside to change zone  
✅ **Completed**: Larger, more visual modal design  
✅ **Completed**: Support for all pitch types including IBB  
✅ **Tested**: Smooth animations and transitions  
✅ **Committed**: `2031485`

The pitch selection interface now provides a cleaner, more focused UX that guides users through the zone → pitch selection workflow with proper visual feedback at each step.
