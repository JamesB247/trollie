"""Quotes as approval subjects (blueprint §5.3, §13.1)."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.approvals.models import Approval
from app.errors import ErrorCode, TrollieError
from app.quotes.models import Quote, QuoteKind, QuoteState
from app.quotes.service import expire_if_due, owned_quote, recompute_hash


class QuoteSubject:
    def current_hash(
        self,
        session: Session,
        account_id: uuid.UUID,
        subject_id: uuid.UUID,
        now: datetime,
        *,
        lock: bool,
    ) -> tuple[str, datetime]:
        quote = owned_quote(session, subject_id, account_id, lock=lock)
        if quote.kind != QuoteKind.FIRM:
            raise TrollieError(
                ErrorCode.VALIDATION_FAILED, "an estimate cannot be approved; request a firm quote"
            )
        if expire_if_due(session, quote, now):
            raise TrollieError(
                ErrorCode.QUOTE_EXPIRED, "quote is no longer valid", state=quote.state
            )
        if quote.state != QuoteState.FIRM:
            raise TrollieError(
                ErrorCode.INVALID_STATE_TRANSITION,
                "quote is not awaiting approval",
                state=quote.state,
            )
        if recompute_hash(quote) != quote.quote_hash:
            raise TrollieError(ErrorCode.REAPPROVAL_REQUIRED, "quote integrity check failed")
        return quote.quote_hash, quote.expires_at

    def on_approved(self, session: Session, subject_id: uuid.UUID, approval: Approval) -> None:
        quote = session.get(Quote, subject_id)
        quote.state = QuoteState.APPROVED
        quote.state_version += 1
