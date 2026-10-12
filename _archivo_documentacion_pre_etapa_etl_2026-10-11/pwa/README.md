# Deck at the Plate — PWA

Nueva PWA del juego (React 19 + TypeScript estricto + Vite + Tailwind v4).
El backend no se toca; se migra por fases desde `frontend/` (legado). Ver
`../PWA_ANALYSIS.md` para el análisis, reglas de código y checklist de fases.

## Scripts

| Comando             | Uso                                       |
| ------------------- | ----------------------------------------- |
| `npm run dev`       | Dev server en http://localhost:5173       |
| `npm run build`     | Typecheck + build de producción (`dist/`) |
| `npm run typecheck` | `tsc -b`                                  |
| `npm run lint`      | oxlint                                    |
| `npm run test`      | Vitest (unit)                             |
| `npm run format`    | Prettier write                            |
| `npm run preview`   | Servir `dist/` localmente                 |

## Estructura

```
src/
├── app/          # Router, providers
├── features/     # auth, lobby, team, game, cards, shop (store, api, pages)
├── shared/       # api, ui (design system), hooks, lib (i18n, audio)
├── offline/      # service worker, IndexedDB, sync (Fase 4)
└── test/         # setup de testing
```

## Configuración

- API base: `VITE_API_URL` (ver `../.env.example`; default en el cliente).
- Ruta del WebSocket: `VITE_WS_URL`.
