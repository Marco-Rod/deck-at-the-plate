"""DATA-STUFF-001 — la cadena ratings-2.0 → player_cards.stuff está cerrada.

Contexto
--------
El motor consume ``card.stuff`` (GAMEPLAY-ENGINE-003B: contact-quality
suppression, k=.30 / α=.50), pero la ruta de publicación nunca asignó esa
columna: ``_card_from_profile`` leía ``stuff_rating`` dentro de ``_RATING_FIELDS``
y lo descartaba. Toda carta publicada caía en el ``server_default`` 70, es decir
Stuff exactamente neutro para toda la flota.

    "el motor habla Stuff pero el catálogo lo silencia"

La auditoría de producción (``etl/audit_stuff_propagation.py``) encontró
392/404 pitchers ACTIVE con ``card.stuff == 70`` mientras el Stuff
autoritativo de ratings-2.0 era otro valor (2.97% de materialización).

Estos contratos congelan la corrección en tres frontiers:

    S1  la publicación materializa ``stuff`` (no vuelve a caer en el default)
    S2  la validación de publicación falla si ``stuff`` no llega
    S3  el backfill es explícito, idempotente y sólo de pitchers

Y el que más importa a futuro:

    S4  un catálogo nuevo no puede reintroducir el silent default

Por qué el role-shape importa
-----------------------------
``stuff_rating`` es NULL **por diseño** para BATTER (CHECK
``ck_card_rating_profiles_complete_role_shape``) y ``player_cards.stuff`` es
NOT NULL. Tratar las 806 cartas como una población homogénea produciría ~402
correcciones inventadas. Los contratos S1/S3 fijan la separación: la flota de
bateo permanece en ``STUFF_BASELINE``, que es su valor exacto (delta 0,
supresión 0), no un 0 que sesgaría hacia abajo.
"""

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.engine.stuff_policy import STUFF_BASELINE, stuff_power_suppression
from app.models import (
    CardCatalog,
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    CardRatingProfile,
    PlayerCardModel,
    PlayerRatings,
)
from app.models.card import CardRarity
from legacy.seeds.backfill_cards import backfill_catalog_stuff
from etl.services.card_catalog import _validate_rows, publish_card_catalog
from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION

from tests.etl.test_card_catalog_rating_profile import (
    END,
    START,
    _batter_ratings,
    _generation_profile,
    _pitcher_profile,
    _pitcher_ratings,
    _publication_context,
    _rating_distribution,
)
from etl.services.card_rating_profiles import generate_card_rating_profile


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(sqlite_engine):
    session = sessionmaker(bind=sqlite_engine)()
    yield session
    session.close()


def _publish(db, edition):
    return publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )


def _active_catalog(db):
    return db.query(CardCatalog).filter_by(status="ACTIVE").one()


class TestS1PublicacionMaterializaStuff:
    """S1 — la publicación escribe el Stuff autoritativo en la carta."""

    def test_pitcher_publica_stuff_de_su_rating_profile(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)  # stuff_rating=74
        _pitcher_profile(db, player_season, ratings)
        db.commit()

        result = _publish(db, edition)
        card = db.query(PlayerCardModel).one()

        assert result.status == "ACTIVE"
        assert card.stuff == 74

    def test_pitcher_no_hereda_el_baseline_por_defecto(self, db):
        """Regresión directa del defecto: stuff != STUFF_BASELINE.

        Si esto vuelve a 70, la cadena se rompió otra vez.
        """
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()

        _publish(db, edition)
        card = db.query(PlayerCardModel).one()

        assert card.stuff != STUFF_BASELINE
        assert stuff_power_suppression(card.stuff) != 0.0

    def test_batter_queda_en_el_baseline_exacto(self, db):
        """`stuff_rating` es NULL para BATTER; el fallback es el baseline, no 0.

        Escribir 0 en vez de STUFF_BASELINE daría supresión +21 en lugar de 0:
        un sesgo grande e invisible sobre las 402 cartas de bateo.
        """
        _team, player, player_season, edition = _publication_context(
            db, primary_position="DH"
        )
        ratings = _batter_ratings(db, player)  # stuff_rating ausente por diseño
        _generation_profile(db, player_season, ratings)
        db.commit()

        _publish(db, edition)
        card = db.query(PlayerCardModel).one()

        assert card.stuff == STUFF_BASELINE
        assert stuff_power_suppression(card.stuff) == 0.0

    def test_fallback_a_generation_profile_tambien_materializa(self, db):
        """Sin CardRatingProfile la fuente es el CardGenerationProfile."""
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()

        _publish(db, edition)
        card = db.query(PlayerCardModel).one()

        assert card.card_rating_profile_id is None
        assert card.stuff == 74

    def test_publicacion_es_idempotente_en_stuff(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()

        _publish(db, edition)
        first = db.query(PlayerCardModel).one().stuff
        _publish(db, edition)

        assert db.query(PlayerCardModel).count() == 1
        assert db.query(PlayerCardModel).one().stuff == first


class TestS2ValidacionDePublicacion:
    """S2 — la validación falla si `stuff` no llega a la carta."""

    def _card(self, db, **overrides):
        payload = {
            "name": "Probe",
            "overall": 80,
            "position": "SP",
            "stuff": STUFF_BASELINE,
            "card_edition_id": db.info["edition_id"],
        }
        payload.update(overrides)
        return PlayerCardModel(**payload)

    def test_stuff_fuera_de_rango_se_reporta(self, db):
        _team, _player, _ps, edition = _publication_context(db)
        db.info["edition_id"] = edition.id

        issues = _validate_rows([self._card(db, stuff=140)])

        assert any("stuff fuera de rango" in issue for issue in issues)

    def test_stuff_none_se_reporta(self, db):
        """`getattr(card, f) or 0` enmascararía None como 0 (dentro de rango)."""
        _team, _player, _ps, edition = _publication_context(db)
        db.info["edition_id"] = edition.id
        card = self._card(db)
        card.stuff = None

        issues = _validate_rows([card])

        assert any("stuff sin materializar" in issue for issue in issues)

    def test_stuff_en_rango_no_se_reporta(self, db):
        _team, _player, _ps, edition = _publication_context(db)
        db.info["edition_id"] = edition.id

        issues = _validate_rows([self._card(db, stuff=45), self._card(db, stuff=96)])

        assert not any("stuff" in issue for issue in issues)


class TestS3BackfillControlado:
    """S3 — el backfill es explícito, idempotente y sólo de pitchers."""

    def test_dry_run_no_escribe(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()
        _publish(db, edition)

        card = db.query(PlayerCardModel).one()
        card.stuff = STUFF_BASELINE  # reproduce el silent default
        db.commit()

        summary = backfill_catalog_stuff(db, catalog_id=_active_catalog(db).id)

        assert summary["apply"] is False
        assert summary["changed"] == 1
        db.rollback()
        assert db.query(PlayerCardModel).one().stuff == STUFF_BASELINE

    def test_apply_escribe_el_stuff_autoritativo(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()
        _publish(db, edition)

        card = db.query(PlayerCardModel).one()
        card.stuff = STUFF_BASELINE
        db.commit()

        summary = backfill_catalog_stuff(
            db, catalog_id=_active_catalog(db).id, apply=True
        )

        assert summary["changed"] == 1
        assert summary["unchanged"] == 0
        assert db.query(PlayerCardModel).one().stuff == 74

    def test_es_idempotente(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()
        _publish(db, edition)
        catalog_id = _active_catalog(db).id

        backfill_catalog_stuff(db, catalog_id=catalog_id, apply=True)
        second = backfill_catalog_stuff(db, catalog_id=catalog_id, apply=True)

        assert second["changed"] == 0
        assert second["unchanged"] == 1

    def test_no_toca_cartas_de_bateo(self, db):
        """Una flota de bateo en 70 es su valor correcto, no un mismatch."""
        _team, player, player_season, edition = _publication_context(
            db, primary_position="DH"
        )
        ratings = _batter_ratings(db, player)
        _generation_profile(db, player_season, ratings)
        generate_card_rating_profile(
            db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
        )
        db.commit()
        _publish(db, edition)

        summary = backfill_catalog_stuff(
            db, catalog_id=_active_catalog(db).id, apply=True
        )

        assert summary["changed"] == 0
        assert summary["batter_cards_untouched"] == 1
        assert db.query(PlayerCardModel).one().stuff == STUFF_BASELINE

    def test_reports_fuente_de_cada_carta(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        generate_card_rating_profile(
            db, source_player_ratings_id=ratings.id, card_edition_id=edition.id
        )
        db.commit()
        _publish(db, edition)

        summary = backfill_catalog_stuff(
            db, catalog_id=_active_catalog(db).id, apply=True
        )

        assert summary["stuff_sources"]["card_rating_profile"] == 1

    def test_no_afecta_a_otros_catalogos(self, db):
        """No es un filtro global: otro catálogo queda intacto."""
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()
        _publish(db, edition)

        # Un catálogo RETIRED distinto, con una edición propia.
        other_edition = CardEdition(
            code="2026_BASE_RETIRED",
            name="Base Retirada",
            edition_type=CardEditionType.BASE,
            season=2026,
            version="edition-9.0",
            source_type=CardEditionSourceType.SYSTEM,
            rating_policy_version=BASE_RATING_POLICY_VERSION,
            metadata_payload={},
        )
        db.add(other_edition)
        db.flush()
        other = CardCatalog(
            season=2026,
            edition_type=CardEditionType.BASE,
            version=99,
            status="RETIRED",
            card_edition_id=other_edition.id,
        )
        db.add(other)
        db.flush()

        card = db.query(PlayerCardModel).one()
        card.catalog_id = other.id
        card.card_edition_id = other_edition.id
        card.stuff = STUFF_BASELINE
        db.commit()

        backfill_catalog_stuff(db, catalog_id=_active_catalog(db).id, apply=True)

        assert db.query(PlayerCardModel).one().stuff == STUFF_BASELINE


class TestS4NoRegresionAlSilentDefault:
    """S4 — un catálogo nuevo no puede volver a silenciar Stuff."""

    def test_poblacion_actual_queda_sin_mismatches(self, db):
        """Pitchers y batters conviven: 0 silent defaults entre ambos."""
        _team, p1, ps1, edition = _publication_context(
            db, primary_position="SP", mlb_id=660271, name="Ace"
        )
        p1_ratings = _pitcher_ratings(db, p1)
        _pitcher_profile(db, ps1, p1_ratings)
        generate_card_rating_profile(
            db, source_player_ratings_id=p1_ratings.id, card_edition_id=edition.id
        )

        _team2, p2, ps2, ed2 = _publication_context(
            db,
            primary_position="DH",
            mlb_id=660272,
            name="Slugger",
            team_key="team-2",
            source_external_id=2,
        )
        p2_ratings = _batter_ratings(db, p2)
        _generation_profile(db, ps2, p2_ratings)
        generate_card_rating_profile(
            db, source_player_ratings_id=p2_ratings.id, card_edition_id=ed2.id
        )
        db.commit()

        _publish(db, edition)
        cards = db.query(PlayerCardModel).all()

        # Reproduce la clasificación de la auditoría: para cada carta de
        # pitcher, card.stuff debe coincidir con el Stuff autoritativo.
        profiles = {
            p.id: p
            for p in db.query(CardRatingProfile)
            .filter(CardRatingProfile.id.in_([c.card_rating_profile_id for c in cards]))
            .all()
        }
        # Sin este assert el test pasa en vacío: si `profiles` viniera vacío, el
        # bucle haría `continue` en cada carta y `silent_defaults` sería 0
        # siempre. Es la razón de existir de este contrato.
        assert len(profiles) == 2, "las cartas deben apuntar a un CardRatingProfile"
        assert len([c for c in cards if c.card_rating_profile_id]) == 2

        silent_defaults = 0
        for card in cards:
            profile = profiles.get(card.card_rating_profile_id)
            if profile is None or profile.role != "PITCHER":
                continue
            if card.stuff == STUFF_BASELINE and profile.stuff_rating != STUFF_BASELINE:
                silent_defaults += 1

        assert silent_defaults == 0

    def test_mapa_produccion_usa_el_stuff_de_la_carta(self, db):
        """El atributo persistido llega al mapper, no al revés."""
        from app.engine.attribute_mapper import map_card_to_pitcher_attrs

        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        ratings = _pitcher_ratings(db, player)
        _pitcher_profile(db, player_season, ratings)
        db.commit()
        _publish(db, edition)

        card = db.query(PlayerCardModel).one()
        attrs = map_card_to_pitcher_attrs(card)

        assert attrs["stuff"] == card.stuff == 74


class TestS5LaAuditoriaMideLoQueDice:
    """S5 — la auditoría que produjo el 392 no puede dejar de medirlo.

    `392` es el número que Justificó abrir 001B. Si su clasificación o su
    precedencia cambiaran en silencio, el roadmap volvería a mentir.
    """

    def test_clasifica_el_mismatch_critico(self):
        from etl.audit_stuff_propagation import (
            CLASS_DIVERGENT,
            CLASS_EXACT,
            CLASS_EXACT_BASELINE,
            CLASS_SILENT_DEFAULT,
            CLASS_STALE_OVERRIDE,
            _classify,
        )

        # El caso que produjo 392: la carta quedó en el server_default y el
        # autoritativo es otro. Cuenta como silent default tanto si el
        # autoritativo es bajo como alto.
        assert _classify(STUFF_BASELINE, 45) == CLASS_SILENT_DEFAULT
        assert _classify(STUFF_BASELINE, 97) == CLASS_SILENT_DEFAULT

        # Coincidencias: el baseline exacto es una clase propia, no "exact",
        # porque es indistinguible de un default silencioso sin el autoritativo.
        assert _classify(STUFF_BASELINE, STUFF_BASELINE) == CLASS_EXACT_BASELINE
        assert _classify(74, 74) == CLASS_EXACT

        # Divergencia en los dos sentidos, que no es el mismo defecto.
        assert _classify(97, STUFF_BASELINE) == CLASS_STALE_OVERRIDE
        assert _classify(80, 45) == CLASS_DIVERGENT

    def test_precedencia_de_la_auditoria(self):
        from etl.audit_stuff_propagation import (
            SOURCE_BASELINE,
            SOURCE_PLAYER_RATINGS,
            SOURCE_PROFILE,
            _resolve_authoritative_stuff,
        )

        profile = {"stuff_rating": 82}
        rating = {"stuff_rating": 61}

        # Perfil manda, aunque PlayerRatings tenga otro valor.
        assert _resolve_authoritative_stuff(profile, rating) == (82, SOURCE_PROFILE)

        # stuff_rating NULL en el perfil (así es para BATTER) cae a
        # PlayerRatings, no a inventar un valor.
        assert _resolve_authoritative_stuff({"stuff_rating": None}, rating) == (
            61,
            SOURCE_PLAYER_RATINGS,
        )

        # Sin perfil, la ruta fallback de la publicación sigue siendo válida.
        assert _resolve_authoritative_stuff(None, rating) == (61, SOURCE_PLAYER_RATINGS)

        # Sin ninguna fuente autoritativa: baseline exacto, marcado como tal.
        assert _resolve_authoritative_stuff(None, None) == (
            STUFF_BASELINE,
            SOURCE_BASELINE,
        )

    def test_la_auditoria_no_afirma_d6_sin_evidencia(self, db, sqlite_engine, monkeypatch, capsys):
        """D6 se deriva de conteos before/after, no se declara PASS."""
        import json

        from etl import audit_stuff_propagation as audit

        _team, p1, ps1, edition = _publication_context(
            db, primary_position="SP", mlb_id=660271, name="Ace"
        )
        p1_ratings = _pitcher_ratings(db, p1)
        _pitcher_profile(db, ps1, p1_ratings)
        generate_card_rating_profile(
            db, source_player_ratings_id=p1_ratings.id, card_edition_id=edition.id
        )

        _team2, p2, ps2, ed2 = _publication_context(
            db,
            primary_position="DH",
            mlb_id=660272,
            name="Slugger",
            team_key="team-2",
            source_external_id=2,
        )
        p2_ratings = _batter_ratings(db, p2)
        _generation_profile(db, ps2, p2_ratings)
        generate_card_rating_profile(
            db, source_player_ratings_id=p2_ratings.id, card_edition_id=ed2.id
        )
        db.commit()
        _publish(db, edition)

        monkeypatch.setattr(audit, "engine", sqlite_engine)
        # `Base.metadata.create_all` no crea `alembic_version`: la auditoría
        # assume una BD migrada (en producción siempre la hay).
        with sqlite_engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
            conn.execute(text("INSERT INTO alembic_version VALUES ('0042')"))

        audit.main(["--sample", "0"])
        report = json.loads(capsys.readouterr().out)

        assert report["schema"]["alembic_head"] == "0042"
        assert report["schema"]["player_cards_stuff_column"] is True

        # Un único documento JSON parseable, con la prueba de D6 dentro.
        assert report["block"] == "DATA-STUFF-001A"
        assert report["rollback_integrity"]["clean"] is True
        assert report["contracts"]["D6"]["status"] == "PASS"
        assert report["contracts"]["D6"]["observed"]["table_counts_unchanged"] is True

        # La flota de bateo no infla el contador crítico: sin esto, una carta
        # de bateo en 70 contaría como mismatch y el "392" sería ~794.
        assert report["role_split"]["PITCHER"] == 1
        assert report["role_split"]["BATTER"] == 1
        assert report["counters"]["total_pitcher_cards"] == 1
        assert report["counters"]["total_active"] == 2
        assert report["counters"]["silent_default_mismatch"] == 0
        assert report["counters"]["exact_match"] == 1
