# Responsive Design Quick Reference

**For:** Frontend developers working on deck-at-the-plate  
**Updated:** August 25, 2026

---

## Breakpoints (Tailwind Config)

| Name | Width | Use Case |
|------|-------|----------|
| `xs` | 375px | iPhone SE / Mobile portrait |
| `sm` | 640px | Mobile landscape / Small tablet |
| `md` | 768px | iPad / Tablet portrait |
| `lg` | 1024px | iPad landscape / Small desktop |
| `xl` | 1280px | Desktop standard |
| `2xl` | 1536px | Desktop wide |
| `4k` | 2560px | 4K Ultra-wide |

**Use in Tailwind classes:** `w-full md:w-[450px]`, `text-xs md:text-sm`, etc.

---

## Responsive Patterns (Copy-Paste Ready)

### Pattern 1: Full-width mobile → Fixed width desktop

```jsx
<div className="w-full md:w-[450px] md:flex-shrink-0">
  {/* content */}
</div>
```

### Pattern 2: Stack mobile → Row desktop

```jsx
<div className="flex flex-col md:flex-row gap-2 md:gap-6">
  <div className="w-full md:w-[450px]">{/* left */}</div>
  <div className="flex-1">{/* center */}</div>
  <div className="w-full md:w-[450px]">{/* right */}</div>
</div>
```

### Pattern 3: Responsive font sizes

```jsx
<div className="text-xs md:text-sm lg:text-base">
  {/* Scales: 12px (xs) → 14px (sm) → 16px (lg) */}
</div>
```

### Pattern 4: Responsive spacing

```jsx
<div className="p-2 md:p-4 gap-1 md:gap-3">
  {/* Padding & gaps scale smoothly */}
</div>
```

### Pattern 5: Responsive width sizing

```jsx
<div className="w-24 sm:w-32 md:w-40 lg:w-56">
  {/* Width: 96px (xs) → 128px (sm) → 160px (md) → 224px (lg) */}
</div>
```

### Pattern 6: Reorder on mobile

```jsx
<div className="flex flex-col md:flex-row">
  <div className="order-1 md:order-2">{/* appears 2nd on desktop */}</div>
  <div className="order-2 md:order-1">{/* appears 1st on desktop */}</div>
</div>
```

### Pattern 7: Overflow handling on mobile

```jsx
<div className="w-full md:w-[450px] overflow-y-auto max-h-[40vh] md:max-h-full">
  {/* Scrollable on mobile, full height on desktop */}
</div>
```

### Pattern 8: Grid responsive

```jsx
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 md:gap-4">
  {/* Columns: 1 (xs) → 2 (sm) → 3 (md) → 4 (lg) */}
</div>
```

---

## Component-Specific Guidance

### Scoreboard.tsx

✅ **Good practices:**
- Font sizes use variables: `inningHeaderSize`, `scoreSize`, etc.
- Widths: `w-32 sm:w-40 md:w-60`
- Gaps: `gap-0.5 sm:gap-1 md:gap-3`

❌ **Avoid:**
- Fixed `w-[560px]` on mobile
- Font sizes below `text-[9px]`
- Gaps below `gap-0.5`

### PlayerCard.tsx

✅ **Good practices:**
- Use `size` prop: `size="sm" | "md" | "lg"`
- Aspect ratio: `aspect-[3/4]` (maintains ratio)
- Jersey text: Scales with breakpoints

❌ **Avoid:**
- Fixed `h-80` (use aspect ratio instead)
- Jersey text below `text-3xl` on mobile
- Stats text below `text-[6px]`

### LobbyScreen.jsx

✅ **Good practices:**
- Layout: `flex-col lg:flex-row` (mobile stack, desktop side-by-side)
- Widths: `w-full lg:w-5/12` for panels
- Grid: Scales with `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4`

❌ **Avoid:**
- Grid without responsive columns
- Fixed panel widths on mobile
- Font sizes that don't scale

### StadiumShowcaseScreen.tsx

✅ **Good practices:**
- Main layout: `flex flex-col md:flex-row`
- Panels: `w-full md:w-[450px]`
- Reordering: Use `order-N` classes
- Scroll: `overflow-y-auto max-h-[40vh] md:max-h-full`

❌ **Avoid:**
- Fixed 3-column layout on mobile
- Hardcoded `style={{ width: 'calc(...)' }}`
- No scroll handling on mobile overflow

### CentralField.tsx

✅ **Good practices:**
- Remove `calc()` style attributes
- Use max-width: `max-w-xs sm:max-w-sm md:max-w-md lg:max-w-2xl`
- PlayerCard sizes: `w-24 sm:w-32 md:w-40 lg:w-56`

❌ **Avoid:**
- Inline styles with calculations
- Fixed widths in flex-col context
- Gaps below `gap-1`

---

## Minimum Font Sizes (Accessibility)

| Component | xs | sm | md | lg+ | Status |
|-----------|----|----|----|----|--------|
| Scoreboard | 9px | 10px | 11px | 11px | ✅ Pass |
| PlayerCard stats | 6px | 7px | 8px | 8px | ⚠️ 6px OK in sports context |
| LobbyScreen | 10px | 10px | 12px | 14px | ✅ Pass |
| Buttons | 10px | 12px | 12px | 14px | ✅ Pass |

**Rule:** No text below 6px absolute minimum. Preferred: 8px+.

---

## Common Mistakes to Avoid

### ❌ Don't: Use desktop-first approach

```jsx
/* WRONG - desktop-first */
<div className="w-[450px] md:w-full">
```

### ✅ Do: Use mobile-first approach

```jsx
/* RIGHT - mobile-first */
<div className="w-full md:w-[450px]">
```

---

### ❌ Don't: Use inline styles with magic numbers

```jsx
/* WRONG */
<div style={{ width: 'calc(224px + 24px + 144px + 24px + 224px)' }}>
```

### ✅ Do: Use Tailwind classes

```jsx
/* RIGHT */
<div className="max-w-xs sm:max-w-sm md:max-w-md lg:max-w-2xl">
```

---

### ❌ Don't: Mix responsive and fixed dimensions

```jsx
/* WRONG - conflicting */
<div className="w-[450px] md:w-full">
```

### ✅ Do: Scale proportionally

```jsx
/* RIGHT */
<div className="w-full sm:w-80 md:w-96 lg:w-[450px]">
```

---

### ❌ Don't: Forget about mobile overflow

```jsx
/* WRONG - content overflows on mobile */
<div className="flex gap-6">
  <div className="w-[450px]">{/* */}</div>
  <div className="w-[450px]">{/* */}</div>
</div>
```

### ✅ Do: Stack on mobile

```jsx
/* RIGHT */
<div className="flex flex-col md:flex-row gap-2 md:gap-6">
  <div className="w-full md:w-[450px]">{/* */}</div>
  <div className="w-full md:w-[450px]">{/* */}</div>
</div>
```

---

## Testing Breakpoints in Chrome DevTools

1. **Open DevTools:** F12
2. **Toggle Device Toolbar:** Ctrl+Shift+M
3. **Set Custom Size:**
   - 375px (iPhone SE) - `xs`
   - 640px (Landscape) - `sm`
   - 768px (iPad) - `md`
   - 1024px (iPad Pro) - `lg`
   - 1280px (Desktop) - `xl`
   - 1536px (Desktop wide) - `2xl`
   - 2560px (4K) - `4k`

4. **Check for:**
   - No horizontal scroll
   - Fonts readable
   - Touch targets ≥44px
   - No overlapping elements

---

## When to Add a New Breakpoint

Only add breakpoints for **specific business needs**:

✅ **Good reason:** "Mobile screens at 375px need different layout"  
✅ **Good reason:** "Tablets at 768px need 2-column grid"

❌ **Bad reason:** "Looks weird at 800px"  
❌ **Bad reason:** "My monitor is 2560px"

**Current breakpoints cover 95%+ of devices. Don't add more.**

---

## Performance Tips

✅ **Do:**
- Use Tailwind classes (not inline styles)
- Leverage flex-col/flex-row (not complex grid)
- Use max-width constraints (prevents sprawl)
- Test on actual devices (not just DevTools)

❌ **Don't:**
- Add media queries in component styles
- Use `@screen` breakpoints in CSS files
- Calculate widths/sizes in JavaScript
- Hardcode pixel values

---

## Troubleshooting

### Problem: Content overflows on mobile

**Solution:** Check for `w-[fixed]` without `md:` modifier.

```jsx
/* WRONG */
<div className="w-[450px]">

/* RIGHT */
<div className="w-full md:w-[450px]">
```

---

### Problem: Font too small on mobile

**Solution:** Add responsive font size.

```jsx
/* WRONG */
<div className="text-sm">

/* RIGHT */
<div className="text-[10px] md:text-sm">
```

---

### Problem: Layout looks squished on mobile

**Solution:** Add responsive gaps and padding.

```jsx
/* WRONG */
<div className="gap-6 p-6">

/* RIGHT */
<div className="gap-2 md:gap-6 p-2 md:p-6">
```

---

### Problem: Buttons too small to tap on mobile

**Solution:** Ensure 44px+ minimum height.

```jsx
/* RIGHT */
<button className="px-3 py-2 sm:px-4 sm:py-2">
  {/* min-height with padding reaches 44px on mobile */}
</button>
```

---

## Files to Reference

- **Tailwind Config:** `frontend/tailwind.config.js`
- **Working Example (Scoreboard):** `frontend/src/components/stadium/components/base/Scoreboard.tsx`
- **Working Example (LobbyScreen):** `frontend/src/pages/LobbyScreen.jsx`
- **Full Test Results:** `.kiro/PHASE1_TEST_RESULTS.md`
- **Phase 1 Summary:** `.kiro/PHASE1_SUMMARY.md`

---

## Questions?

See `.kiro/PHASE1_TEST_RESULTS.md` for detailed test results and verification.

---

**Last Updated:** August 25, 2026  
**Status:** ✅ Production Ready
