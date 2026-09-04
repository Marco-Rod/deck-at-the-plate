/**
 * StadiumPage CSS Module Test - Task 11 Verification
 *
 * This test verifies that:
 * 1. Mobile viewport styles (<1200px) are preserved
 * 2. Desktop styles apply at >=1200px
 * 3. Breakpoint boundaries are correctly set at 1200px
 * 4. All typography enhancements target desktop only
 *
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('StadiumPage.module.css - Task 11 Verification', () => {
  const cssPath = resolve(process.cwd(), 'src/features/game/pages/StadiumPage.module.css')
  const cssContent = readFileSync(cssPath, 'utf-8')

  describe('Requirement 8.4: Desktop rules use @media (min-width: 1200px)', () => {
    it('should have desktop media query at 1200px breakpoint', () => {
      // Verify the desktop media query exists
      expect(cssContent).toContain('@media (min-width: 1200px)')
    })

    it('should NOT have desktop rules below 1200px', () => {
      // Verify no desktop-specific rules at lower breakpoints
      expect(cssContent).not.toMatch(/@media \(min-width: (1199|1180|1100)px\)/)
    })

    it('should have mobile/tablet media queries below 1200px', () => {
      // Verify mobile and tablet breakpoints exist
      expect(cssContent).toMatch(/@media \(max-width: 1199(\.98)?px\)/)
      expect(cssContent).toContain('@media (max-width: 767px)')
      expect(cssContent).toContain('@media (min-width: 768px) and (max-width: 1199px)')
    })
  })

  describe('Requirements 1.1, 1.2: PlayerCard typography scaling in desktop only', () => {
    it('should scale player numbers (.font-sports) in desktop viewport', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Player numbers should have clamp with minimum 48px
      expect(desktopSection).toMatch(/\.playerCard.*\.font-sports.*font-size:\s*clamp\(48px/s)
    })

    it('should scale player names (.font-vintage) in desktop viewport', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Player names should have clamp with minimum 14px
      expect(desktopSection).toMatch(/\.playerCard.*\.font-vintage.*font-size:\s*clamp\(14px/s)
    })

    it('should NOT modify player card typography in mobile sections', () => {
      const mobileSection = extractMobileSection(cssContent)

      // Mobile section should not contain playerCard font-size modifications for .font-sports or .font-vintage
      expect(mobileSection).not.toMatch(/\.playerCard.*\.font-sports.*font-size/)
      expect(mobileSection).not.toMatch(/\.playerCard.*\.font-vintage.*font-size/)
    })
  })

  describe('Requirements 2.1, 2.2, 2.3: Statistics display typography in desktop only', () => {
    it('should scale stat labels to 11px minimum in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Stat labels should be 11px in desktop
      expect(desktopSection).toMatch(
        /\.playerCard.*grid-cols-3.*\.font-vintage.*font-size:\s*11px/s,
      )
    })

    it('should scale stat values to 16px minimum in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Stat values should be 16px in desktop
      expect(desktopSection).toMatch(/\.playerCard.*grid-cols-3.*\.font-sports.*font-size:\s*16px/s)
    })

    it('should increase hover scale to 1.08 in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Hover effect should scale to 1.08
      expect(desktopSection).toMatch(
        /\.playerCard.*grid-cols-3.*:hover.*transform:\s*scale\(1\.08\)/s,
      )
    })
  })

  describe('Requirements 3.1, 3.2: Scoreboard typography in desktop only', () => {
    it('should scale score numbers to minimum 42px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Score numbers should have clamp with minimum 42px
      expect(desktopSection).toMatch(/\.areaScore.*\.font-sports.*font-size:\s*clamp\(42px/s)
    })

    it('should scale team labels to 12px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      // Team labels should be 12px
      expect(desktopSection).toMatch(/\.areaScore.*\.font-vintage.*font-size:\s*12px/s)
    })
  })

  describe('Requirements 4.1, 4.2, 4.3, 4.4: Action button enhancements in desktop only', () => {
    it('should set minimum height of 80px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaAction button.*min-height:\s*80px/s)
    })

    it('should set minimum width of 180px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaAction button.*min-width:\s*180px/s)
    })

    it('should set font size to 32px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaAction button.*font-size:\s*32px/s)
    })

    it('should apply scale(1.03) on hover in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaAction button:hover.*transform:\s*scale\(1\.03\)/s)
    })
  })

  describe('Requirements 5.1, 5.2, 5.3, 5.6: GameSituation layout and typography', () => {
    it('should use horizontal layout (flex-direction: row) in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.gameSituation.*flex-direction:\s*row/s)
    })

    it('should use vertical layout (flex-direction: column) in mobile', () => {
      const mobileSection = extractMobileSection(cssContent)

      // Mobile should explicitly set column layout
      expect(mobileSection).toMatch(/\.gameSituation.*flex-direction:\s*column/s)
    })

    it('should scale count dots to 12px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.countDot.*width:\s*12px/s)
      expect(desktopSection).toMatch(/\.countDot.*height:\s*12px/s)
    })

    it('should scale inning number to 24px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.situationValue.*font-size:\s*24px/s)
    })

    it('should scale count labels to 11px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.countLabel.*font-size:\s*11px/s)
    })
  })

  describe('Requirements 6.1, 6.2, 6.3: Next Batter Preview typography', () => {
    it('should scale batter number to 18px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.nextBatter.*\.font-sports.*font-size:\s*18px/s)
    })

    it('should scale batter name to 14px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.nextBatter.*\.font-vintage.*font-size:\s*14px/s)
    })

    it('should scale stat values to 16px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.nextBatter.*grid-cols-3.*\.font-sports.*font-size:\s*16px/s)
    })
  })

  describe('Requirements 7.1, 7.2, 7.3, 7.4: Tactical Cards dimensions', () => {
    it('should set minimum height of 140px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaCards button.*min-height:\s*140px/s)
    })

    it('should set minimum width of 100px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaCards button.*min-width:\s*100px/s)
    })

    it('should scale card ID text to 14px in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(/\.areaCards button.*\.font-sports.*font-size:\s*14px/s)
    })

    it('should apply scale(1.06) and translateY(-4px) on hover in desktop', () => {
      const desktopSection = extractDesktopSection(cssContent)

      expect(desktopSection).toMatch(
        /\.areaCards button:hover.*transform:\s*scale\(1\.06\) translateY\(-4px\)/s,
      )
    })
  })

  describe('Requirement 8.1, 8.5: Mobile viewport preservation', () => {
    it('should maintain mobile grid layout structure', () => {
      // Check that coreGameplay uses grid layout in the CSS file
      expect(cssContent).toContain('.coreGameplay')
      expect(cssContent).toMatch(/\.coreGameplay\s*\{[^}]*display:\s*grid/)
    })

    it('should NOT have desktop typography enhancements outside media queries', () => {
      const baseStyles = cssContent.split('@media')[0] ?? ''

      // Base styles should not contain desktop-specific typography
      expect(baseStyles).not.toMatch(/\.playerCard.*font-size:\s*clamp\(48px/)
      expect(baseStyles).not.toMatch(/\.areaAction button.*min-height:\s*80px/)
    })
  })

  describe('Mobile background image preservation', () => {
    it('should use mobile background for viewports <=1199px', () => {
      const mobileBgSection = cssContent.match(
        /@media \(max-width: 1199.*?\{[^}]*stadium-mobile\.png[^}]*\}/s,
      )

      expect(mobileBgSection).toBeTruthy()
    })

    it('should use desktop background by default', () => {
      const baseStyles = cssContent.split('@media')[0]

      expect(baseStyles).toMatch(/\.gameBg.*background-image:.*stadium-desktop\.png/s)
    })
  })
})

/**
 * Helper functions to extract specific sections of CSS
 */

function extractDesktopSection(css: string): string {
  // Extract content within @media (min-width: 1200px) { ... }
  const desktopMatch = css.match(/@media \(min-width: 1200px\)\s*\{([\s\S]*?)(?=@media|$)/g)

  if (!desktopMatch) return ''

  return desktopMatch.join('\n')
}

function extractMobileSection(css: string): string {
  // Extract content within mobile/tablet media queries and base styles
  const mobileMatches = css.match(/@media \(max-width: (1199|767|430).*?\)\s*\{[\s\S]*?\n\}/g)
  const baseStyles = css.split('@media')[0] ?? ''

  if (!mobileMatches) return baseStyles

  return baseStyles + '\n' + mobileMatches.join('\n')
}
