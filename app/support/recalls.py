"""Product recall traceability (T44): which approved purchases contained a product."""

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.orders.models import Order
from app.quotes.models import Quote


def orders_containing(session: Session, product_id: uuid.UUID) -> list[dict]:
    """Orders whose approved, immutable snapshot included the product, with the seller and
    quantity per leg. Identification only; the response workflow is operational."""
    path = text("quotes.snapshot @? cast(:path AS jsonpath)").bindparams(
        path=f'$.legs[*].lines[*].product.id ? (@ == "{product_id}")'
    )
    rows = session.execute(
        select(Order, Quote).join(Quote, Quote.id == Order.quote_id).where(path)
    ).all()
    out = []
    for order, quote in rows:
        for leg in quote.snapshot["legs"]:
            for line in leg["lines"]:
                if line["product"]["id"] == str(product_id):
                    out.append(
                        {
                            "order_id": str(order.id),
                            "account_id": str(order.account_id),
                            "state": order.state,
                            "seller": leg["seller"]["legal_name"],
                            "units": line["units"],
                        }
                    )
    return out
