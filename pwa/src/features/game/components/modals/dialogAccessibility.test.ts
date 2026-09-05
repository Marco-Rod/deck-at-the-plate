import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8')

describe('game dialog accessibility', () => {
  it.each([
    'ChangePitcherModal.tsx',
    'GameIntroModal.tsx',
    'GameOverModal.tsx',
    'InningTransitionModal.tsx',
    'QuitGameModal.tsx',
    'RivalPitcherChangeModal.tsx',
  ])('%s declara semántica modal y usa control de foco', (file) => {
    const contents = source(`src/features/game/components/modals/${file}`)
    expect(contents).toMatch(/role="(?:dialog|alertdialog)"/)
    expect(contents).toContain('aria-modal="true"')
    expect(contents).toMatch(/aria-(?:label|labelledby)=/)
    expect(contents).toContain('useDialogFocus')
  })

  it('el selector de lanzamiento se comporta como diálogo', () => {
    const contents = source('src/features/game/components/pitch/PitchZoneGrid.tsx')
    expect(contents).toContain('role="dialog"')
    expect(contents).toContain('aria-modal="true"')
    expect(contents).toContain('aria-labelledby="pitch-selection-title"')
    expect(contents).toContain('useDialogFocus')
  })
})
