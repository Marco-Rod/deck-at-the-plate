# 🎮 Deck at the Plate - Responsive Design Roadmap

**Date**: August 25, 2026  
**Status**: Planning Phase  
**Target Breakpoints**: Mobile (375px), Tablet (768px), Desktop (1024px+), 4K (2560px+)

---

## 📋 Application Flow & Screens

```
┌─────────────────────────────────────────────────────┐
│                  APPLICATION ENTRY                  │
│                    (App.jsx)                        │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   [NO USER]         [USER LOGGED]
        │                 │
        │                 ▼
        │         ┌──────────────────┐
        │         │  LOBBY SCREEN    │
        │         └────┬──────┬──────┘
        │              │      └──────┐
        │              ▼             ▼
        │      [START GAME]  [MY TEAM / SHOWCASE]
        │              │
        ▼              ▼
   ┌─────────┐  ┌──────────────────────┐
   │ AUTH    │  │ ROSTER SELECTION     │
   │ SCREEN  │  │      SCREEN          │
   │         │  └──────────┬───────────┘
   ├─────────┤             │
   │ONBOARDING◄────────────┘
   │ SCREEN  │
   └────┬────┘
        │
        └──────────────────┐
                          ▼
                  ┌──────────────────┐
                  │  STADIUM SCREEN  │
                  │    (GAMEPLAY)    │
                  └──────────────────┘
```

---

## 🎯 Screen-by-Screen Analysis & Fixes

### 1️⃣ AuthScreen (LOGIN / REGISTER)

**File**: `frontend/src/pages/AuthScreen.jsx`

**Current Status**: ⚠️ PARTIALLY RESPONSIVE

**Current Layout**:
```jsx
<div className="w-screen h-screen flex items-center justify-center">
  <div className="max-w-md w-full p-6">
    {/* Form content */}
  </div>
</div>
```

**Issues Found**:
| Issue | Severity | Details |
|-------|----------|---------|
| `max-w-md` (448px) OK on mobile | 🟢 Minor | But padding `p-6` (24px) makes content 400px on 375px |
| Form inputs not scaled | 🟡 Medium | Text inputs fixed height, might be small on mobile |
| Button sizing fixed | 🟡 Medium | No responsive text/padding adjustment |
| Background image | 🟡 Medium | May not scale well on mobile |

**Responsive Requirements**:
- ✅ Already uses `max-w-md` (good)
- ❌ Add `p-4 md:p-6 lg:p-8` for responsive padding
- ❌ Add `text-sm md:text-base lg:text-lg` for input fields
- ❌ Add `w-full md:max-w-md` for flexible width
- ❌ Test on actual 375px device

**Priority**: 🟡 **MEDIUM** - Already mostly responsive, needs tweaks

**Estimated Effort**: 1-2 hours

---

### 2️⃣ OnboardingScreen (FRANCHISE SELECTION)

**File**: `frontend/src/pages/OnboardingScreen.jsx`

**Current Status**: 🔴 NOT RESPONSIVE

**Current Layout**:
```jsx
<div className="flex flex-col items-center justify-center min-h-screen w-screen">
  <div className="max-w-2xl w-[90%]"> {/* 90% but with fixed max-width */}
    {/* Team selection grid */}
  </div>
</div>
```

**Issues Found**:
| Issue | Severity | Details |
|-------|----------|---------|
| Grid layout hardcoded | 🔴 Critical | Likely `grid-cols-2` or `grid-cols-3` with no `sm:` variant |
| Team cards fixed size | 🔴 Critical | Cards may not scale properly on mobile |
| Font sizes hardcoded | 🟡 High | Team names, descriptions probably fixed px |
| Spacing fixed | 🟡 High | Gap, padding probably fixed |
| Starter pack modal | 🟡 High | Large modal may overflow on mobile |

**Responsive Requirements**:
- ❌ Change grid: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4`
- ❌ Scale team cards: `w-full aspect-square md:w-auto`
- ❌ Responsive fonts: `text-base md:text-lg lg:text-xl`
- ❌ Responsive spacing: `gap-2 md:gap-4 lg:gap-6`
- ❌ Modal: `max-w-sm md:max-w-md lg:max-w-xl`
- ❌ Add `overflow-y-auto` for scrolling on small screens

**Priority**: 🔴 **HIGH** - Critical for mobile gameplay

**Estimated Effort**: 3-4 hours

---

### 3️⃣ LobbyScreen (MAIN MENU)

**File**: `frontend/src/pages/LobbyScreen.jsx`

**Current Status**: 🔴 NOT RESPONSIVE

**Current Layout**:
```jsx
<div className="w-screen h-screen flex flex-col items-center justify-center">
  <div className="max-w-4xl w-[90%]">
    {/* Header */}
    {/* Buttons/cards for game modes */}
  </div>
</div>
```

**Issues Found**:
| Issue | Severity | Details |
|-------|----------|---------|
| Button grid fixed | 🔴 Critical | Probably `grid-cols-3` or flex row with fixed widths |
| Card sizing hardcoded | 🔴 Critical | Game mode cards may have fixed `w-80` or similar |
| Navigation buttons | 🔴 Critical | `onOpenMyTeam`, `onOpenShowcase` buttons may not fit |
| User info display | 🟡 High | User avatar/name placement fixed |
| Text sizes | 🟡 High | Title, button text probably hardcoded |

**Responsive Requirements**:
- ❌ Button grid: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3` with `gap-2 md:gap-4`
- ❌ Cards: `w-full sm:w-auto` with responsive aspect ratio
- ❌ Navigation bar: Stack vertically on mobile, horizontal on tablet+
- ❌ User info: `flex-col md:flex-row` layout switching
- ❌ Fonts: `text-xl md:text-2xl lg:text-3xl`
- ❌ Padding: `p-4 md:p-6 lg:p-8`

**Priority**: 🔴 **HIGH** - Main entry point after login

**Estimated Effort**: 4-5 hours

---

### 4️⃣ MyTeamScreen (ROSTER MANAGEMENT)

**File**: `frontend/src/pages/MyTeamScreen.jsx`

**Current Status**: 🔴 NOT RESPONSIVE

**Current Layout**:
```jsx
<div className="w-screen h-screen flex flex-col">
  <header className="w-full h-16"> {/* Fixed height header */}
  <main className="flex-1 flex">
    <div className="w-1/4"> {/* Player list - 25% */}
    <div className="w-3/4"> {/* Player detail/grid - 75% */}
  </main>
</div>
```

**Issues Found**:
| Issue | Severity | Details |
|-------|----------|---------|
| **2-column fixed split** | 🔴 Critical | `w-1/4` + `w-3/4` doesn't work on mobile |
| Player cards hardcoded | 🔴 Critical | Likely `w-64`, `h-80` with fixed aspect |
| Grid layout fixed | 🔴 Critical | Probably `grid-cols-4` or `grid-cols-6` |
| Search/filter bar | 🟡 High | May not scale |
| Stat display | 🟡 High | Player stats probably too small on mobile |
| Header fixed height | 🟡 High | 64px may be too large or too small depending on device |

**Responsive Requirements**:
- ❌ Layout: `flex-col md:flex-row` (stack on mobile, side-by-side on tablet+)
- ❌ Left panel: `w-full md:w-1/4 mb-4 md:mb-0`
- ❌ Right panel: `w-full md:w-3/4`
- ❌ Grid: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4`
- ❌ Cards: `w-full h-auto aspect-[3/4]` instead of hardcoded dimensions
- ❌ Header: `h-auto md:h-16` with responsive padding
- ❌ Add `sticky` header for mobile scroll
- ❌ Add `overflow-y-auto` for scrollable sections

**Priority**: 🔴 **HIGH** - Important for team management

**Estimated Effort**: 4-5 hours

---

### 5️⃣ CardShowcaseScreen (CARD ALBUM)

**File**: `frontend/src/pages/CardShowcaseScreen.jsx`

**Current Status**: 🔴 NOT RESPONSIVE

**Current Layout**:
```jsx
<div className="w-screen h-screen flex flex-col">
  <header className="w-full h-20"> {/* Fixed height */}
  <main className="flex-1 flex">
    <sidebar className="w-1/5"> {/* Position filter - 20% */}
    <grid className="w-4/5"> {/* Card grid - 80% */}
      {/* Cards with PositionTile component */}
  </main>
</div>
```

**Issues Found**:
| Issue | Severity | Details |
|-------|----------|---------|
| **Sidebar fixed split** | 🔴 Critical | `w-1/5` + `w-4/5` breaks on mobile |
| Position tiles hardcoded | 🔴 Critical | Likely `w-48`, `h-64` or similar |
| Grid columns fixed | 🔴 Critical | Probably `grid-cols-5` or `grid-cols-6` |
| Card images | 🔴 Critical | May not scale, aspect ratio issues |
| Position buttons | 🟡 High | Filter buttons may have fixed width |
| Typography | 🟡 High | Player name, team, position text probably hardcoded |

**Responsive Requirements**:
- ❌ Layout: `flex-col md:flex-row` with sidebar stacking on mobile
- ❌ Sidebar: `w-full md:w-1/5 mb-4 md:mb-0` with `max-h-32 md:max-h-full overflow-x-auto md:overflow-y-auto`
- ❌ Grid: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5`
- ❌ Cards: `w-full h-auto aspect-[3/4]` instead of hardcoded
- ❌ Position buttons: `px-2 py-1 md:px-3 md:py-2 text-xs md:text-sm`
- ❌ Header: `h-auto md:h-20 p-4 md:p-0`
- ❌ Add search/filter collapse on mobile

**Priority**: 🟡 **MEDIUM-HIGH** - Important but not critical for core gameplay

**Estimated Effort**: 4-5 hours

---

### 6️⃣ RosterSelectionScreen (LINEUP PICKER)

**File**: `frontend/src/pages/RosterSelectionScreen.jsx`

**Current Status**: 🔴 NOT RESPONSIVE

**Current Layout**:
```jsx
<div className="w-screen h-screen flex flex-col">
  <header className="w-full h-24"> {/* Large fixed header */}
  <main className="flex-1 flex">
    <left-panel className="w-96"> {/* Player pool - 384px */}
    <center-panel className="flex-1"> {/* Field position grid */}
    <right-panel className="w-96"> {/* Info panel - 384px */}
  </main>
</div>
```

**Issues Found**:
| Issue | Severity | Details |
|-------|----------|---------|
| **3-column fixed layout** | 🔴 Critical | `w-96` panels = 768px + gaps; impossible on mobile |
| Field grid hardcoded | 🔴 Critical | Probably fixed position circles for bases/positions |
| Player cards | 🔴 Critical | `w-56`, `h-80` too large for mobile |
| Drag-drop UI | 🔴 Critical | May not work on touchscreen without adaptation |
| Select buttons | 🟡 High | Probably fixed size |
| Typography | 🟡 High | Player names, stats hardcoded sizes |

**Responsive Requirements**:
- ❌ Layout: `flex-col md:flex-col lg:flex-row` (stack all on mobile/tablet, 3-col on desktop only)
- ❌ Left panel: `w-full lg:w-96 h-auto lg:h-full overflow-y-auto`
- ❌ Center panel: `w-full lg:flex-1 h-auto`
- ❌ Right panel: `w-full lg:w-96 h-auto lg:h-full overflow-y-auto`
- ❌ Field grid: Scale positions dynamically `scale-75 md:scale-100 lg:scale-125`
- ❌ Player cards: `w-full sm:w-1/2 md:w-1/3 lg:w-56`
- ❌ Drag-drop: Add touch event handlers for mobile
- ❌ Header: `h-auto md:h-24 p-4 md:p-6`

**Priority**: 🔴 **CRITICAL** - Core gameplay feature

**Estimated Effort**: 5-6 hours

---

### 7️⃣ StadiumShowcaseScreen (MAIN GAMEPLAY - LARGEST COMPONENT)

**File**: `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`

**Current Status**: 🔴 COMPLETELY NOT RESPONSIVE

**Current Layout**:
```tsx
<main className="w-[95%] mx-auto flex justify-between items-center min-h-[500px]">
  <div className="w-[450px] flex-shrink-0"> {/* LEFT: Lineup + Stats */}
  <CentralField /> {/* CENTER: Field + Card Reveal */}
  <div className="w-[450px] flex-shrink-0"> {/* RIGHT: Pitcher Info */}
</main>
```

**Critical Issues** (See detailed analysis in previous context):
| Issue | Severity | Component | Details |
|-------|----------|-----------|---------|
| **450px panels fixed** | 🔴 CRITICAL | Main layout | 900px panels alone; impossible on mobile |
| **Scoreboard hardcoded** | 🔴 CRITICAL | Scoreboard.tsx | `w-60` + `w-9×9` + `w-11×3` = 700px minimum |
| **Player cards 224×320** | 🔴 CRITICAL | PlayerCard.tsx | Fixed `w-56 h-80` with `text-[5px]` fonts |
| **Central field calc** | 🔴 CRITICAL | CentralField.tsx | `width: calc(224px + ...)` hardcoded |
| **GameplayDeck fixed** | 🔴 CRITICAL | GameplayDeckAndReveal.tsx | `w-72` reveal card = 288px |
| **All fonts 5px-18px** | 🔴 CRITICAL | Multiple | Unreadable below 1400px viewport |
| **No flex-wrap** | 🔴 CRITICAL | Main layout | No stacking on mobile |

**Responsive Requirements** (Detailed breakdown by component):

#### 7a. StadiumShowcaseScreen Main Layout
```tsx
// FROM:
<main className="flex justify-between items-center min-h-[500px]">

// TO:
<main className="flex flex-col md:flex-col lg:flex-row justify-between items-center min-h-[500px] gap-4">
  {/* Mobile: Stack vertically, full-width panels */}
  {/* Tablet: Still stack or arrange differently */}
  {/* Desktop: 3-column layout */}
</main>
```

**Changes**:
- ❌ `w-[450px]` → `w-full lg:w-[450px]`
- ❌ `flex-shrink-0` → `lg:flex-shrink-0`
- ❌ Add `flex-col md:flex-col lg:flex-row` to main
- ❌ Scoreboard: `w-full md:w-[95%] lg:w-full overflow-x-auto`

#### 7b. Scoreboard Component
```tsx
// Issues:
- Team name: w-60 (240px) → w-1/3 md:w-60
- Inning columns: w-9 (36px) per inning → w-8 md:w-9 (compress on mobile)
- Fonts: text-[13px] → text-[10px] md:text-[13px]

// New approach:
<Scoreboard 
  compact={isMobile} // Pass flag to component
  scale={viewportWidth < 768 ? 0.75 : 1}
/>
```

**New Scoreboard structure**:
```tsx
{/* Mobile version: compress everything */}
<div className="w-full overflow-x-auto">
  <div className="min-w-max">
    {/* Compressed inning columns */}
  </div>
</div>

{/* Desktop version: full size */}
<div className="w-full">
  {/* Normal size */}
</div>
```

#### 7c. PlayerCard Component
```tsx
// FROM:
<div className="w-56 h-80">
  <span className="text-5xl"> {/* jersey */}
  <span className="text-[5px]"> {/* stats */}

// TO:
<div className="w-full sm:w-48 md:w-56 aspect-[3/4]">
  <span className="text-4xl sm:text-5xl md:text-6xl"> {/* jersey */}
  <span className="text-[8px] sm:text-[9px] md:text-[10px]"> {/* stats */}
```

**Changes**:
- ❌ Width: `w-56` → `w-full sm:w-48 md:w-56`
- ❌ Height: `h-80` → `aspect-[3/4]` (maintains ratio)
- ❌ Jersey #: `text-5xl` → `text-3xl sm:text-4xl md:text-5xl lg:text-6xl`
- ❌ Stats: `text-[5px]` → `text-[6px] sm:text-[7px] md:text-[8px] lg:text-[10px]`
- ❌ Player name: `text-[10px]` → `text-[8px] sm:text-[9px] md:text-[10px]`
- ❌ Team name: `text-[8px]` → `text-[6px] sm:text-[7px] md:text-[8px]`

#### 7d. CentralField Component
```tsx
// FROM:
style={{ width: 'calc(224px + 24px + 144px + 24px + 224px)' }}

// TO:
className="w-full md:w-[calc(224px+48px+144px)] lg:w-auto"
```

**Changes**:
- ❌ Replace inline calc with CSS Grid or Flex with minmax
- ❌ Dynamic sizing based on available space
- ❌ `grid grid-cols-[auto_auto_auto] gap-4 md:gap-6`

#### 7e. GameplayDeckAndReveal Component
```tsx
// FROM:
<div className="w-72"> {/* 288px */}

// TO:
<div className="w-48 sm:w-56 md:w-64 lg:w-72 aspect-[3/4]">
```

**Changes**:
- ❌ Width: `w-72` → `w-48 sm:w-56 md:w-64 lg:w-72`
- ❌ Height: Use aspect ratio instead of hardcoded
- ❌ Positioning: `bottom-4 left-6` → `bottom-2 sm:bottom-4 left-2 sm:left-6`
- ❌ Animation: Scale down on mobile if needed

#### 7f. GameInfo Component
```tsx
// FROM:
<div style={{ width: 'calc(224px + 24px + 144px + 24px + 224px)' }}>

// TO:
<div className="w-full md:w-auto flex flex-col sm:flex-row gap-2 sm:gap-4">
```

**Changes**:
- ❌ Remove inline calc
- ❌ Use Flexbox with responsive flex-direction
- ❌ Pitcher card: `w-full sm:w-56`
- ❌ Info: `w-full sm:w-36`
- ❌ Batter card: `w-full sm:w-56`

#### 7g. LineupPanel Component
```tsx
// FROM:
<span className="text-[13px]">
<span className="text-[10px]"> {/* stats */}

// TO:
<span className="text-[10px] sm:text-[11px] md:text-[13px]">
<span className="text-[8px] sm:text-[9px] md:text-[10px]">
```

#### 7h. TacticalHand Component
```tsx
// Already has: flex-col md:flex-row (GOOD!)
// But card size needs adjustment:
// From: w-40 (160px)
// To: w-24 sm:w-32 md:w-40 lg:w-48
```

---

## 📱 Breakpoint Strategy

Define custom breakpoints in `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      screens: {
        'xs': '375px',   // iPhone SE
        'sm': '640px',   // Small phones
        'md': '768px',   // Tablets
        'lg': '1024px',  // Large tablets / small laptops
        'xl': '1280px',  // Laptops
        '2xl': '1536px', // Desktops
        '4k': '2560px',  // 4K monitors
      },
    }
  }
}
```

**Usage**:
```tsx
<div className="w-full xs:w-[375px] sm:w-96 md:w-[768px] lg:w-[1024px]">
```

---

## 🎯 Implementation Order (Priority)

### Phase 1: CRITICAL (Week 1-2)
1. **AuthScreen** - 2 hours - MEDIUM priority
2. **LobbyScreen** - 5 hours - HIGH priority
3. **StadiumShowcaseScreen Main Layout** - 3 hours - CRITICAL priority

### Phase 2: HIGH (Week 2-3)
4. **Scoreboard Component** - 3 hours
5. **PlayerCard Component** - 2 hours
6. **GameplayDeckAndReveal** - 2 hours

### Phase 3: MEDIUM (Week 3-4)
7. **RosterSelectionScreen** - 6 hours
8. **OnboardingScreen** - 4 hours

### Phase 4: MEDIUM (Week 4)
9. **MyTeamScreen** - 5 hours
10. **CardShowcaseScreen** - 5 hours

---

## 🧪 Testing Breakpoints

After implementation, test at these viewport widths:

```
xs (375px)  - iPhone SE, small Android
sm (640px)  - iPhone 12/13/14, standard phone
md (768px)  - iPad, small tablet
lg (1024px) - iPad Pro, large tablet
xl (1280px) - MacBook Air, standard laptop
2xl (1536px) - Full HD Desktop
4k (2560px) - 4K Monitor (32")
```

**Test tools**:
- Chrome DevTools responsive mode
- Firefox responsive design mode
- [Responsively App](https://responsively.app)
- Physical device testing (iPhone, iPad, Android)

---

## 📊 Metric Targets

| Metric | Target | Current |
|--------|--------|---------|
| Minimum viewport width | 375px | 1920px |
| Font size (min) | 12px | 5px |
| Panel width (max) | 100% | 450px |
| Scoreboard fit width | 375px | 700px+ |
| Mobile display | Full (no scroll) | Broken |
| Tablet display | Optimized | Poor |
| Touch target size | ≥44px | Varies |

---

## 📝 Component Checklist

### AuthScreen
- [ ] Add `p-4 md:p-6 lg:p-8` for responsive padding
- [ ] Add `text-sm md:text-base` for form text
- [ ] Test at 375px, 768px, 1024px

### OnboardingScreen
- [ ] Change grid: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4`
- [ ] Add `aspect-square` to team cards
- [ ] Responsive fonts and spacing
- [ ] Test modal overflow

### LobbyScreen
- [ ] Responsive button grid
- [ ] Navigation bar stacking
- [ ] User info layout switching
- [ ] Test all breakpoints

### MyTeamScreen
- [ ] Layout: `flex-col md:flex-row`
- [ ] Responsive grid: `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4`
- [ ] Sticky header on mobile
- [ ] Test drag/drop on touch

### CardShowcaseScreen
- [ ] Sidebar layout switching
- [ ] Responsive grid
- [ ] Filter button stacking
- [ ] Test image scaling

### RosterSelectionScreen
- [ ] 3-column → stack layout
- [ ] Field grid scaling
- [ ] Touch event handling
- [ ] Drag-drop adaptation

### StadiumShowcaseScreen (CRITICAL)
- [ ] Main layout: 3-col → stack → 3-col
- [ ] Scoreboard scaling
- [ ] PlayerCard sizing
- [ ] All sub-component responsive updates
- [ ] Extensive testing

---

## 🔧 Configuration Files to Update

### 1. `tailwind.config.js`
Add custom breakpoints (see breakpoint strategy section above)

### 2. `frontend/src/index.css`
Add custom media query utilities if needed:
```css
@media (max-width: 767px) {
  .compact-mobile { /* mobile-specific styles */ }
}
```

### 3. New component props
Add responsive props to stadium components:
```tsx
interface ResponsiveProps {
  compact?: boolean;    // Mobile layout
  scale?: number;       // Scale factor
  hideOn?: string[];    // Hide on breakpoints
  showOn?: string[];    // Show on breakpoints
}
```

---

## 📚 Reference Links

- [Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [MDN: CSS Media Queries](https://developer.mozilla.org/en-US/docs/Web/CSS/Media_Queries)
- [Material Design Breakpoints](https://material.io/design/layout/responsive-layout-grid.html)
- [Apple HIG - Layout](https://developer.apple.com/design/human-interface-guidelines/ios/visual-design/layout/)

---

## 💡 Best Practices

1. **Mobile First**: Design for 375px first, then enhance for larger screens
2. **Progressive Enhancement**: Start with content layout, add features for larger screens
3. **Touch Targets**: Minimum 44×44px for touch interfaces on mobile
4. **Typography**: Use relative sizes (rem, em) instead of pixels when possible
5. **Images**: Use responsive images with srcset
6. **Flexbox/Grid**: Prefer modern CSS layout over hardcoded widths
7. **Testing**: Test on real devices, not just DevTools
8. **Performance**: Consider lazy loading images on mobile
9. **Accessibility**: Maintain color contrast, touch target sizes
10. **No Horizontal Scroll**: Mobile layouts should never scroll horizontally (except for sliders)

---

## 🎬 Next Steps

1. Review this document with team
2. Prioritize which screens to tackle first
3. Create individual tickets/issues for each screen
4. Set up testing framework for breakpoint validation
5. Begin Phase 1 implementation
6. Weekly review and adjustment

---

**Document Version**: 1.0  
**Last Updated**: August 25, 2026  
**Next Review**: After Phase 1 completion
