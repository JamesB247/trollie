"""Seed the synthetic merchants and catalogue into the configured database.

Usage: uv run python -m scripts.seed
"""

from sqlalchemy.orm import Session

from app.clock import SystemClock
from app.config import check_startup, get_settings
from app.db import check_deployment_marker, make_engine
from app.seed import seed


def main() -> None:
    settings = get_settings()
    check_startup(settings)
    engine = make_engine(settings)
    check_deployment_marker(engine, settings)
    with Session(engine) as session, session.begin():
        ids = seed(session, now=SystemClock().now())
    print(f"seeded {sum(k.startswith('merchant:') for k in ids)} fictional merchants")


if __name__ == "__main__":
    main()
