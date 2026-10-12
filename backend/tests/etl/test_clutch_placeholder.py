"""GAMEPLAY-RATING-002 -- Clutch como placeholder explícito (opción A).

Decisión registrada el 2026-10-01:

    Option:          A
    Neutral:         70
    Gameplay effect: NONE
    Current role:    ratings-2.0 placeholder only
    Future:          B (leverage situacional) cuando exista telemetry

Estos contratos fijan las dos mitades de esa decisión:

1. **No hay efecto de gameplay.** Un test conductual corre el `calculator` con
   el mismo seed y compara distribuciones de resultados variando sólo Clutch.
   Si alguien cablea Clutch sin querer, este test falla.
2. **El placeholder está bien formado.** El neutral es una constante canónica
   única, los pitchers no quedan en el piso del dominio, y el backfill nunca
   pisa Clutch que sí tenga fuente autoritativa.

La caracterización que_familyó a la decisión A está en el roadmap §26-bis:
`clutch_evidence` vacío (0/869 filas), `calculator` sin lectura de `clutch`, y
cero varianza en la columna (402 batters en 70, 404 pitchers en 0).
"""

import random

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.engine.stuff_policy import STUFF_BASELINE
from app.models import (
    CardGenerationProfile,
    CardRatingProfile,
    PlayerCardModel,
)
from app.models.card import CardRarity
from legacy.seeds.backfill_cards import NEUTRAL_CLUTCH, backfill_catalog_clutch
from etl.config.ratings_2 import CLUTCH_NEUTRAL_RATING, CLUTCH_SOURCE
from etl.services.card_catalog import _validate_rows, publish_card_catalog
from etl.services.card_rating_profiles import generate_card_rating_profile
from tests.etl.test_card_catalog_rating_profile import (
    END,
    _batter_ratings,
    _generation_profile,
    _pitcher_profile,
    _pitcher_ratings,
    _publication_context,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _publish(db, edition):
    return publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )


def _catalog_id(db):
    from app.models import CardCatalog

    return db.query(CardCatalog).filter_by(status="ACTIVE").one().id


class TestA1ElNeutralEsUnaSolaConstante:
    """A1 — no puede haber dos "neutros" de Clutch circulando."""

    def test_el_neutral_canónico_es_70(self):
        assert CLUTCH_NEUTRAL_RATING == 70

    def test_el_backfill_legacy_usa_la_misma_constante(self):
        """`NEUTRAL_CLUTCH` era 50 y divergía de la fuente canónica (70)."""
        assert NEUTRAL_CLUTCH == CLUTCH_NEUTRAL_RATING == 70

    def test_la_fuente_declara_que_es_un_placeholder(self):
        """El motivo del placeholder está escrito, no implícito."""
        assert "SITUATIONAL" in CLUTCH_SOURCE.upper()
        assert "NEUTRAL" in CLUTCH_SOURCE.upper()

    def test_sin_catalogo_activo_falla_explícitamente(self, db):
        """No debe escribir en un catálogo inventado."""
        with pytest.raises(RuntimeError, match="ACTIVE BASE"):
            backfill_catalog_clutch(db, catalog_id=None, apply=False)


class TestA2PublicacionMaterializaElNeutral:
    """A2 — un pitcher publica Clutch neutral, no 0."""

    def test_pitcher_publica_el_neutral(self, db):
        _team, player, player_season, edition = _publication_context(
            db, primary_position="SP"
        )
        _pitcher_profile(db, player_season, _pitcher_ratings(db, player))
        db.commit()

        result = _publish(db, edition)
        card = db.query(PlayerCardModel).one()

        assert result.status == "ACTIVE"
        # `clutch_rating` es NULL por diseño para PITCHER (role-shape CHECK).
        assert card.clutch == CLUTCH_NEUTRAL_RATING
        assert card.clutch != 0, "0 es el piso del dominio, no el neutral"

    def test_batter_conserva_su_clutch_autoritativo(self, db):
        """El neutral sólo rellena ausencias; nunca pisa un valor real."""
        _team, player, player_season, edition = _publication_context(
            db, primary_position="DH"
        )
        _generation_profile(db, player_season, _batter_ratings(db, player))
        db.commit()

        _publish(db, edition)
        card = db.query(PlayerCardModel).one()
        profile = db.query(CardGenerationProfile).one()

        assert card.clutch == profile.clutch_rating == CLUTCH_NEUTRAL_RATING

    def test_la_validacion_rechaza_clutch_ausente(self, db):
        """`getattr(card, 'clutch') or 0` enmascararía None como 0."""
        row = PlayerCardModel(name="x", overall=50, stuff=STUFF_BASELINE)

        row.clutch = None
        issues = _validate_rows([row])
        assert any("clutch sin materializar" in i for i in issues), issues

        row.clutch = CLUTCH_NEUTRAL_RATING
        assert not any("clutch" in i for i in _validate_rows([row]))


class TestA3BackfillRellenaAusencias:
    """A3 — el backfill corrige datos previos al fix, sin pisar datos reales.

    Con la publicación ya corregida, una carta recién publicada nace en el
    neutral y el backfill es no-op. Su trabajo real es sobre el catálogo ya
    publicado antes del fix, donde los pitchers quedaron en 0. Estos tests
    reproducen ese estado putting la columna a 0 explícitamente.
    """

    def _pre_fix_state(self, db):
        """Un pitcher en 0 (estado pre-fix) y un batter con Clutch real."""
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

        # Estado pre-fix: el pitcher quedó en el piso del dominio.
        pitcher = db.query(PlayerCardModel).filter_by(name="Ace").one()
        assert pitcher.clutch == CLUTCH_NEUTRAL_RATING  # la publicación ya lo arregla
        pitcher.clutch = 0
        db.commit()
        return edition

    def test_dry_run_no_escribe(self, db):
        self._pre_fix_state(db)
        before = {c.id: c.clutch for c in db.query(PlayerCardModel).all()}

        summary = backfill_catalog_clutch(db, catalog_id=_catalog_id(db), apply=False)
        db.expire_all()
        after = {c.id: c.clutch for c in db.query(PlayerCardModel).all()}

        assert summary["changed"] == 1
        assert after == before, "el dry-run no debe escribir"

    def test_apply_escribe_el_neutral(self, db):
        self._pre_fix_state(db)
        summary = backfill_catalog_clutch(db, catalog_id=_catalog_id(db), apply=True)

        cards = {c.name: c for c in db.query(PlayerCardModel).all()}
        assert cards["Ace"].clutch == CLUTCH_NEUTRAL_RATING
        assert summary["changed"] == 1
        assert summary["neutral"] == CLUTCH_NEUTRAL_RATING == 70

    def test_es_idempotente(self, db):
        self._pre_fix_state(db)
        catalog_id = _catalog_id(db)
        backfill_catalog_clutch(db, catalog_id=catalog_id, apply=True)
        second = backfill_catalog_clutch(db, catalog_id=catalog_id, apply=True)

        assert second["changed"] == 0
        assert second["unchanged"] == 1

    def test_no_pisa_clutch_con_fuente_autoritativa(self, db):
        """El bateador tiene Clutch autoritativo: se omite, no se sobreescribe."""
        self._pre_fix_state(db)
        summary = backfill_catalog_clutch(db, catalog_id=_catalog_id(db), apply=True)

        assert summary["skipped_with_authoritative_clutch"] == 1
        assert summary["changed"] == 1  # sólo el pitcher

    def test_no_toca_otros_catalogos(self, db):
        from app.models import CardCatalog

        edition = self._pre_fix_state(db)
        catalog_id = _catalog_id(db)
        ace = db.query(PlayerCardModel).filter_by(name="Ace").one()

        retired = CardCatalog(
            id="retired-catalog",
            season=2026,
            edition_type="BASE",
            status="RETIRED",
            version=0,
            rating_model_version="LEGACY",
            data_end_date=END,
        )
        db.add(retired)
        db.commit()

        # Una carta del catálogo histórico, con el Clutch que dejó el backfill
        # legacy (no el neutral) para demostrar que no se reescribe.
        legacy_card = PlayerCardModel(
            id="legacy-card",
            card_edition_id=edition.id,
            catalog_id="retired-catalog",
            game_identity_id=ace.game_identity_id,
            team_id=ace.team_id,
            name="Legacy Guy",
            number="00",
            position="SP",
            overall=70,
            rarity=ace.rarity,
            contact=60,
            power=60,
            velocity=80,
            control=70,
            movement=70,
            vision=0,
            clutch=50,
            stuff=STUFF_BASELINE,
            is_active=False,
            is_pack_eligible=False,
        )
        db.add(legacy_card)
        db.commit()

        backfill_catalog_clutch(db, catalog_id=catalog_id, apply=True)

        db.expire_all()
        untouched = db.query(PlayerCardModel).filter_by(id="legacy-card").one()
        assert untouched.clutch == 50, "un catálogo retirado es histórico"


class TestA4ClutchNoAfectaElGameplay:
    """A4 — la decisión A, verificada conductualmente contra el calculator.

    Se cubren las DOS ramas del resolver, porque consumen atributos distintos:

    - **SWING**: `_calculate_contact_outcome(con, pwr, vel, mov, ...)` ---
      aquí vive la calidad de contacto y es donde se inserta Stuff.
    - **TAKE**: `_take_stake_probability(take_bias, ctl, vis, ...)` --- aquí
      `vision` sí pesa, y `con`/`pwr` no.

    Cubrir sólo una habría dejado un agujero: cablear Clutch en la rama
    TAKE no movería nada en un test que sólo corre swings.
    """

    PITCHER = {"velocidad": 90, "control": 85, "movimiento": 88, "stuff": STUFF_BASELINE}
    PITCH = {"zone": 5, "pitch_type": "SLIDER"}
    TRIALS = 400

    SWING = {"swing_type": "NORMAL", "guessed_zone": 5, "guessed_pitch": "SLIDER"}
    TAKE = {"swing_type": "TAKE", "guessed_zone": 5, "guessed_pitch": "SLIDER"}

    def _distribution(self, batter_attrs, swing, seed0=0, seed_pitcher_stuff=None):
        from app.engine.calculator import _resolve_play_outcome

        pitcher = dict(self.PITCHER)
        if seed_pitcher_stuff is not None:
            pitcher["stuff"] = seed_pitcher_stuff

        counts = {}
        for i in range(self.TRIALS):
            random.seed(seed0 + i)
            result = _resolve_play_outcome(pitcher, batter_attrs, self.PITCH, swing)
            key = (result.event, result.description)
            counts[key] = counts.get(key, 0) + 1
        return counts

    # --- SWING: donde una Clutch mal cableada se notaría ---

    def test_swing_variar_clutch_no_cambia_la_distribución(self):
        base = {"contacto": 75, "poder": 80, "vision": 70}
        low = self._distribution({**base, "clutch": 0}, self.SWING)
        neutral = self._distribution({**base, "clutch": CLUTCH_NEUTRAL_RATING}, self.SWING)
        high = self._distribution({**base, "clutch": 99}, self.SWING)

        assert low == neutral, "Clutch altera el swing: decisión A violada"
        assert neutral == high, "Clutch altera el swing: decisión A violada"

    def test_swing_el_arnés_detecta_poder(self):
        """Contramuestra: en la rama SWING, `poder` SÍ mueve la distribución."""
        base = {"contacto": 75, "vision": 70, "clutch": CLUTCH_NEUTRAL_RATING}
        weak = self._distribution({**base, "poder": 20}, self.SWING)
        strong = self._distribution({**base, "poder": 99}, self.SWING)

        assert weak != strong, "el arnés SWING no detecta diferencias: test vacuío"

    # --- TAKE: `vision` pesa, `con`/`pwr` no ---

    def test_take_variar_clutch_no_cambia_la_distribución(self):
        base = {"contacto": 75, "poder": 80, "vision": 70}
        low = self._distribution({**base, "clutch": 0}, self.TAKE)
        high = self._distribution({**base, "clutch": 99}, self.TAKE)

        assert low == high, "Clutch altera el take: decisión A violada"

    def test_take_el_arnés_detecta_vision(self):
        """Contramuestra: en la rama TAKE, `vision` SÍ mueve la distribución."""
        base = {"contacto": 75, "poder": 80, "clutch": CLUTCH_NEUTRAL_RATING}
        blind = self._distribution({**base, "vision": 20}, self.TAKE)
        keen = self._distribution({**base, "vision": 95}, self.TAKE)

        assert blind != keen, "el arnés TAKE no detecta diferencias: test vacuío"

    # --- Contraste: Stuff sí está cableado (GAMEPLAY-ENGINE-003B) ---

    def test_stuff_sí_mueve_la_distribución(self):
        batter = {"contacto": 75, "poder": 80, "vision": 70, "clutch": CLUTCH_NEUTRAL_RATING}
        baseline = self._distribution(batter, self.SWING, seed_pitcher_stuff=STUFF_BASELINE)
        elite = self._distribution(batter, self.SWING, seed_pitcher_stuff=97)

        assert baseline != elite, "Stuff debería estar cableado (003B): contraste caído"
