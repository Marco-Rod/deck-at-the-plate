from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.orm import Session
import asyncio

from app.database import SessionLocal
from app.repositories import get_game_by_id
from app.engine.websocket_manager import manager
from app.engine.fog_of_war import sanitize_state_for_player
from app.auth import authenticate_ws_token

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/games/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(..., description="JWT del usuario que se conecta"),
    user_id: str = Query(None, description="(legado) ignorado — la identidad se valida con el token"),
):
    """
    Punto de conexión WebSocket por partida y usuario.
    Mantiene el canal abierto para notificar eventos en tiempo real.

    Seguridad:
      - La identidad del usuario se deriva del token JWT (query param `token`),
        nunca del path ni de un parámetro manipulable por el cliente.
      - Solo usuarios que pertenecen a la partida pueden conectarse.

    NOTA: Se instancia la sesión de DB manualmente porque Depends(get_db) no
    funciona de forma fiable en handlers WebSocket async de FastAPI — el generador
    síncrono puede no inyectarse correctamente y provoca un error de handshake.
    """
    # Autenticar antes de aceptar la conexión → evita que cualquiera se suscriba
    try:
        user_id = authenticate_ws_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket, game_id, user_id)
    db: Session = SessionLocal()
    try:
        # Enviar estado actual sanitizado al conectar
        game = get_game_by_id(db, game_id)
        if game:
            # Verificar que el usuario autenticado pertenezca a la partida.
            if user_id not in (game.home_user_id, game.away_user_id):
                await websocket.close(code=4403)
                return

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
            
            # ⭐ ARREGLADO: Ejecutar trigger_cpu_response si es necesario
            # En caso de que la CPU deba actuar en el primer turn (ej. usuario es AWAY en TOP)
            print(f"[WS] Verificando si CPU debe actuar al conectar...")
            from app.engine.game_actions import trigger_cpu_response
            state = dict(game.state_data or {})
            print(f"[WS] State before trigger: current_pitch={state.get('current_pitch')}, is_top={game.is_top_inning}, mode={state.get('mode')}")
            try:
                await trigger_cpu_response(game, state, db, game_id)
                print(f"[WS] ✅ trigger_cpu_response completed successfully")
            except Exception as e:
                print(f"[WS] ❌ Error en trigger_cpu_response: {e}")
                import traceback
                traceback.print_exc()
            
            # La CPU pudo actuar sin commitear (Unit of Work del router): persistir
            # antes de recargar desde BD para no perder los cambios en memoria.
            db.commit()
            # Recargar game desde DB para sincronizar
            db.refresh(game)
            print(f"[WS] State after trigger: current_pitch={game.state_data.get('current_pitch') if game.state_data else None}")
            
            # ⭐ Si la CPU lanzó en el inicio, enviar el estado actualizado al cliente
            if game.state_data and game.state_data.get('current_pitch'):
                print(f"[WS] CPU lanzó en el inicio, enviando INIT_GAME_STATE actualizado...")
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
                        "user_role": "HOME" if user_id == game.home_user_id else "AWAY",
                    }
                })
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