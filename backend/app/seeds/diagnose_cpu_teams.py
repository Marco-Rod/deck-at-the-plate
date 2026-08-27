"""
Script de diagnóstico para revisar el estado de los equipos CPU
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/diagnose_cpu_teams.py
"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

try:
    from app.database import SessionLocal
    from app.models import Team, PlayerCardModel
except ModuleNotFoundError:
    from database import SessionLocal
    from models import Team, PlayerCardModel


def diagnose():
    """Diagnóstico del estado de equipos CPU"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("DIAGNÓSTICO DE EQUIPOS CPU")
        print("=" * 60)
        
        # 1. Verificar si la columna is_cpu existe
        all_teams = db.query(Team).all()
        if not all_teams:
            print("❌ No hay equipos en la BD")
            return
        
        first_team = all_teams[0]
        try:
            _ = first_team.is_cpu
            print("✅ Columna is_cpu existe en la tabla teams")
        except AttributeError:
            print("❌ Columna is_cpu NO existe en la tabla teams")
            print("   Ejecuta: python app/seeds/add_is_cpu_column.py")
            return
        
        # 2. Contar equipos totales
        total_teams = len(all_teams)
        print(f"\n📊 Total de equipos en BD: {total_teams}")
        
        # 3. Contar equipos CPU
        cpu_teams = db.query(Team).filter(Team.is_cpu == True).all()
        print(f"🤖 Equipos CPU (is_cpu=True): {len(cpu_teams)}")
        if cpu_teams:
            for team in cpu_teams:
                cards_count = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).count()
                print(f"   - {team.id}: {team.name} ({cards_count} cartas)")
        
        # 4. Verificar si JAL, CUL, MTY, MXL existen
        print("\n🔍 Buscando equipos CPU esperados:")
        cpu_expected = ["JAL", "CUL", "MTY", "MXL"]
        for team_id in cpu_expected:
            team = db.query(Team).filter(Team.id == team_id).first()
            if team:
                is_cpu_flag = "✅ is_cpu=True" if team.is_cpu else "❌ is_cpu=False"
                cards_count = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).count()
                print(f"   {team_id}: {team.name} {is_cpu_flag} ({cards_count} cartas)")
            else:
                print(f"   {team_id}: ❌ NO EXISTE")
        
        # 5. Verificar endpoint /cpu
        print("\n🔗 Simulando endpoint GET /api/v1/teams/cpu:")
        cpu_response = db.query(Team).filter(Team.is_cpu == True).all()
        if cpu_response:
            print(f"   Retornaría {len(cpu_response)} equipos")
        else:
            print("   ❌ Retornaría 0 equipos (array vacío)")
        
        # 6. Verificar equipos MLB (30)
        mlb_teams = db.query(Team).filter(Team.is_cpu == False).all()
        print(f"\n🏟️  Equipos MLB (is_cpu=False): {len(mlb_teams)}")
        if len(mlb_teams) > 0 and len(mlb_teams) <= 10:
            for team in mlb_teams[:10]:
                print(f"   - {team.id}: {team.name}")
        elif len(mlb_teams) > 10:
            print(f"   (Primeros 5 de {len(mlb_teams)})")
            for team in mlb_teams[:5]:
                print(f"   - {team.id}: {team.name}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diagnose()
