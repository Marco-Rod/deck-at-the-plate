"""
Router: Autenticación
======================
Endpoints para registro e inicio de sesión de usuarios.

  POST /api/v1/auth/register  → Crea un nuevo usuario con contraseña hasheada y wallet inicial.
  POST /api/v1/auth/login     → Verifica credenciales y retorna un JWT Bearer token.

El token JWT tiene una vigencia de 8 horas y contiene el user_id en el claim "sub".
Para rutas protegidas, incluir el header:
    Authorization: Bearer <token>

Seguridad:
    - Las contraseñas se hashean con bcrypt a través de passlib.
    - El SECRET_KEY se lee de la variable de entorno JWT_SECRET_KEY.
    - Nunca se retorna el hash de la contraseña en ninguna respuesta.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import bcrypt
import time
import threading

from app.database import get_db
from app.models import User, UserWallet
from app.auth import create_access_token
from app.schemas.user import RegisterRequest, LoginResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

# Contexto de hashing: bcrypt con manejo automático de versiones obsoletas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    """Retorna el hash bcrypt truncando la entrada a 72 bytes."""
    # Convertir a bytes y truncar explícitamente a 72 bytes
    pwd_bytes = plain.encode('utf-8')[:72]
    # Generar salt y hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def _verify_password(plain: str, hashed: str) -> bool:
    """Verifica si la contraseña coincide con el hash en BD."""
    pwd_bytes = plain.encode('utf-8')[:72]
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


# ---------------------------------------------------------------------------
# Rate limiting simple en memoria (aplica a /login y /register).
# Limita intentos por IP para mitigar fuerza bruta y enumeración de cuentas.
# Nota: en un despliegue multi-instancia se debe sustituir por un store
# distribuido (Redis) o un reverse proxy (nginx limit_req).
# ---------------------------------------------------------------------------

_login_limits: dict = {}       # ip -> lista de timestamps
_login_lock = threading.Lock()

# Máximo de solicitudes por ventana de tiempo (p. ej. 10 por 5 minutos)
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW_SECONDS = 300


def _client_ip(request: Request) -> str:
    # Confiar en el header X-Forwarded-For solo si está presente y es válido.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_login_rate_limit(request: Request) -> None:
    """Comprueba el límite de intentos por IP; lanza 429 si se excede."""
    ip = _client_ip(request)
    now = time.time()

    with _login_lock:
        window = _login_limits.setdefault(ip, [])
        # Descartar timestamps fuera de la ventana
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        window[:] = [ts for ts in window if ts > cutoff]

        if len(window) >= RATE_LIMIT_MAX:
            # Limpiar IPs con listas vacías para evitar crecimiento sin límite
            if not window:
                _login_limits.pop(ip, None)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
            )

        window.append(now)

        # Poda defensiva: evitar que el dict crezca indefinidamente.
        if len(_login_limits) > 10000:
            stale_cutoff = now - RATE_LIMIT_WINDOW_SECONDS
            for key, ts_list in list(_login_limits.items()):
                pruned = [ts for ts in ts_list if ts > stale_cutoff]
                if pruned:
                    _login_limits[key] = pruned
                else:
                    _login_limits.pop(key, None)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario"
)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario en el sistema.

    - Valida que el username no esté en uso.
    - Hashea la contraseña con bcrypt antes de persistirla.
    - Crea automáticamente una wallet con 1000 Stamps y 0 Gems iniciales.

    Retorna el user_id y username del usuario creado (sin contraseña ni hash).
    """
    enforce_login_rate_limit(request)

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El nombre de usuario '{payload.username}' ya está en uso."
        )

    new_user = User(
        username=payload.username,
        hashed_password=_hash_password(payload.password),
        has_completed_onboarding=False
    )
    db.add(new_user)
    db.flush()  # Genera el ID sin hacer commit, para poder crear la wallet en la misma transacción

    # Crear wallet inicial con Stamps de bienvenida
    wallet = UserWallet(user_id=new_user.id, stamps=1000, gems=0)
    db.add(wallet)
    db.commit()
    db.refresh(new_user)

    return {
        "status": "created",
        "user_id": new_user.id,
        "username": new_user.username,
        "has_completed_onboarding": False
    }


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión y obtener JWT"
)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Autentica al usuario y retorna un JWT Bearer token.

    Acepta el formato estándar OAuth2 (form-data con campos `username` y `password`),
    lo que permite compatibilidad con el botón "Authorize" en la documentación de FastAPI.

    El token incluye el user_id en el claim "sub" y expira en 8 horas.
    """
    enforce_login_rate_limit(request)

    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not _verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user.id})

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )
