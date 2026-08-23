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

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, UserWallet
from app.auth import create_access_token
from app.schemas.user import RegisterRequest, LoginResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

# Contexto de hashing: bcrypt con manejo automático de versiones obsoletas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    """Retorna el hash bcrypt de la contraseña en texto plano."""
    return pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    return pwd_context.verify(plain, hashed)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario"
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario en el sistema.

    - Valida que el username no esté en uso.
    - Hashea la contraseña con bcrypt antes de persistirla.
    - Crea automáticamente una wallet con 1000 Stamps y 0 Gems iniciales.

    Retorna el user_id y username del usuario creado (sin contraseña ni hash).
    """
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El nombre de usuario '{payload.username}' ya está en uso."
        )

    new_user = User(
        username=payload.username,
        hashed_password=_hash_password(payload.password),
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
    }


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión y obtener JWT"
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Autentica al usuario y retorna un JWT Bearer token.

    Acepta el formato estándar OAuth2 (form-data con campos `username` y `password`),
    lo que permite compatibilidad con el botón "Authorize" en la documentación de FastAPI.

    El token incluye el user_id en el claim "sub" y expira en 8 horas.
    """
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
