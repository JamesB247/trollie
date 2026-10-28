"""Imports every model module so Base.metadata is complete (Alembic autogenerate, tests)."""

from app.accounts import models as accounts_models  # noqa: F401
from app.controls import models as controls_models  # noqa: F401
from app.delivery import models as delivery_models  # noqa: F401
from app.durable import models as durable_models  # noqa: F401
from app.ledger import models as ledger_models  # noqa: F401
from app.merchants import models as merchants_models  # noqa: F401
from app.models import Base
from app.offers import models as offers_models  # noqa: F401
from app.products import models as products_models  # noqa: F401

metadata = Base.metadata
