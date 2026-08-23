from app.database import engine, Base
from app.models import Team, PlayerCardModel, TacticCard, User, UserWallet, UserCardInventory, GameSession

def reset_db():
    print("Eliminando tablas antiguas...")
    Base.metadata.drop_all(bind=engine)
    print("Creando tablas con el nuevo esquema...")
    Base.metadata.create_all(bind=engine)
    print("¡Base de datos lista!")

if __name__ == "__main__":
    reset_db()