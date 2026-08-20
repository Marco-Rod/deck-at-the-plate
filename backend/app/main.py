from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import cards, games, gameplay, ws

app = FastAPI(
    title="Deck at the Plate - API 1v1",
    version="1.0.0",
    description="API Backend para el juego de cartas de béisbol en tiempo real."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Registrar el router del Módulo 1
app.include_router(cards.router)
# Registrar el router del Modulo 2
app.include_router(games.router)
# Registrar el router del Modulo 2
app.include_router(gameplay.router)
# Registrar router WebSocket
app.include_router(ws.router)

@app.get("/")
def read_root():
    return {"status": "ok", "app": "Deck at the Plate API"}