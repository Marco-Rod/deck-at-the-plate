from app.repositories.team_repository import find_cards_by_team

from tests.fixtures import seed_versioned_cpu_roster


def test_find_cards_by_team_sin_catalogo_conserva_consulta_historica(db):
    seeded = seed_versioned_cpu_roster(db)

    cards = find_cards_by_team(db, seeded["team"].id)
    catalog_ids = {card.catalog_id for card in cards}

    assert catalog_ids == {
        seeded["retired_catalog"].id,
        seeded["active_catalog"].id,
    }


def test_find_cards_by_team_puede_limitarse_a_un_catalogo(db):
    seeded = seed_versioned_cpu_roster(db)

    cards = find_cards_by_team(
        db,
        seeded["team"].id,
        catalog_id=seeded["active_catalog"].id,
    )

    assert cards
    assert {card.catalog_id for card in cards} == {seeded["active_catalog"].id}
    retired_ids = {card.id for card in seeded["retired_cards"]}
    returned_ids = {card.id for card in cards}
    assert returned_ids.isdisjoint(retired_ids)
