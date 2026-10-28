"""Imports every model module so Base.metadata is complete (Alembic autogenerate, tests)."""

from app.controls import models as controls_models  # noqa: F401
from app.ledger import models as ledger_models  # noqa: F401
from app.models import Base

metadata = Base.metadata
