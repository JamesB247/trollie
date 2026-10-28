"""Business-operation idempotency (blueprint §10.5; T25).

Same key + same request → the original response is replayed, with no second effect.
Same key + different request → DUPLICATE_OPERATION_CONFLICT.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.durable.hashing import canonical_hash
from app.durable.models import IdempotencyRecord
from app.errors import ErrorCode, TrollieError


@dataclass
class Operation:
    record: IdempotencyRecord

    @property
    def replay(self) -> bool:
        return self.record.completed

    @property
    def response(self) -> dict[str, Any] | None:
        return self.record.response

    def complete(self, response: dict[str, Any]) -> None:
        self.record.completed = True
        self.record.response = response


def begin(session: Session, *, scope: str, key: str, request: Any) -> Operation:
    """Claim (scope, key) for this request under a row lock held until commit.

    A concurrent caller with the same key blocks until the first commits, then sees
    a completed record and replays it.
    """
    request_hash = canonical_hash(request)
    session.execute(
        insert(IdempotencyRecord)
        .values(scope=scope, key=key, request_hash=request_hash)
        .on_conflict_do_nothing(index_elements=["scope", "key"])
    )
    record = session.scalars(
        select(IdempotencyRecord)
        .where(IdempotencyRecord.scope == scope, IdempotencyRecord.key == key)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if record.request_hash != request_hash:
        raise TrollieError(
            ErrorCode.DUPLICATE_OPERATION_CONFLICT,
            "idempotency key reused with a different request",
            scope=scope,
            key=key,
        )
    return Operation(record)
