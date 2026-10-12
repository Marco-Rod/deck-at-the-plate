"""Orquestador del primer catálogo BASE jugable.

Este módulo expresa una intención de producto: desde datos MLB hasta un
catálogo BASE candidato, y opcionalmente activo. No contiene fórmulas de
ratings, reglas de rareza ni lógica del motor; cada una vive en su servicio
especializado. Así el flujo puede leerse, probarse y operar sin convertir el
CLI en otro módulo grande.

La activación siempre usa ``enforce_gameplay_gates=True``. Por ello un lote
V1 no puede quedar ACTIVE si no puede sostener rosters CPU, starter packs y
sobres. Sin ``activate`` el resultado permanece ``VALIDATING`` para revisión.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models import PlayerRatings
from app.services.card_editions import ensure_system_base_edition
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.pipelines.metadata import MetadataPipeline
from etl.pipelines.statcast import StatcastRawPipeline
from etl.services.card_catalog import promote_card_catalog, publish_card_catalog
from etl.services.catalog_repertoire_sync import sync_candidate_repertoires
from etl.services.card_rating_profiles import generate_card_rating_profile
from etl.services.identity_generation import validate_game_identities
from etl.services.player_ratings_as_of import generate_player_ratings_as_of
from etl.services.rating_distributions import build_overall_rating_distribution
from etl.services.ratings2_card_profiles import generate_card_profile_from_ratings2
from etl.services.season_bounds import resolve_regular_season_start
from etl.sources.mlb import MLBStatsApiClient
from etl.sources.statcast import StatcastSourceAdapter


@dataclass(frozen=True)
class BaseCatalogV1Result:
    """Reporte serializable de una ejecución, sin exponer objetos ORM."""

    season: int
    as_of_date: date
    data_start_date: date
    activate_requested: bool
    catalog_id: str
    catalog_status: str
    catalog_version: int
    cards_created: int
    ratings_by_role: dict[str, int] = field(default_factory=dict)
    profiles_by_status: dict[str, int] = field(default_factory=dict)
    stages: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


class BaseCatalogV1Pipeline:
    """Coordina las piezas existentes para crear el catálogo BASE de V1.

    Los clientes se pueden inyectar para pruebas. En producción se crean con
    sus adaptadores normales, sin que las dependencias de red se filtren hacia
    los servicios de ratings o catálogo.
    """

    def __init__(
        self,
        db: Session,
        *,
        mlb_client: MLBStatsApiClient | None = None,
        statcast_adapter: StatcastSourceAdapter | None = None,
    ) -> None:
        self._db = db
        self._mlb_client = mlb_client or MLBStatsApiClient()
        self._statcast_adapter = statcast_adapter or StatcastSourceAdapter()

    def run(
        self,
        *,
        season: int,
        as_of_date: date,
        activate: bool = False,
        ingest_statcast: bool = True,
    ) -> BaseCatalogV1Result:
        """Construye un candidato BASE y lo promueve sólo si se solicita.

        La operación es re-ejecutable: metadata y perfiles usan sus propias
        claves idempotentes, y el lifecycle devuelve no-op para una edición ya
        materializada. Una excepción de una etapa detiene el flujo; no intenta
        ocultar ni continuar con datos incompletos.
        """
        if as_of_date.year != season:
            raise ValueError("as_of_date debe pertenecer a season")

        data_start_date = resolve_regular_season_start(
            self._mlb_client, season=season, date_to=as_of_date
        )
        metadata = MetadataPipeline(self._db, self._mlb_client)
        source_teams = metadata.run_source_teams(
            season=season,
            data_start_date=data_start_date,
            data_end_date=as_of_date,
        )
        mappings = metadata.run_game_team_mappings(
            season=season,
            data_start_date=data_start_date,
            data_end_date=as_of_date,
            valid_from=data_start_date,
        )
        rosters = metadata.run_rosters(
            season=season,
            data_start_date=data_start_date,
            data_end_date=as_of_date,
        )
        identities = metadata.run_game_identities(season=season, missing_only=True)
        identity_gate = validate_game_identities(self._db, season=season)
        if not identity_gate.ok:
            raise ValueError("identidades GAME inválidas: " + "; ".join(identity_gate.detail))

        statcast = None
        if ingest_statcast:
            statcast = StatcastRawPipeline(self._db, self._statcast_adapter).run(
                date_from=data_start_date,
                date_to=as_of_date,
                season=season,
            )
        ratings = {
            role: generate_player_ratings_as_of(
                self._db,
                season=season,
                role=role,
                as_of_date=as_of_date,
                mlb_client=self._mlb_client,
            )
            for role in ("BATTER", "PITCHER")
        }
        # Los CardGenerationProfile calculan el tier relativo de cada jugador
        # contra esta población exacta. Estas distribuciones se construyen
        # después de materializar ambos roles; las distribuciones analíticas
        # creadas por ``generate_player_ratings_as_of`` no son equivalentes a
        # la distribución de overall requerida por el adaptador de cartas.
        overall_distributions = {
            role: build_overall_rating_distribution(
                self._db,
                season=season,
                role=role,
                data_start_date=data_start_date,
                data_end_date=as_of_date,
            )
            for role in ("BATTER", "PITCHER")
        }
        edition = ensure_system_base_edition(self._db, season=season)
        profile_statuses = self._materialize_profiles(
            season=season,
            data_start_date=data_start_date,
            as_of_date=as_of_date,
            card_edition_id=edition.id,
        )
        published = publish_card_catalog(
            self._db,
            season=season,
            card_edition_id=edition.id,
            rating_model_version=RATING_MODEL_VERSION,
            data_end_date=as_of_date,
            # El primer catálogo también debe atravesar los gates V1.
            activate_if_first=False,
        )
        # También hidrata candidatos creados antes de que V1 materializara
        # repertorios, sin volver a descargar ni recalcular datos RAW.
        repertoire_sync = None
        if published.status == "VALIDATING":
            repertoire_sync = sync_candidate_repertoires(
                self._db, catalog_id=published.catalog_id
            )
        final = published
        if activate and published.status == "VALIDATING":
            final = promote_card_catalog(
                self._db,
                catalog_id=published.catalog_id,
                enforce_gameplay_gates=True,
            )

        return BaseCatalogV1Result(
            season=season,
            as_of_date=as_of_date,
            data_start_date=data_start_date,
            activate_requested=activate,
            catalog_id=final.catalog_id,
            catalog_status=final.status,
            catalog_version=final.catalog_version,
            cards_created=final.created,
            ratings_by_role={
                role: getattr(result.ratings, "created", 0)
                + getattr(result.ratings, "updated", 0)
                + getattr(result.ratings, "unchanged", 0)
                for role, result in ratings.items()
            },
            profiles_by_status=profile_statuses,
            stages={
                "source_teams": source_teams,
                "game_mappings": mappings,
                "rosters": rosters,
                "identities": identities,
                "statcast": statcast,
                "identity_gate": identity_gate,
                "overall_distributions": overall_distributions,
                "repertoire_sync": repertoire_sync,
            },
            issues=list(final.issues),
        )

    def _materialize_profiles(
        self,
        *,
        season: int,
        data_start_date: date,
        as_of_date: date,
        card_edition_id: str,
    ) -> dict[str, int]:
        """Adapta cada snapshot ratings-2.0 sin recalcular sus fórmulas."""
        rows = (
            self._db.query(PlayerRatings)
            .filter(
                PlayerRatings.season == season,
                PlayerRatings.rating_model_version == RATING_MODEL_VERSION,
                PlayerRatings.data_start_date == data_start_date,
                PlayerRatings.data_end_date == as_of_date,
            )
            .order_by(PlayerRatings.player_id, PlayerRatings.role)
            .all()
        )
        statuses: dict[str, int] = {}
        for ratings in rows:
            generation = generate_card_profile_from_ratings2(
                self._db, player_ratings_id=ratings.id
            )
            statuses[generation.status] = statuses.get(generation.status, 0) + 1
            if generation.card_generation_profile_id is None:
                continue
            rating = generate_card_rating_profile(
                self._db,
                source_player_ratings_id=ratings.id,
                card_edition_id=card_edition_id,
            )
            statuses[rating.status] = statuses.get(rating.status, 0) + 1
        return statuses


def render_base_catalog_v1_report(result: BaseCatalogV1Result) -> str:
    """Renderiza el resultado para operación humana desde el CLI.

    La salida es intencionalmente compacta: el detalle de cada etapa permanece
    en logs y en ``result.stages`` para no convertir una ejecución normal en un
    volcado de objetos ORM o payloads de proveedores.
    """
    ratings = ", ".join(
        f"{role}={count}" for role, count in sorted(result.ratings_by_role.items())
    ) or "sin ratings"
    profiles = ", ".join(
        f"{status}={count}" for status, count in sorted(result.profiles_by_status.items())
    ) or "sin perfiles"
    lines = [
        "BASE catalog V1",
        f"season={result.season} as_of={result.as_of_date.isoformat()} start={result.data_start_date.isoformat()}",
        f"catalog={result.catalog_id} version={result.catalog_version} status={result.catalog_status} cards={result.cards_created}",
        f"ratings: {ratings}",
        f"profiles: {profiles}",
        "stages: " + ", ".join(result.stages),
    ]
    if result.issues:
        lines.append("issues: " + "; ".join(result.issues))
    return "\n".join(lines)
