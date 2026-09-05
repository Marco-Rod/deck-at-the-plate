import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const html = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')

describe('font loading', () => {
  it('carga la hoja de fuentes sin bloquear el primer render', () => {
    expect(html).toMatch(/rel="preload"\s+as="style"/)
    expect(html).toContain("onload=\"this.onload=null;this.rel='stylesheet'\"")
    expect(html).toMatch(/<noscript>[\s\S]*fonts\.googleapis\.com[\s\S]*<\/noscript>/)
  })

  it('usa font-display swap y no solicita la variante itálica sin uso', () => {
    expect(html).toContain('display=swap')
    expect(html).not.toContain('Courier+Prime:ital')
    expect(html).toContain('Courier+Prime:wght@400;700')
    expect(html).toContain('Inter:wght@400;600;700')
    expect(html).toContain('Teko:wght@600;700')
  })
})
