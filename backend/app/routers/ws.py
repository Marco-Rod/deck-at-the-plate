from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio

from app.database import SessionLocal
from app.models import GameSession
from app.engine.websocket_manager import manager
from app.engine.fog_of_war import sanitize_state_for_player

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/games/{game_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, user_id: str):
    """
    Punto de conexión WebSocket por partida y usuario. 
    Mantiene el canal abierto para notificar eventos en tiempo real.

    NOTA: Se instancia la sesión de DB manualmente porque Depends(get_db) no
    funciona de forma fiable en handlers WebSocket async de FastAPI — el generador
    síncrono puede no inyectarse correctamente y provoca un error de handshake.
    """
    await manager.connect(websocket, game_id)
    db: Session = SessionLocal()
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
                "state_data": {
                    **sanitized_state,
                    "user_role": "HOME" if user_id == game.home_user_id else "AWAY",  # ⭐ NUEVO
                }
            })
            print(f"[WS] Conexión establecida: game={game_id}, user={user_id}")
            
            # ⭐ ARREGLADO: Ejecutar trigger_cpu_response_if_needed si es necesario
            # En caso de que la CPU deba actuar en el primer turn (ej. usuario es AWAY en TOP)
            print(f"[WS] Verificando si CPU debe actuar al conectar...")
            from app.routers.gameplay import trigger_cpu_response_if_needed
            state = dict(game.state_data or {})
            await trigger_cpu_response_if_needed(game, state, db, game_id)
        else:
            await websocket.send_json({
                "type": "ERROR",
                "message": f"Partida '{game_id}' no encontrada."
            })
            print(f"[WS ERROR] Partida no encontrada: {game_id}")
            return

        # ⭐ ARREGLADO: En lugar de bloquearse esperando receive_text(),
        # mantener la conexión viva sin bloquear otros eventos
        while True:
            try:
                # Esperar messages con timeout para permitir que se procesen otros eventos
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                print(f"[WS] Mensaje del cliente {user_id}: {data}")
            except asyncio.TimeoutError:
                # Timeout es normal, simplemente mantenemos la conexión viva
                continue
            except WebSocketDisconnect:
                print(f"[WS] Desconexión: game={game_id}, user={user_id}")
                manager.disconnect(websocket, game_id)
                break
            except Exception as e:
                print(f"[WS ERROR] Recibiendo mensaje: {e}")
                manager.disconnect(websocket, game_id)
                break

    except Exception as e:
        # Capturar errores inesperados para que no cierren silenciosamente la conexión
        print(f"[WS ERROR] game={game_id} user={user_id}: {e}")
        manager.disconnect(websocket, game_id)
    finally:
        db.close()