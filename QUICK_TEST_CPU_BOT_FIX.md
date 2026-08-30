# Quick Test: Verificar Fix de CPU_BOT

## ⚡ Resumen de 30 Segundos

**Problema:** Backend recibe `CPU_BOT` en lugar del equipo seleccionado

**Causa:** Frontend antiguo (`frontend/`) interfería. Ya eliminado.

**Fix:** PWA ahora usa `config.rivalId` del Zustand store

**Estado:** Listo para probar

---

## 🧪 Prueba Rápida (5 minutos)

```bash
# 1. Asegurar que PWA está corriendo
cd pwa
npm run dev
# → http://localhost:5173

# 2. En otra terminal, backend también corriendo
cd backend
python -m uvicorn app.main:app --reload
# → http://localhost:8000
```

---

## 📱 Pasos en la UI

1. **Lobby**
   - Selecciona un rival (carrusel abajo)
   - Ejemplo: Cincinnati Reds (id: "CIN")

2. **RosterSelectionPage**
   - Alinea 9 bateadores
   - Haz clic en "INICIAR PARTIDA"

3. **Observa en Console (F12)**
   ```
   [DEBUG-RosterSelectionPage] MONTADA CON CONFIG: {
     rivalId: "CIN",  ← ¿VE ESTO? ✓
     ...
   }
   ```

4. **Observa en Backend Terminal**
   ```
   [DEBUG-Router] away_user_id details: value='CIN', is_empty=False
                                                        ↑ ¿"CIN"? ✓
   ```

---

## ✅ Éxito = Ves Esto

**Console:**
```
rivalId: "CIN"
away_user_id: "CIN"
```

**Backend:**
```
away_user_id=CIN
rival_team_id=CIN
```

**Resultado:** Partida con Cincinnati Reds ✓

---

## ❌ Falla = Ves Esto

**Console:**
```
rivalId: ""  ← VACÍO
away_user_id: undefined
```

**Backend:**
```
away_user_id=CPU_BOT
rival_team_id=CPU_BOT
```

**Resultado:** Error "No hay cartas para equipo CPU_BOT" ✗

---

## 📋 Reportar Si Falla

Comparte:
1. Los logs exactos que ves en console
2. Lo que recibe el backend
3. Si `rivalId` está vacío o tiene valor
4. El URL exacto donde estás (`localhost:5173`, etc.)

