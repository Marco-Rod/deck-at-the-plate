from typing import Dict, List, Tuple, Callable
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # game_id -> Lista de (WebSocket, user_id) activos (Jugador Local y Visitante)
        self.active_connections: Dict[str, List[Tuple[WebSocket, str]]] = {}

    async def connect(self, websocket: WebSocket, game_id: str, user_id: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        self.active_connections[game_id].append((websocket, user_id))

    def disconnect(self, websocket: WebSocket, game_id: str):
        if game_id in self.active_connections:
            self.active_connections[game_id] = [
                (ws, uid) for ws, uid in self.active_connections[game_id] if ws is not websocket
            ]
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def broadcast_to_game(self, game_id: str, message: dict):
        """Envia un evento en JSON a todos los jugadores conectados a la sala del partido."""
        for connection, _ in self.active_connections.get(game_id, []):
            await connection.send_json(message)

    async def broadcast_to_game_view(self, game_id: str, build_message: Callable[[str], dict | None]):
        """
        Envía un evento en JSON PERO calculando un payload distinto por destinatario.
        ``build_message(user_id)`` recibe el user_id de cada cliente conectado y
        retorna el dict que se le enviará (o ``None`` para omitirlo).

        Es el canal correcto para mensajes que incluyen ``state_data`` sujeto a
        Fog of War: permite sanitizar la información por jugador.
        """
        for connection, user_id in self.active_connections.get(game_id, []):
            payload = build_message(user_id)
            if payload is not None:
                await connection.send_json(payload)

# Instancia global para ser utilizada en los routers
manager = ConnectionManager()