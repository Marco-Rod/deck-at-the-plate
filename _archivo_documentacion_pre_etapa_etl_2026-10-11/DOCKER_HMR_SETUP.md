# 🐳 Docker HMR (Hot Module Reload) Setup

## Problema
Después de cambios en archivos TypeScript/React, el contenedor PWA requería reinicio manual para reflejar cambios.

## Solución Implementada
Configuración de **HMR (Hot Module Reload)** de Vite para funcionar correctamente dentro de Docker.

## 📋 Cambios Realizados

### 1. `vite.config.ts` - Configuración de HMR
```typescript
server: {
  host: '0.0.0.0',
  port: 5173,
  hmr: {
    host: process.env.VITE_HMR_HOST || 'localhost',
    port: process.env.VITE_HMR_PORT ? parseInt(process.env.VITE_HMR_PORT) : 5173,
    protocol: 'ws',
  },
},
```

**Explicación:**
- `host: '0.0.0.0'` - Escucha en todas las interfaces dentro del contenedor
- `hmr.host` - Le dice a Vite cómo conectarse desde el navegador (`localhost`)
- `hmr.port` - Puerto WebSocket para HMR
- `protocol: 'ws'` - WebSocket sin SSL (usar `wss` en producción)

### 2. `docker-compose.yml` - Variables de entorno
```yaml
environment:
  - VITE_HMR_HOST=localhost
  - VITE_HMR_PORT=5173
```

**Por qué es necesario:**
- Permite cambiar el host/puerto sin recompilar la imagen Docker
- Útil si expones el contenedor en un puerto diferente

## 🚀 Cómo Usar

### Opción 1: Local (desarrollo normal sin Docker)
```bash
cd pwa
npm run dev
# Vite automáticamente usa HMR en localhost:5173
```

### Opción 2: Con Docker Compose
```bash
docker-compose up -d
# Ahora los cambios en pwa/src/** se reflejan automáticamente
# Sin necesidad de reiniciar el contenedor
```

## ✅ Verificación
1. Abre `http://localhost:5173` en el navegador
2. Modifica un archivo en `pwa/src/**`
3. **Esperado:** La página se recarga automáticamente sin reiniciar el contenedor
4. **Antes:** Era necesario `docker-compose restart pwa`

## 📝 Notas Técnicas

### ¿Cómo funciona HMR en Vite?
1. Vite dev server corre en el contenedor en `0.0.0.0:5173`
2. El navegador se conecta a `localhost:5173` (desde la máquina host)
3. Vite observa cambios de archivos dentro del contenedor
4. Cuando hay cambios, Vite envía una señal WebSocket al navegador
5. El navegador reemplaza módulos sin recargar la página completa

### ¿Qué pasa si cambio `VITE_HMR_HOST`?
- Si expones Docker en otra IP/hostname, cambia `VITE_HMR_HOST` en `docker-compose.yml`
- Ejemplo para desarrollo remoto:
  ```yaml
  environment:
    - VITE_HMR_HOST=192.168.1.100  # Tu IP local
    - VITE_HMR_PORT=5173
  ```

### ¿Por qué no estaba funcionando antes?
- Vite sin configuración explícita de HMR en Docker intenta conectarse a sí mismo
- Dentro del contenedor, "localhost" es solo el contenedor (no el host)
- La configuración ahora le dice explícitamente dónde pueden acceder los clientes

## 🔧 Troubleshooting

**Síntoma:** "WebSocket connection failed"
- **Causa:** VITE_HMR_HOST no coincide con tu URL de acceso
- **Solución:** Verifica el valor en `docker-compose.yml`

**Síntoma:** Cambios no aparecen
- **Causa:** Volumen no montado correctamente
- **Solución:** Verifica `volumes: - ./pwa:/app` en `docker-compose.yml`

**Síntoma:** "Cannot find module" después de cambios
- **Causa:** `node_modules` no está sincronizado
- **Solución:** Ejecuta `docker-compose rebuild pwa`

## 📚 Referencias
- [Vite Server Config](https://vitejs.dev/config/server-options.html)
- [Vite HMR Configuration](https://vitejs.dev/guide/ssr.html#hmr)
- [Docker Best Practices for Node.js](https://nodejs.org/en/docs/guides/nodejs-docker-webapp/)
