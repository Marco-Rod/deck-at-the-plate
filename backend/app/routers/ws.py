from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GameSession
from app.engine.websocket_manager import manager
from app.engine.fog_of_war import sanitize_state_for_player

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/games/{game_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, user_id: str, db: Session = Depends(get_db)):
    """
    Punto de conexión WebSocket por partida y usuario. 
    Mantiene el canal abierto para notificar eventos en tiempo real.
    """
    await manager.connect(websocket, game_id)
    try:
        # Enviar estado actual sanitizado al conectar
        game = db.query(GameSession).filter(GameSession.id == game_id).first()
        if game:
            sanitized_state = sanitize_state_for_player(
                state_data=game.state_data,
                requesting_user_id=user_id,
                home_user_id=game.home_user_id,
                away_user_id=game.away_user_id,
                is_top_inning=game.is_top_inning
            )
            await websocket.send_json({
                "type": "INIT_GAME_STATE",
                "game_id": game_id,
                "outs": game.outs,
                "balls": game.balls,
                "strikes": game.strikes,
                "score_home": game.score_home,
                "score_away": game.score_away,
                "current_inning": game.current_inning,
                "is_top_inning": game.is_top_inning,
                "state_data": sanitized_state
            })

        while True:
            # Mantener conexión viva recibiendo pings del cliente
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)