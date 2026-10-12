# 🔍 Diagnóstico y Corrección de Equipos CPU

## El Problema
Solo aparece 1 equipo CPU (default) en el carrusel en lugar de 4 (JAL, CUL, MTY, MXL).

## Causa Encontrada
Los equipos CPU existen pero **NO tienen `is_cpu=True`** en la BD. El diagnóstico mostró:
```
🤖 Equipos CPU (is_cpu=True): 0
   JAL: Charros ❌ is_cpu=False
   CUL: Tomateros ❌ is_cpu=False
   MTY: Sultanes ❌ is_cpu=False
   MXL: Águilas ❌ is_cpu=False
```

---

## ✅ Solución (Elige UNA de estas opciones)

### Opción A: Script Actualizado (RECOMENDADO)
```bash
docker compose exec baseball_backend python app/seeds/seed_cpu_teams.py
```

Ahora incluye lógica para **actualizar equipos existentes** además de crear nuevos.

### Opción B: Script Directo
```bash
docker compose exec baseball_backend python app/seeds/update_cpu_teams_direct.py
```

Script específico para solo marcar los 4 equipos CPU.

### Opción C: Script de Marcado
```bash
docker compose exec baseball_backend python app/seeds/mark_cpu_teams.py
```

Script anterior que hace lo mismo que la Opción B.

---

## 🚀 Pasos Finales

1. Ejecuta UNA de las opciones arriba (recomendado: Opción A)
2. Reinicia el backend:
   ```bash
   docker compose restart baseball_backend
   ```
3. Verifica con el diagnóstico:
   ```bash
   docker compose exec baseball_backend python app/seeds/diagnose_cpu_teams.py
   ```

Debería mostrar:
```
🤖 Equipos CPU (is_cpu=True): 4
   - JAL: Charros (14 cartas)
   - CUL: Tomateros (14 cartas)
   - MTY: Sultanes (12 cartas)
   - MXL: Águilas (12 cartas)
```

---

## 📋 Scripts Disponibles

| Script | Propósito |
|--------|-----------|
| `diagnose_cpu_teams.py` | Revisar estado actual |
| `seed_cpu_teams.py` | Crear/actualizar equipos CPU (NUEVO) |
| `update_cpu_teams_direct.py` | Solo marcar existentes |
| `mark_cpu_teams.py` | Marcar existentes (antiguo) |
| `add_is_cpu_column.py` | Agregar columna (ya ejecutado) |



