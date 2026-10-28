"""Explicit wiring of pluggable components, called once at startup and in tests."""

from app.approvals.service import SUBJECTS


def register_all() -> None:
    from app.quotes.approval_subject import QuoteSubject
    from app.quotes.service import FUNDING_VALIDATORS
    from app.wallet.grants import MandateSubject
    from app.wallet.service import validate_funding_source

    SUBJECTS.setdefault("quote", QuoteSubject())
    SUBJECTS.setdefault("mandate", MandateSubject())
    FUNDING_VALIDATORS.setdefault("wallet", validate_funding_source)
