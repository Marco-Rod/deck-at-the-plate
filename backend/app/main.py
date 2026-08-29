"""
Deck at the Plate — API Backend
=================================
Punto de entrada de la aplicación FastAPI.

Routers registrados:
    /api/v1/cards    → Catálogo de equipos y cartas de jugadores.
    /api/v1/games    → Creación y consulta de sesiones de juego (con Fog of War).
    /api/v1/games    → Motor de jugabilidad 1v1 (pitch, swing, tácticas, robo, cambio de picher).
    /api/v1/user     → Perfil e inventario de usuario.
    /api/v1/shop     → Tienda: starter pack y apertura de sobres.
    /ws/games        → WebSocket de eventos en tiempo real por partida.

Las tablas se crean automáticamente con Base.metadata.create_all al iniciar
(se recomienda migrar a Alembic para control de versiones del schema — ver TODO #13).
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import engine, Base
from app.routers import cards, games, gameplay, ws, user, shop, auth, teams

# Configurar logging a nivel de aplicación
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Deck at the Plate - API 1v1",
    version="1.0.0",
    description="API Backend para el juego de cartas de béisbol en tiempo real."
)

# Definir los orígenes explícitamente (puerto predeterminado de Vite)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # TODO #12: Restringir a dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea las tablas en la DB si no existen (modo desarrollo)
Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(cards.router)
app.include_router(gameplay.router)
app.include_router(games.router)
app.include_router(ws.router)
app.include_router(user.router)
app.include_router(shop.router)
app.include_router(teams.router)

# Exception handler personalizado para errores de validación
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """
    Convierte errores de validación de Pydantic en respuestas legibles.
    Extrae el primer error y retorna un mensaje amigable al usuario.
    """
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        
        # Obtener información del campo y el tipo de error
        field = first_error.get("loc", [])[-1] if first_error.get("loc") else "unknown"
        error_type = first_error.get("type", "validation_error")
        msg = first_error.get("msg", "Validación fallida")
        
        # Mapear tipos de error a mensajes amigables
        error_messages = {
            "string_too_short": f"El campo '{field}' debe tener al menos 6 caracteres",
            "string_too_long": f"El campo '{field}' excede la longitud máxima permitida",
            "value_error": f"Valor inválido para '{field}'",
        }
        
        user_message = error_messages.get(error_type, msg)
        
        return JSONResponse(
            status_code=422,
            content={
                "detail": user_message,
                "field": field,
                "type": error_type
            }
        )
    
    # Fallback si no hay errores específicos
    return JSONResponse(
        status_code=422,
        content={"detail": "Error de validación en la solicitud"}
    )

@app.get("/")
def read_root():
    return {"status": "ok", "app": "Deck at the Plate API"}
