"""
Script para marcar los 4 equipos CPU (JAL, CUL, MTY, MXL) con is_cpu=True
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/mark_cpu_teams.py
"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

try:
    from app.database import SessionLocal
    from app.models import Team
except ModuleNotFoundError:
    from database import SessionLocal
    from models import Team


def mark_cpu_teams():
    """Marca los 4 equipos CPU con is_cpu=True"""
    db = SessionLocal()
    try:
        cpu_team_ids = ["JAL", "CUL", "MTY", "MXL"]
        
        # Obtener los equipos CPU
        teams = db.query(Team).filter(Team.id.in_(cpu_team_ids)).all()
        
        if not teams:
            print("❌ No se encontraron los equipos CPU. Verifica que existan: JAL, CUL, MTY, MXL")
            return
        
        # Marcar como is_cpu=True
        for team in teams:
            if not team.is_cpu:
                team.is_cpu = True
                print(f"✓ Marcando {team.id} ({team.name}) como CPU")
            else:
                print(f"✓ {team.id} ({team.name}) ya estaba marcado como CPU")
        
        db.commit()
        print(f"\n✅ {len(teams)} equipos CPU marcados exitosamente")
        
        # Verificar
        cpu_teams = db.query(Team).filter(Team.is_cpu == True).all()
        print(f"\n📊 Total de equipos CPU en la BD: {len(cpu_teams)}")
        for team in cpu_teams:
            print(f"   - {team.id}: {team.name}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    mark_cpu_teams()
