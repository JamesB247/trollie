# Trollie — repo seed

Start here: `CLAUDE.md` (sprint scope and rules), then `DECISIONS.md` (adopted decisions and superseded clauses).

- `docs/ENGINEERING_BLUEPRINT.md` — implementation spec (wins on technical matters, except clauses superseded in `DECISIONS.md`)
- `docs/PRD.md` — product requirements v2.2
- `docs/WALLET_AND_SPRINT_DECISIONS_ADDENDUM.md` — wallet scope addendum, adopted with amendments A1–A6
- `DECISIONS.md` — decision log

Current sprint: M0 baseline + M2–M3 synthetic commerce + W1–W3 synthetic wallet. M1 commercial feasibility remains open. No real money, merchants, WhatsApp or LLM calls. All wallet amounts are **SIMULATED — NOT REAL MONEY**.

## Running locally

```bash
docker compose up --build
```

The app serves on http://localhost:8000 (`/healthz`). Use `localhost`, not `127.0.0.1`, so passkeys work.

Without Docker (needs Postgres 16 with a `trollie` role and `trollie`/`trollie_test` databases):

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --port 8000
uv run pytest
```
