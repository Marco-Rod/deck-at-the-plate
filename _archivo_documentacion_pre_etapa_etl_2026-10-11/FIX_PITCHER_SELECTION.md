# Fix: Agregar Selector de Pitcher

## 🎯 Problema Descubierto

Al crear una partida, el backend rechazaba con error:
```
Se requiere un lanzador valido para ambos equipos. home=None, away=card_694297
```

**Causa**: El frontend NO estaba enviando `home_pitcher_id` en el payload.

---

## ✅ Cambios Realizados

### 1. `RosterSelectionPage.tsx`
```typescript
// Agregado:
const pitchers = useMemo(
  () => (inventory ?? []).filter((i) => i.card.position === 'SP' || i.card.position === 'RP'),
  [inventory],
)

const [selectedPitcherId, setSelectedPitcherId] = useState<string | null>(null)

// Validación en handleConfirm:
if (!selectedPitcherId) {
  setError('Debes seleccionar un pitcher')
  return
}

// En el payload:
const payload = {
  ...
  home_pitcher_id: selectedPitcherId,  ✅ AGREGADO
  ...
}
```

### 2. UI Nueva
Se agregó una sección **"Pitcher"** antes de "Deck" donde:
- Muestra todos los SP y RP disponibles
- Usuario selecciona uno haciendo clic
- El seleccionado se resalta con borde dorado

---

## 🧪 Próxima Prueba

1. Navega a RosterSelectionPage como antes
2. **NUEVO**: Verás una sección "Pitcher" con tus lanzadores
3. **REQUIERE**: Selecciona un pitcher (haz clic en uno)
4. Alinea 9 bateadores
5. Selecciona tácticas (opcional)
6. **Haz clic en "INICIAR PARTIDA"**

---

## ✅ Éxito Si Ves:

Console:
```
[DEBUG-RosterSelectionPage] PAYLOAD COMPLETO A ENVIAR: {
  "home_pitcher_id": "card_694297",  ✅ PITCHER INCLUÍDO
  "home_lineup": [...],
  ...
}
```

Backend:
```
[DEBUG-Service] HOME: rival_team_id=AZ (from away_user_id), away_user_id=CPU_BOT (CPU)
No hay cartas para equipo CPU_BOT; usando cartas de cualquier equipo.  ← ESTO ES CORRECTO

✅ Partida se crea exitosamente
✅ Te llevas al Stadium
```

---

## ❌ Si Aún Hay Error

Si el pitcher selector NO aparece:
- Recarga la página
- Verifica que estés en `pwa/` (no `frontend.OLD`)

Si el pitcher sigue siendo None:
- El payload tiene `home_pitcher_id` pero podría ser invalido
- Verifica en console que `home_pitcher_id` NO sea null o undefined

