# Crowd simulation — SIMULATED, NOT REAL MONEY

A stress and abuse test: dozens of synthetic shoppers use Trollie at the same time, at
random moments, through the public API. Some are careful, some are broke, some are confused,
and some are attackers. Faults are injected into the merchant, payment and courier
simulators while they shop. Afterwards an oracle checks the money and state invariants
directly in the database.

It answers **"where does the logic break under messy, concurrent, hostile use?"** It does
**not** answer whether households want Trollie, whether real prices make split baskets
worthwhile, or whether real merchants, banks or couriers behave like the simulators
(DECISIONS.md I-036, I-037).

## Run it

```bash
uv run python -m scripts.crowd.run --spawn-server --users 60 --minutes 8
```

`--spawn-server` creates a fresh `trollie_crowd` database, migrates it, starts a server
with the background worker on, and seeds the market. Results go to `sim_runs/<timestamp>/`:
`REPORT.md`, `summary.json`, `events.jsonl` (every action, what the shopper "said", the
HTTP outcome and a verdict) and `server.log`.

Useful options: `--seed N` replays the same crowd and choices (timing still varies),
`--chaos 0..1` sets how often faults are injected, `--speed 0.3` compresses pauses.

```bash
uv run python -m scripts.crowd.savings --database-url postgresql+psycopg://trollie:trollie@localhost:5432/trollie_crowd
```

Runs the real optimiser on random baskets in every zone and compares one store, up to two
stores, and the "cheapest shelf price anywhere" figure.

### Driving shoppers with Claude models

```bash
uv pip install anthropic
export ANTHROPIC_API_KEY=...
uv run python -m scripts.crowd.run --spawn-server --users 60 --minutes 15 --brain mixed
```

`--brain claude` gives every shopper a model (randomly Haiku 5.5, Sonnet 5.5 or Opus 5.5);
`mixed` gives roughly half. Each model gets a persona and tools that map onto the same
API actions; attackers also get a free-form `/v1` probe. Models act only as outside
customers. Nothing places a model in Trollie's money path. This costs API usage: expect
roughly one model call per shopper action.

## The market (fictional)

`app/simulators/market.py`, seeded by `/v1/dev/seed?market=true`. Six invented chains
modelled on *kinds* of South African retailer, not on any real company. No retailer data
was scraped or copied.

| Chain | Archetype | Branches | Delivery |
|---|---|---|---|
| Zest Express | app-first rapid delivery, premium prices, nearest branch | 7 | ~40 min, R35 |
| Fairbasket Supermarkets | national mid-market, loyalty prices, free delivery over R600 | 7 | ~3 h, R50 |
| Corner Tree Market | owner-run franchise, each branch sets its own prices, R150 minimum | 8 | ~2 h, R40 |
| Thrift Depot | discount staples, narrow range, R200 minimum | 5 | ~6 h, R30 |
| Brickline Hardware | big-box hardware, free delivery over R1 500 | 5 | next day, R150 |
| Yardstick Build | franchise building yard, cheaper cement, township coverage | 5 | next day, R250 |

Ten delivery zones across Gauteng, Western Cape, KwaZulu-Natal and Eastern Cape. A chain
serves a zone from **one** branch (the "nearest store" rule), so a shopper sees one branch per
chain and the optimiser may combine two chains. There are 90 products under invented brands,
with gaps in each branch's range, low and zero stock lines, and promotions. Prices are
hand-set, illustrative levels, not market data.

## The crowd

`scripts/crowd/personas.py`. Each run draws the mix at random from OS entropy (the seed is
printed): always some attackers, some careful shoppers and some broke shoppers; the rest
are regular households, impulsive shoppers, confused low-tech shoppers, DIY builders, stokvel
bulk buyers and busy parents who delegate to an agent. Shoppers ask in English, isiZulu,
Afrikaans or SMS-speak, use everyday and brand-as-category words ("mielie meal", "Jik",
"Omo", "Koo beans"), make typos, hesitate, double-tap, give up and come back.

The outside world (`scripts/crowd/world.py`) delivers bank transfers late, sometimes twice
or with the wrong amount; store staff mark orders ready; couriers collect, deliver or fail;
settlement reports arrive; and random merchant, payment and courier faults are armed.

## How outcomes are judged

Every action gets a verdict: `ok`, `refused` (an attack correctly stopped), `friction` (an
honest shopper blocked: sometimes correct, sometimes a product gap), `BREACH` (a rule
violated), `BUG` (server error) or `SLOW`. After the run, `scripts/crowd/oracle.py` checks:
ledger balance; no order charged above its approval or captured twice; refunds within the
charge and within each store leg; provider and Trollie agreeing on money taken; no negative
wallet or envelope; no wallet holding more than was confirmed into it; merchant stock never
negative or over-held; no stale holds, stuck orders, dead jobs or engaged kill switches; and
one order per approval.

## Results, 29 October 2026

Three runs of 60 stochastic shoppers (8, 8 and 10 minutes; chaos 0.5), 8 746 actions
in all. Each run drew a different crowd. Code was fixed between runs.

### What broke, and what was fixed

| Run | Found | Severity | Fix |
|---|---|---|---|
| 1 | The same missing item could be refunded twice by submitting the claim again with a new idempotency key; one store leg was refunded beyond its value. Only the order-total cap held. | **Money (breach)** | I-038: claims name the line; per-line and per-leg caps across card and wallet refunds |
| 1 | 10³⁰ packs and a 10¹⁹-cent top-up crashed the server (500) | Robustness | I-039: input bounds |
| 1 | A rejected or lost courier booking left a *paid* order "fulfilling" forever; a driver update for it crashed the server | Customer harm | I-042: incident, attention reason, support case; sweep re-looks-up lost bookings; 409 not 500 |
| 1 | A courier failure after collection left a paid order "fulfilling" forever with no owner | Customer harm | I-042: support-owned case with the leg value; status explains it |
| 2 | When shoppers raced for the same courier slot, a paid order's commit crashed on every retry (slot over capacity) and hung in `COMMITTING`; a deadlock between two such orders | **Money held, no goods** | I-040: unwind cleanly (`delivery_capacity_lost`), lock slots in order |
| 2 | With a late payment webhook, the provider had taken R7 038.67 that Trollie still showed as "payment pending"; Trollie never asked | **Money taken, order waiting** | I-041: look up after two quiet minutes |
| 3 | Nothing: no breaches, no server errors, every invariant passed; the slot fix fired twice live | — | — |

Each fix has a regression test (`tests/test_compensation.py`, `tests/test_api.py`).

### What held every time

Across 449 judged attack attempts in 27 techniques: no one read, approved, ordered or funded with
another account's ids; no forged session, webhook or replayed passkey assertion worked;
no smuggled price/payee/"approved" field was accepted; agents could not fund themselves,
broaden their grant, approve, confirm their own preference or spend without a mandate;
double-taps and reused idempotency keys never created a second order or charge; nobody
withdrew more than they had. The ledger balanced in every run, and provider and Trollie
agreed on money taken (except the run-2 late-webhook gap above).

### What honest shoppers hit (product findings, not bugs)

Run 3, 723 friction events among ~2 800 honest actions:

- **Search is literal (187 + 39).** "mielie meal", "Jik", "Omo", "Koo beans", "amaqanda",
  "Ricoffy" find nothing; the catalogue says "Super maize meal", "Bleach", "Washing powder".
  People shop in brand-as-category words, three languages and typos. This is where a
  proposing-only language layer (M6) earns its place: map words to catalogue ids, never prices.
- **185 chat messages had nowhere to go** ("when will my order arrive?", "can I pay cash?",
  "deliver to my mom in Umlazi instead"). There is no conversational channel yet.
- **Wallet before money (185).** Shoppers chose "pay from wallet" while their transfer was
  still pending; correctly refused, but it reads as failure. The UI should say "R… on the way".
- **Lost races for stock (126 reservation failures).** Popular low-stock lines go between
  quote and firm-up. Correct, but the shopper must be offered the next-best basket.
- **Coverage gaps (40 + 9).** Some lists cannot be completed by any two stores in that zone.
- **Abandoned payments.** 23 orders ended in `PAYMENT_PENDING` because the shopper never finished
  the bank step. Holds expire correctly, but the orders never expire: add a checkout timeout.

### Does a two-store split make sense here?

`scripts/crowd/savings.py`, 500 random grocery baskets on a fresh market:

| | One store | Up to two stores |
|---|---|---|
| Basket completely fulfilable | 43% | 77% |
| Cheapest option uses two stores | — | 61% of fulfilable baskets |
| Saving vs best single store | — | median 0%, max 13%; median 2.8% when the split is chosen |

In this fixture the second store mainly buys **completeness**, not savings: delivery fees and
minimums eat most price differences. And the "cheapest shelf price anywhere" figure a
comparison site would show is not achievable once fees, minimums and stock are real. These
numbers come from invented prices and invented range gaps; they show what to measure with
real data, not what the answer is.

### What this does not prove

Real merchant, bank, provider and courier behaviour; real prices and demand; how real people
(or real models) phrase requests; performance at production scale (one process, one
database, 60 users: p95 latency 86-176 ms). The Claude-driven brain is built but was not run
here (no API key in this environment).
