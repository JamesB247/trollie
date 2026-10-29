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

## Round 2, 29 October 2026: catalogue scale, scams, stolen money, hijacked agents

```bash
uv run python -m scripts.crowd.run --spawn-server --users 60 --minutes 20 --market large
```

**Market** (`app/simulators/bigmarket.py`, I-043): about 63 000 generated products.
Ubuntu Hypermarket carries 50 000 lines with a slow, flaky integration (2.5 s average, 15%
of calls 9 s, 6 s timeout). Zest Express carries 20 000, answers instantly, and its
couriers are often late. Fairbasket carries 18 000 and behaves well. Kaya Living sells
furniture and appliances: new, legitimate, multi-day delivery. BargainBox Direct is the
scam: it got past onboarding with forged documents, sells about 750 popular lines 25% under
market, accepts every order and never hands anything to a courier. A 20-minute run is one
compressed shopping day. Shoppers arrive in sessions on a South African day curve (lunch
bump, evening peak); fraudsters and attackers keep night hours.

**New actors**: fraudsters load money stolen from someone else's bank account, buy TVs and
phones, and try to withdraw before the bank recalls it. Thieves steal a busy parent's
shopping agent mid-day, then push baskets and urgent "approve now" requests at the owner,
try to spend without approval, widen the grant and withdraw. Every shopper whose delivery
window passes with nothing delivered complains ("your bot recommended this store") and
claims the money back.

### Same crowd, before and after the controls (seed 199673325719780)

| | Before | After |
|---|---|---|
| Paid, nothing received after the delivery window | R16 042 | R1 084 (one parcel lost by a courier; fixed after the run) |
| Paid to the scam store / refunded to its customers | R10 226 / R0 | R4 818 / R4 435 |
| Scam store at end of day | trading | suspended |
| Stolen money loaded / spent or withdrawn before recall | R143 678 / R84 829 | R143 678 / R0 |
| Stolen agents / suspended | 2 / 0 | 2 / 2 |
| Owners paying for a thief's basket | 0 | 0 (grant caps held in both runs) |
| Orders placed (honest shoppers) | 80 (58) | 63 (50) |
| Breaches / server errors | 0 / 0 | 0 / 0 |

Controls added (I-044 to I-047): merchant probation with automatic suspension and refunds,
an exposure cap on undelivered money at new merchants, re-checking that a merchant still
trades at firm-up and order time, `not_delivered` claims (only after the window and only if
the goods never reached a courier; Trollie works out the amount), a clearing period for new
top-ups with a wallet restriction after a recall, agent strikes and request rate limits,
and a circuit breaker for stores that keep timing out.

**What it cost honest shoppers**: 21 "money still clearing" refusals and 8 fewer honest
orders on the after day. The clearing period and allowance are a risk decision for the
pilot, not an engineering default.

**Still open**: paying a new merchant before delivery is proven (settlement timing is a D02
provider question); who carries a courier's loss (D05); the hypermarket's slow integration
still fails most stock holds (32% before, 39% after); the circuit breaker only stops
offering it while it is failing, so its coverage is lost then too; search at 63 000
products is literal and roughly 10x slower (p50 92 ms, still fine).
