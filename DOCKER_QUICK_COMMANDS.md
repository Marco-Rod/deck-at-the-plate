# 🐳 Docker Quick Commands

## 🎯 TL;DR - El único comando que necesitas

```bash
docker exec -it baseball_backend python reset_without_prompt.py
```

**Eso es todo.** Espera a que termine (1-2 minutos) y listo.

---

## 📋 Comandos Útiles

### Verificar que Docker está corriendo
```bash
docker ps
```
Output esperado:
```
CONTAINER ID   IMAGE            COMMAND                  NAMES
abc123         baseball_backend  uvicorn app.main...     baseball_backend
def456         baseball_frontend docker-entrypoint...    baseball_frontend
ghi789         postgres:15       postgres               baseball_db
```

### Ver logs en tiempo real
```bash
docker logs baseball_backend -f
```
Presiona `Ctrl+C` para salir.

### Ver últimas 50 líneas de logs
```bash
docker logs baseball_backend --tail 50
```

### Reiniciar contenedor backend
```bash
docker restart baseball_backend
```

### Detener todo
```bash
docker-compose down
```

### Iniciar todo de nuevo
```bash
docker-compose up -d
```

### Ejecutar comando interactivo (bash)
```bash
docker exec -it baseball_backend bash
# Luego dentro del contenedor:
# python reset_without_prompt.py
# exit
```

### Ver estado actual de servicios
```bash
docker-compose ps
```

### Limpiar volúmenes (⚠️ borra BD completamente)
```bash
docker-compose down -v
docker-compose up -d
```

---

## 🔄 Workflows Comunes

### Workflow 1: Reset Completo (Lo Recomendado)
```bash
docker exec -it baseball_backend python reset_without_prompt.py
```
✅ Limpia usuarios + equipos + recarga cartas con fixes

### Workflow 2: Solo Limpiar Usuarios (sin cargas)
```bash
docker exec -it baseball_backend python app/seeds/clean_db.py
```
Cuando pida confirmación, escribe: `s` + Enter

### Workflow 3: Solo Recargar Cartas
```bash
docker exec -it baseball_backend python app/seeds/seed_mlb_2026.py
```

### Workflow 4: Ver Progreso en Vivo
```bash
# Terminal 1: Ver logs
docker logs baseball_backend -f

# Terminal 2: Ejecutar reset
docker exec -it baseball_backend python reset_without_prompt.py
```

### Workflow 5: Troubleshoot - Restart y Reset
```bash
docker restart baseball_backend
docker exec -it baseball_backend python reset_without_prompt.py
```

---

## 🎮 Testing Flow Completo

```bash
# 1. Reset (en tu terminal local)
docker exec -it baseball_backend python reset_without_prompt.py
# Espera a que muestre: ✅ COMPLETADO

# 2. Abre browser
http://localhost:5173

# 3. Crea usuario (cualquier info)

# 4. Selecciona equipo (NO LAD - ej: SF, NYY)

# 5. Abre sobre

# 6. Verifica logs (en otra terminal)
docker logs baseball_backend | tail -50
# Busca: "SILVER: 2" "BRONZE: 4" "COMMON: 7"
```

---

## 📊 Status Checks

### ¿Docker está corriendo?
```bash
docker ps | grep baseball
```
Si no muestra nada, hace falta iniciar: `docker-compose up -d`

### ¿BD está lista?
```bash
docker exec baseball_db pg_isready -U game_user
```
Output: `accepting connections` = ✅

### ¿Backend está respondiendo?
```bash
curl http://localhost:8000/docs
```
Debería devolver HTML (Swagger docs)

### ¿Frontend está sirviendo?
```bash
curl http://localhost:5173
```
Debería devolver HTML

---

## ⏱️ Tiempos Esperados

| Operación | Tiempo |
|-----------|--------|
| Limpiar BD | < 1 segundo |
| Seed MLB 2026 | 1-2 minutos (1ª vez) |
| Seed MLB 2026 | 30-60 seg (siguientes) |
| Reset completo | 2-3 minutos |

---

## ✅ Checklist Post-Reset

- [ ] `docker exec ... reset_without_prompt.py` terminó sin errores
- [ ] Veo "✅ COMPLETADO - Base de datos lista"
- [ ] Crear usuario nuevo en browser funciona
- [ ] Seleccionar equipo (no LAD) funciona
- [ ] Abrir sobre funciona
- [ ] Logs muestran "SILVER: 2" "BRONZE: 4" "COMMON: 7"

---

## 🆘 Si Algo Falla

```bash
# Reset y reboot
docker-compose restart backend
docker exec -it baseball_backend python reset_without_prompt.py

# Si sigue fallando
docker-compose down
docker-compose up -d
docker exec -it baseball_backend python reset_without_prompt.py

# Nuclear option (borra todo)
docker-compose down -v
docker-compose up -d
docker exec -it baseball_backend python reset_without_prompt.py
```

---

## 📞 Common Issues

### "Cannot connect to Docker daemon"
```bash
# Docker no está corriendo
# Windows/Mac: Abre Docker Desktop
# Linux: sudo systemctl start docker
```

### "No such container: baseball_backend"
```bash
# El contenedor no existe
docker-compose up -d
```

### "Timed out waiting for response"
```bash
# Contenedor no está listo. Espera y reintenta:
docker-compose up -d
sleep 5
docker exec -it baseball_backend python reset_without_prompt.py
```

### "database connection refused"
```bash
# BD no está lista. Reinicia:
docker-compose restart db
sleep 3
docker exec -it baseball_backend python reset_without_prompt.py
```

---

## 💾 Archivos Importantes

- `docker-compose.yml` - Configuración de servicios
- `backend/reset_without_prompt.py` - Script de reset (lo que ejecutamos)
- `backend/run_complete_reset.py` - Script con confirmación interactiva
- `DOCKER_RESET_INSTRUCTIONS.md` - Instrucciones detalladas

