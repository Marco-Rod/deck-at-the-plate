"""Contrato de la fachada CLI para el orquestador BASE V1."""

from datetime import date

from etl.cli import _build_parser
from etl.pipelines.base_catalog_v1 import BaseCatalogV1Result, render_base_catalog_v1_report


def test_build_base_catalog_parser_accepts_activation_and_statcast_retry():
    args = _build_parser().parse_args(
        [
            "build-base-catalog", "--season", "2026", "--as-of", "2026-06-15",
            "--activate", "--skip-statcast",
        ]
    )

    assert args.command == "build-base-catalog"
    assert args.season == 2026
    assert args.as_of_date == date(2026, 6, 15)
    assert args.activate is True
    assert args.skip_statcast is True


def test_sync_catalog_repertoires_parser_requires_catalog_id():
    args = _build_parser().parse_args(
        ["sync-catalog-repertoires", "--catalog-id", "candidate-1"]
    )

    assert args.command == "sync-catalog-repertoires"
    assert args.catalog_id == "candidate-1"


def test_base_catalog_report_is_compact_and_does_not_dump_stages():
    report = render_base_catalog_v1_report(
        BaseCatalogV1Result(
            season=2026,
            as_of_date=date(2026, 6, 15),
            data_start_date=date(2026, 3, 26),
            activate_requested=False,
            catalog_id="catalog-1",
            catalog_status="VALIDATING",
            catalog_version=1,
            cards_created=42,
            ratings_by_role={"BATTER": 20, "PITCHER": 22},
            profiles_by_status={"CREATED": 42},
            stages={"statcast": object(), "rosters": object()},
        )
    )

    assert "catalog=catalog-1 version=1 status=VALIDATING cards=42" in report
    assert "stages: statcast, rosters" in report
    assert "object at" not in report
