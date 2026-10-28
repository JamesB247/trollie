"""Explicit wiring of pluggable components, called once at startup and in tests."""

from app.approvals.service import SUBJECTS


def register_all() -> None:
    from app.quotes.approval_subject import QuoteSubject

    SUBJECTS.setdefault("quote", QuoteSubject())
