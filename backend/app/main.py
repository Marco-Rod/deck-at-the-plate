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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import cards, games, gameplay, ws, user, shop, auth

app = FastAPI(
    title="Deck at the Plate - API 1v1",
    version="1.0.0",
    description="API Backend para el juego de cartas de béisbol en tiempo real."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO #12: Restringir a dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea las tablas en la DB si no existen (modo desarrollo)
Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(cards.router)
app.include_router(games.router)
app.include_router(gameplay.router)
app.include_router(ws.router)
app.include_router(user.router)
app.include_router(shop.router)


@app.get("/")
def read_root():
    return {"status": "ok", "app": "Deck at the Plate API"}
