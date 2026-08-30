"""
Seed Script: Poblar BD con datos reales de MLB 2026
=====================================================

Fuente: statsapi.mlb.com (API oficial de MLB, sin API key requerida)
Descripción:
  - Obtiene los 30 equipos de MLB
  - Asigna nombres ficticios (que no causen conflictos de marca)
  - Obtiene rosters de 40 jugadores por equipo
  - Calcula stats realistas para 25 de Marzo de 2026
  - Genera atributos de juego (velocidad, control, poder, contacto, etc.)

Ejecución en Docker:
  docker compose exec baseball_backend python -m app.seeds.seed_mlb_2026

Ejecución local:
  python app/seeds/seed_mlb_2026.py
"""

import sys
import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

# Solución al ModuleNotFoundError
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

from sqlalchemy.orm import Session

try:
    from app.database import SessionLocal
    from app.models import PlayerCardModel, Team
    from app.core.enums import PITCHER_POSITIONS, Position
except ModuleNotFoundError:
    from database import SessionLocal
    from models import PlayerCardModel, Team
    from core.enums import PITCHER_POSITIONS, Position


# Mapeo de equipos reales a nombres ficticios
TEAM_FICTIONS = {
    "NYY": ("NYY", "Titanes de Nueva York", "New York", "#0C2C56", "NYY"),
    "BOS": ("BOS", "Piratas de Boston", "Boston", "#BD3039", "BOS"),
    "TB": ("TB", "Tormentas de Tampa", "Tampa Bay", "#092C5E", "TB"),
    "BAL": ("BAL", "Águilas de Baltimore", "Baltimore", "#DF4601", "BAL"),
    "TOR": ("TOR", "Azulejos de Toronto", "Toronto", "#134687", "TOR"),
    "LAY": ("LAY", "Ángeles de Los Ángeles", "Los Angeles", "#BA0021", "LAA"),
    "SEA": ("SEA", "Marineros de Seattle", "Seattle", "#0C2C56", "SEA"),
    "OAK": ("OAK", "Forajidos de Oakland", "Oakland", "#003831", "OAK"),
    "TEX": ("TEX", "Rangers de Texas", "Texas", "#003278", "TEX"),
    "HOU": ("HOU", "Astros de Houston", "Houston", "#EB6E1F", "HOU"),
    "KC": ("KC", "Realeza de Kansas City", "Kansas City", "#12284B", "KC"),
    "MIN": ("MIN", "Gemelos de Minnesota", "Minnesota", "#002B5C", "MIN"),
    "DET": ("DET", "Tigres de Detroit", "Detroit", "#0C2C56", "DET"),
    "CWS": ("CWS", "Calcetines Blancos de Chicago", "Chicago", "#27251F", "CWS"),
    "NYM": ("NYM", "Meteoros de Nueva York", "New York", "#002D72", "NYM"),
    "ATL": ("ATL", "Bravos de Atlanta", "Atlanta", "#002B5C", "ATL"),
    "WSH": ("WSH", "Nacionalistas de Washington", "Washington", "#AB0003", "WSH"),
    "PHI": ("PHI", "Filis de Filadelfia", "Philadelphia", "#CE1141", "PHI"),
    "MIA": ("MIA", "Marlinos de Miami", "Miami", "#00A3E0", "MIA"),
    "NYN": ("NYN", "Mets de Nueva York", "New York", "#002D72", "NYN"),
    "CHC": ("CHC", "Cachorros de Chicago", "Chicago", "#0E3386", "CHC"),
    "MIL": ("MIL", "Cerveceros de Milwaukee", "Milwaukee", "#12284B", "MIL"),
    "STL": ("STL", "Cardenales de St. Louis", "St. Louis", "#C41E3A", "STL"),
    "PIT": ("PIT", "Piratas de Pittsburgh", "Pittsburgh", "#27251F", "PIT"),
    "CIN": ("CIN", "Rojos de Cincinnati", "Cincinnati", "#C6011F", "CIN"),
    "LAD": ("LAD", "Dodgers de Los Ángeles", "Los Angeles", "#005A9C", "LAD"),
    "SD": ("SD", "Padres de San Diego", "San Diego", "#2F241D", "SD"),
    "SF": ("SF", "Gigantes de San Francisco", "San Francisco", "#FD5000", "SF"),
    "COL": ("COL", "Montañeses de Colorado", "Colorado", "#33006F", "COL"),
    "ARI": ("ARI", "Diamantesde Arizona", "Arizona", "#A71930", "ARI"),
}


class MLBSeedHelper:
    """Helper para poblar datos de MLB 2026"""

    BASE_URL = "https://statsapi.mlb.com/api/v1"
    SEASON = 2026

    @staticmethod
    def get_all_teams() -> List[Dict[str, Any]]:
        """Obtiene lista de los 30 equipos de MLB"""
        try:
            url = f"{MLBSeedHelper.BASE_URL}/teams"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            teams = [t for t in data.get("teams", []) if t.get("active") and t.get("sport", {}).get("name") == "Major League Baseball"]
            return teams[:30]  # Limitado a 30 equipos
        except Exception as e:
            print(f"Error al obtener equipos: {e}")
            return []

    @staticmethod
    def get_team_roster(team_id: int) -> List[Dict[str, Any]]:
        """Obtiene el roster de 40 hombres de un equipo"""
        try:
            url = f"{MLBSeedHelper.BASE_URL}/teams/{team_id}/roster"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            roster = data.get("roster", [])
            # Aceptar todos los jugadores disponibles (sin filtro de status)
            # Limitar a 40 jugadores
            return roster[:40]
        except Exception as e:
            print(f"Error al obtener roster de equipo {team_id}: {e}")
            return []

    @staticmethod
    def get_player_stats(player_id: int, season: int = 2026) -> Dict[str, Any]:
        """Obtiene las stats de un jugador para la temporada"""
        try:
            url = f"{MLBSeedHelper.BASE_URL}/people/{player_id}"
            params = {"hydrate": "stats(type=season,season={})".format(season)}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error al obtener stats del jugador {player_id}: {e}")
            return {}

    @staticmethod
    def calculate_batting_attributes(player_data: Dict[str, Any]) -> Dict[str, int]:
        """Calcula atributos de bateo basados en stats reales"""
        stats = player_data.get("stats", [])
        
        # Valores por defecto realistas
        contact = 70
        power = 70

        for stat_group in stats:
            if stat_group.get("type", {}).get("displayName") == "season":
                batting = stat_group.get("stats", {}).get("batting", {})
                if batting:
                    avg = float(batting.get("avg", 0.250)) * 100  # AVG 0.250 = 25.0
                    contact = min(99, max(40, int(avg + 20)))  # 45-99 range
                    
                    hr = int(batting.get("homeRuns", 0))
                    rbi = int(batting.get("rbi", 0))
                    power = min(99, max(40, int(((hr + rbi) / 2) * 0.8)))  # 40-99 range
                break

        return {"contact": contact, "power": power}

    @staticmethod
    def calculate_pitching_attributes(player_data: Dict[str, Any]) -> Dict[str, int]:
        """Calcula atributos de pitcheo basados en stats reales"""
        stats = player_data.get("stats", [])
        
        # Valores por defecto realistas
        velocity = 92
        control = 70
        movement = 75

        for stat_group in stats:
            if stat_group.get("type", {}).get("displayName") == "season":
                pitching = stat_group.get("stats", {}).get("pitching", {})
                if pitching:
                    era = float(pitching.get("era", 4.00))
                    # ERA bajo = mejor control (3.0 ERA = 85, 5.0 ERA = 60)
                    control = min(99, max(40, int(110 - (era * 10))))
                    
                    whip = float(pitching.get("whip", 1.20))
                    # WHIP bajo = movimiento (1.1 WHIP = 85, 1.4 WHIP = 65)
                    movement = min(99, max(40, int(130 - (whip * 50))))
                    
                    # ⭐ NUEVO: Obtener velocidad real promedio del pitcher
                    # Si está disponible, sino usar defecto
                    avg_velocity = pitching.get("era", None)  # Placeholder, ver si hay mejor campo
                    velocity = min(100, max(85, int(pitching.get("avg_fastball_velocity", 92))))
                break

        return {"velocity": velocity, "control": control, "movement": movement}

    @staticmethod
    def get_pitcher_pitch_types(player_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene los tipos de lanzamientos que usa un pitcher en orden de uso (máximo 4).
        Usa la API de Statcast para obtener datos reales del repertorio.
        """
        try:
            # Intentar obtener pitch types desde la API de personales stats
            url = f"{MLBSeedHelper.BASE_URL}/people/{player_id}"
            params = {"hydrate": "pitchData"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            pitch_types = data.get("people", [{}])[0].get("pitchData", {}).get("pitchTypes", [])
            
            if pitch_types:
                # Limitar a máximo 4 y retornar solo los nombres
                return pitch_types[:4]
        except Exception as e:
            print(f"   ⚠️  No se obtuvieron pitch types para {player_id}: {e}")
        
        # Fallback: Repertorio estándar (3 pitcheos)
        return ["FF", "SL", "CH"]

    @staticmethod
    def build_pitcher_repertoire(
        velocity: int,
        control: int,
        movement: int,
        pitch_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Construye el repertorio de 3-4 lanzamientos con variaciones realistas.
        
        Tipos de lanzamiento (abreviaturas MLB):
        - FF: Fastball 4-seam (recta rápida)
        - SL: Slider (deslizante)
        - CH: Changeup (cambio)
        - CU: Curveball (curva)
        - SI: Sinker (recta con movimiento)
        - FS: Splitter (divisor)
        """
        if not pitch_types:
            pitch_types = ["FF", "SL", "CH"]
        
        # Limitar a 4 pitcheos máximo
        pitch_types = pitch_types[:4]
        
        # Mapeo de tipos de lanzamientos a sus características
        PITCH_PROFILES = {
            "FF": {"name": "4-SEAM", "vel": 0, "ctl": 0, "mov": -5},      # Recta rápida, movimiento neutral
            "SL": {"name": "SLIDER", "vel": -8, "ctl": +2, "mov": +5},   # Más lenta, mejor control, más movimiento
            "CH": {"name": "CHANGE", "vel": -12, "ctl": 0, "mov": -2},   # Mucho más lenta, movimiento reducido
            "CU": {"name": "CURVE", "vel": -10, "ctl": -2, "mov": +8},   # Más lenta, movimiento pronunciado
            "SI": {"name": "SINKER", "vel": -2, "ctl": +1, "mov": +6},   # Casi igual de rápida, mucho movimiento
            "FS": {"name": "SPLITTER", "vel": -14, "ctl": +3, "mov": -3}, # Muy lenta, excelente control
        }
        
        repertoire = []
        for idx, pitch_code in enumerate(pitch_types):
            profile = PITCH_PROFILES.get(pitch_code, {"name": "UNKNOWN", "vel": 0, "ctl": 0, "mov": 0})
            
            pitch_obj = {
                "pitch_type": profile["name"],
                "velocity": min(100, max(75, velocity + profile["vel"])),
                "control": min(99, max(40, control + profile["ctl"])),
                "movement": min(99, max(40, movement + profile["mov"])),
            }
            repertoire.append(pitch_obj)
        
        return repertoire


    @staticmethod
    def _normalize_pitcher_position(position: str) -> str:
        """
        Normaliza la abreviatura de un lanzador desde la API de MLB hacia
        el vocabulario canónico del juego (core.enums.Position).

        La API de MLB suele devolver "P" como abreviatura genérica; el juego
        distingue SP/RP/SU/CP/CL/TWP. Si la posición ya es canónica se preserva;
        si es "P", se asigna SP como valor por defecto.
        """
        normalized = position.upper()
        if normalized in PITCHER_POSITIONS:
            return normalized
        if normalized in ("P",):
            return Position.STARTER.value  # "SP"
        # Cualquier otro valor (p. ej. variantes) cae a SP de forma segura
        if normalized and normalized.isalpha():
            return Position.STARTER.value
        return normalized

    @staticmethod
    def create_player_card(
        player_info: Dict[str, Any],
        team_id: str,
        is_pitcher: bool,
        db: Session
    ) -> Optional[PlayerCardModel]:
        """Crea una tarjeta de jugador en la BD"""
        try:
            player_id = player_info.get("person", {}).get("id")
            name = player_info.get("person", {}).get("fullName", "Unknown")
            position = player_info.get("position", {}).get("abbreviation", "DH")
            number = player_info.get("jerseyNumber", "0")

            if not player_id or not name:
                return None

            # ⭐ NORMALIZAR POSICIONES DE LANZADORES
            # La API de MLB devuelve "P" como abreviatura genérica de lanzador,
            # pero el juego distingue SP/RP/SU/CP/CL/TWP (ver core.enums.Position).
            if is_pitcher:
                position = MLBSeedHelper._normalize_pitcher_position(position)

            # Detectar jugadores "two-way" (batean y lanzan)
            is_two_way = is_pitcher and position == Position.TWO_WAY.value

            # Obtener stats del jugador
            player_stats = MLBSeedHelper.get_player_stats(player_id)
            
            # Determinar overall
            overall = 70
            if "jerseyNumber" in player_info and number and number != "0":
                # Usar el número de jersey como seed para overall (70-95)
                overall = 70 + (int(number) % 25)

            # Calcular atributos según posición
            if is_pitcher:
                pitch_attrs = MLBSeedHelper.calculate_pitching_attributes(player_stats)
                velocity = pitch_attrs.get("velocity", 92)
                control = pitch_attrs.get("control", 70)
                movement = pitch_attrs.get("movement", 75)
                contact = 40  # Pitchers no necesitan contacto
                power = 40
                
                # ⭐ NUEVO: Obtener tipos de lanzamientos reales y construir repertorio
                pitch_types = MLBSeedHelper.get_pitcher_pitch_types(player_id)
                repertoire = MLBSeedHelper.build_pitcher_repertoire(velocity, control, movement, pitch_types)
            else:
                batting_attrs = MLBSeedHelper.calculate_batting_attributes(player_stats)
                contact = batting_attrs.get("contact", 70)
                power = batting_attrs.get("power", 70)
                velocity = 90  # Batters no necesitan velocidad
                control = 60
                movement = 60
                repertoire = None

            # Para two-way players, también calcular atributos de bateo
            if is_two_way:
                batting_attrs = MLBSeedHelper.calculate_batting_attributes(player_stats)
                contact = batting_attrs.get("contact", 70)
                power = batting_attrs.get("power", 70)

            # Crear tarjeta (la rareza se asigna con la regla canónica del modelo)
            card = PlayerCardModel(
                id=f"card_{player_id}",
                team_id=team_id,
                name=name,
                number=number,
                position=position,
                overall=overall,
                rarity=PlayerCardModel.get_rarity_by_overall(overall),
                contact=contact,
                power=power,
                velocity=velocity,
                control=control,
                movement=movement,
                is_two_way=is_two_way,
                repertoire=repertoire,
            )

            db.add(card)
            return card

        except Exception as e:
            print(f"Error al crear tarjeta para {name}: {e}")
            return None


def seed_mlb_2026_data(db: Session):
    """Ejecuta el seed principal"""
    print("🔄 Iniciando seed de datos MLB 2026...")
    print(f"📅 Fecha de datos: 25 de Marzo de 2026")
    print()

    # ⭐ LIMPIAR TODAS LAS CARTAS (para evitar conflictos de IDs)
    print("🧹 Limpiando todas las cartas previas...")
    
    # Primero eliminar referencias en user_card_inventories (FK)
    from app.models import UserCardInventory
    deleted_inv = db.query(UserCardInventory).delete()
    print(f"   ✓ {deleted_inv} referencias de inventario eliminadas")
    
    # Luego eliminar todas las cartas
    deleted_cards = db.query(PlayerCardModel).delete()
    db.commit()
    print(f"   ✓ {deleted_cards} cartas previas eliminadas")
    print()

    # 1. Obtener equipos
    print("📥 Obteniendo equipos de MLB...")
    mlb_teams = MLBSeedHelper.get_all_teams()
    print(f"✓ Se obtuvieron {len(mlb_teams)} equipos")
    print()

    total_cards_created = 0

    # 2. Procesar cada equipo
    for idx, mlb_team in enumerate(mlb_teams, 1):
        real_id = mlb_team.get("abbreviation", "")
        real_name = mlb_team.get("name", "")
        mlb_team_id = mlb_team.get("id")

        # Obtener nombre ficticio
        fict_id, fict_name, city, color, badge = TEAM_FICTIONS.get(real_id, (real_id, real_name, "City", "#000000", real_id))

        print(f"[{idx}/30] 🏟️  {real_name} → {fict_name}")

        # Verificar si equipo ya existe
        existing_team = db.query(Team).filter(Team.id == fict_id).first()
        if existing_team:
            print(f"    ✓ Equipo ya existe en BD")
            team = existing_team
            # Asegurar que el flag CPU quede consistente
            if team.is_cpu is not False:
                team.is_cpu = False
                db.commit()
        else:
            # Crear equipo
            team = Team(
                id=fict_id,
                name=fict_name,
                city=city,
                primary_color=color,
                secondary_color="#FFFFFF",
                is_cpu=False,
            )
            db.add(team)
            db.commit()
            print(f"    ✓ Equipo creado")

        # 3. Obtener roster
        print(f"    📋 Obteniendo roster de 40 jugadores...")
        roster = MLBSeedHelper.get_team_roster(mlb_team_id)
        print(f"    ✓ {len(roster)} jugadores encontrados")

        # 4. Procesar jugadores
        pitchers_added = 0
        batters_added = 0

        for player_info in roster:
            position = player_info.get("position", {}).get("abbreviation", "DH")
            # "P" es la abreviatura genérica de lanzador en la API de MLB;
            # el juego la normaliza después a SP/RP/SU/CP/CL/TWP.
            is_pitcher = position.upper() in ("P",) or position.upper() in PITCHER_POSITIONS

            card = MLBSeedHelper.create_player_card(player_info, fict_id, is_pitcher, db)
            if card:
                if is_pitcher:
                    pitchers_added += 1
                else:
                    batters_added += 1
                total_cards_created += 1

        # ⭐ IMPORTANTE: Hacer commit después de procesar cada equipo
        db.commit()
        print(f"    ✓ {pitchers_added} lanzadores + {batters_added} bateadores agregados")
        print()

    print("✅ Seed completado exitosamente")
    print(f"📊 Resumen: 30 equipos x ~40 jugadores = {total_cards_created} jugadores cargados")
    print("💾 Todos los cambios se han persistido en la BD")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_mlb_2026_data(db)
        print("\n✅ Script completado. Los equipos y jugadores de MLB 2026 han sido cargados en la BD.")
        print("💾 Los cambios ya están persistidos en la base de datos.")
    except Exception as e:
        print(f"\n❌ Error durante el seed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

