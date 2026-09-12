"""CLI for the read-only PlayerRatings evidence stability audit."""

import argparse
import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from app.database import SessionLocal
from etl.services.rating_stability import audit_rating_stability


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _json_default(value):
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--from", dest="data_start_date", type=_date, required=True)
    parser.add_argument("--final", dest="final_date", type=_date, required=True)
    parser.add_argument("--rating-model-version", default="ratings-2.0")
    parser.add_argument("--distribution-version", default="dist-1.0")
    parser.add_argument("--snapshots", nargs="*", type=_date)
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        audit = audit_rating_stability(
            db,
            season=args.season,
            data_start_date=args.data_start_date,
            final_date=args.final_date,
            rating_model_version=args.rating_model_version,
            distribution_version=args.distribution_version,
            snapshot_dates=tuple(args.snapshots) if args.snapshots else None,
        )
        print(json.dumps(asdict(audit), default=_json_default, indent=2))
        return 0
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
