"""
Script directo para actualizar equipos CPU a is_cpu=True
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/update_cpu_teams_direct.py
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


def update_cpu_teams():
    """Actualiza los 4 equipos CPU (JAL, CUL, MTY, MXL) a is_cpu=True"""
    db = SessionLocal()
    try:
        cpu_team_ids = ["JAL", "CUL", "MTY", "MXL"]
        
        print("🔄 Actualizando equipos CPU...")
        
        # Actualizar todos los equipos CPU de una vez
        updated_count = 0
        for team_id in cpu_team_ids:
            team = db.query(Team).filter(Team.id == team_id).first()
            if team:
                if not team.is_cpu:
                    team.is_cpu = True
                    updated_count += 1
                    print(f"   ✓ {team.id}: {team.name} → is_cpu=True")
                else:
                    print(f"   ✓ {team.id}: {team.name} (ya estaba marcado)")
            else:
                print(f"   ❌ {team.id}: NO EXISTE")
        
        db.commit()
        
        if updated_count > 0:
            print(f"\n✅ {updated_count} equipos actualizados exitosamente")
        else:
            print(f"\n✓ Todos los equipos ya estaban marcados")
        
        # Verificar
        cpu_teams = db.query(Team).filter(Team.is_cpu == True).all()
        print(f"\n📊 Total de equipos CPU en la BD: {len(cpu_teams)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    update_cpu_teams()
