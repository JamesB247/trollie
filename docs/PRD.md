# Trollie — Product Requirements Document (v2.1, 28 October 2026)

> Product baseline. The separate **Engineering Review and Implementation Blueprint (2026-10-28)** (`docs/ENGINEERING_BLUEPRINT.md`) is the implementation baseline and takes precedence on anything technical. The opening "PoC Architecture" section is historical and non-normative.

---

# Part 0 — Historical: original PoC architecture (non-normative)

*This section is the original synthetic-merchant demo concept (Stage A reference). It does not authorise a live wallet. The authoritative pilot scope is Part 1 onward, as amended by the change log.*

## Goal
Demo a South African agentic shopping marketplace: users fund a wallet, their AI agent compares prices across connected retailers, builds the cheapest basket, gets approval, and pays. Use the demo to sign up retailers and early users.

## Demo scenario
"Do my monthly groceries under R2,000." The agent takes the list, queries every retailer, builds the cheapest basket (single store or split), shows the total and savings, asks for approval, pays from the wallet, and returns order confirmations.

## Components
1. **Retailer connectors (mock):** three or four fake retailers, each exposed as an MCP server or REST API; tools: search_products, get_price, check_stock, get_delivery_fee, place_order; catalogue seeded with realistic names and approximate prices.
2. **Shopping agent:** LLM (Claude) with tool access; parse list, normalise products, query retailers, optimise basket, present options; respects brands, budget, preferred stores, substitutions.
3. **Wallet and policy engine:** sandbox ledger; per-agent limits, merchant allow-list, caps; human approval above a threshold.
4. **Approval and notifications:** web or WhatsApp-style approval with Approve / Edit / Cancel.
5. **Audit and security layer:** every agent action logged; prompt-injection defences; signed orders, idempotency keys, anomaly alerts.

## Original build plan (1–2 weeks)
Days 1–2 mock catalogues; 3–5 agent + optimiser; 6–7 sandbox wallet and approvals; 8–10 audit log, UI, demo video.

## Name ideas (resolved: Trollie)
Thenga, Bhasikidi, Trolli, Spaza Agent, Shopa.

---

# Part 1 — Product Requirements (PRD) — Trollie (trollie.ai)

## Product name
**Trollie** (trollie.ai). Also register trolley.co.za and similar spellings and redirect. Run a trademark check (a Trolley payouts fintech exists internationally).

## Positioning
A South African agentic shopping service. A person talks to their personal agent (built-in on WhatsApp/web, or their own Claude/ChatGPT agent via MCP); the agent builds a complete, fulfilable basket from participating South African stores, compares the eligible delivered total, and coordinates payment and delivery through approved partners with the user's explicit approval. A prefunded rand wallet with envelopes is a later, separately gated product. Trollie augments local retailers; it does not compete with crypto agent wallets.

## Core principle
**The agent never holds money or card details.** It holds a scoped, revocable permission to request purchases. Trollie's servers enforce all spending rules and execute payment.

## v2 — decisions adopted from the 28 Oct 2026 PRD review

**Headline change:** the wallet is no longer the Phase 1 product. Phase 1 is a constrained shopping agent with explicit per-order approval and pay-per-order through an approved provider. Stored value, envelopes, mandates, cards and QR are gated expansions.

### Contradictions resolved
- **Auto-approve under R300 vs "always show the basket":** explicit approval for every live-pilot purchase. Standing mandates (items/categories, merchants, period, cumulative cap, address, stop conditions) are a separate later feature; per-transaction caps alone are defeated by R299 splitting, so mandates enforce aggregate and velocity limits atomically.
- **"Everything cancellable" vs irrevocable rails (PayShap has no reversal):** one message *starts* the applicable process; the UI shows whether the order was stopped, cancellation is pending with the merchant, or a refund is owed.
- **"No cash-out" vs users getting money back:** no peer transfers in v1, but controlled redemption to a verified source/approved bank destination is required. Merchant collusion, resale and refund diversion remain abuse routes needing their own controls.
- **"Live within an hour" vs verification:** merchant states are draft → integration tested → verification pending → payment enabled → delivery ready.
- **"Exact amount" card + buffer:** approval states an explicit maximum total and permitted variance; beyond that needs reapproval.
- **Pseudonymised prompts vs voice notes with names/addresses:** allowlisted context assembly with redaction; residual exposure acknowledged; users told not to send ID documents in chat.
- **Household sharing vs one-budget tokens:** one adult account owner per pilot budget; delegated roles (payer, shopper, approver, recipient, admin) later with explicit permissions.
- **Cheapest-option delivery vs perishables:** suitability and SLA first, cost second.

### Claims removed or reworded
- "Sit on a gateway to avoid a licence" → approved sponsor/provider model; Trollie's own activities still need written classification (TPPP / system operator / technical provider) before real money.
- "Holding customer funds is e-money" → classify stored-value, deposit-taking and payment-service status against the final funds flow.
- "A third of South Africans use ChatGPT" → removed; not a representative estimate.
- "Grocify is compare-only" → it already optimises whole baskets, splits with fuel cost, scans barcodes and alerts across 7–9 retailers.
- "All global players are US-only/English-only" → Gemini shopping launched in India in English and Hindi; forecasts are agent-routed GMV, not SA TAM.
- "Database dump is useless" / "zero retention" / "all data in Cape Town" → reworded in security and privacy sections.
- "Memory is a moat" → memory is a trust feature with export; defensible assets are merchant relationships, SKU mappings, stock/price freshness, fulfilment quality and fraud controls.
- "Walking is free and instant" → a local research question, not an assumption.
- "5,000 orders before pitching chains" → an evidence package (repeat rate, complete-basket rate, defects, unsubsidised contribution, support effort).

## One-line summary
Trollie helps you build and approve a complete grocery basket from participating stores, compares the eligible total delivered cost, and coordinates payment and fulfilment through approved partners. You see the items, substitutions, destination, fees and delivery window before committing.

## Phasing
- **Stage A — Controlled demonstration (now, ~10 working days):** three or four clearly fictional merchants with labelled synthetic prices and stock; deterministic basket optimiser; immutable quotes; explicit approval bound to the quote; simulated ledger with double-entry invariants; demonstrated rejection of prohibited actions (payee change, budget expansion, address change, quote substitution, budget splitting). No real deposits, live cards, real retailer logos or implied partnerships. This is the funding demo.
- **Stage B — Assisted shopping validation (8–12 weeks, one locality):** authorised merchant data; human-assisted quotes and fulfilment; 10–15 household usability sessions on concrete tasks; merchant interviews observing pick/pack/reconcile; measured catalogue coverage.
- **Stage C — Bounded live commerce pilot:** pay-per-order through one approved payment provider (no stored balance); small set of verified, operational merchants; explicit approval for every purchase; packaged ambient goods only (no alcohol, tobacco, medicines or temperature-sensitive items); staffed support; daily reconciliation; bounded maximum loss. Legal/partner gates closed before launch.
- **Stage D — Gated expansion (each capability has its own gate):** prefunded wallet and real envelopes; standing mandates/auto-approve; external third-party agents; virtual cards; Retailer Connect API; mid-size and large-chain partnerships; QR in-person payments; township collection-point model; B2B replenishment; credit (separate regulated product).

## User experience
1. **Start shopping without onboarding:** send a list, photo or voice note and get quoted options before any identity or payment step. Comparison-only use needs no financial onboarding.
2. **Onboarding (when the user wants to buy):** secure mobile-web session (never ID or bank details in WhatsApp chat). Risk-based CDD via a verification provider with accessible alternatives and manual review; passkey (WebAuthn) set up. Measure onboarding time for easy, exception and manual-review cases separately.
3. **Budgets (planning, not custody):** a notional monthly budget tracked against orders. Real reserved funds come only with the gated wallet.
4. **Connect your own agent (later gate):** MCP server as an OAuth resource server (pinned MCP version, PKCE, strict redirect validation, scoped grants). External agents get search, quote and request-to-purchase only, never a payment tool. The consent screen names the client and lists separately what it can read and request.
5. **Shopping:** the agent asks only for missing information, queries participating stores, and the deterministic optimiser returns complete quoted options with coverage, freshness and delivery shown. Uncertain matches are flagged, never silently substituted.
6. **Approval:** a Trollie-controlled approval page rendered from authoritative server data shows contracting seller per sub-order, items, quantities, substitution rules, destination, window, fees and maximum total. A single-use challenge is bound to that immutable quote; the passkey assertion is accepted only for that record. Any material change invalidates approval.
7. **Payment:** pay-per-order through the approved provider's flow (3DS challenge handled by the user, never intercepted). Status: submitted / pending / captured / failed / unknown; unknown is reconciled before any retry.
8. **After:** durable receipt and status page, merchant acceptance and fulfilment states, cancellation/refund request paths with real status, and a human support route.

## Built-in Trollie agent (mass market)
- WhatsApp-first for entry and notifications (text and voice notes); mobile web for onboarding and approval; web access always available so a WhatsApp suspension never cuts users off from receipts, support or refunds.
- Multilingual with per-language measurement of item/quantity/constraint extraction; read back money, quantities and locked items before committing.
- Learns usual brands and lists as user-confirmed structured facts with provenance; a cadence is a suggestion, never a mandate.
- **Channel gate:** dated assessment of Trollie's marketplace/financial use under current WhatsApp Business terms; approved templates and opt-in; human escalation; alcohol and OTC medicines excluded (South Africa not in the allowed lists); budget for non-zero per-message cost after the October 2026 pricing change.
- **Pricing tiers (hypotheses):** Free (limited orders, funded by commission); ~R29 and ~R49 tiers with a plain-language fair-use allowance instead of "unlimited". VAT-inclusive: R29 nets R25.22, R49 nets R42.61 before processing. CPA s14 applies to fixed-term subscriptions; subscription, mandate, order and wallet cancellations are four distinct requests.

## Scope guardrail
The Trollie agent is **shopping-only**. It refuses unrelated tasks (coding, general chat). This limits attack surface and cost; it does **not** by itself establish WhatsApp policy compliance — channel eligibility is a dated gate (D09) with the full Business Platform terms and current rate card on file.

## Future purchases (remember-and-buy)
Three request types:
- **Scheduled buys:** "Replace my milk on Friday" → dated task, purchased on the day.
- **Event buys:** "Cake and flowers for Julie's birthday on X" → shopped 1–2 days ahead, user approves the choice.
- **Open searches:** "Find me curtains" → agent asks for size, colour, budget; presents options; user picks.

Mechanics:
- **Envelopes (Stage D):** until the wallet gate clears, an envelope is a planning budget, not reserved money. Later: distinguish notional budget, internal reservation, provider authorisation hold and settlement; never reserve scarce household cash months ahead.
- **Rhythm learning:** cadence produces a confidence-qualified suggestion; purchase requires confirmation until a versioned standing mandate exists.
- **Scheduled mandates:** timezone (Africa/Johannesburg), recurrence, next run, end date, cumulative cap, constraints, lead times, version; revalidate funds, merchant, address and constraints at execution; revocation stops queued jobs; a late job pauses rather than executes.
- **Heads-up:** a notification is not consent; delivery/read status and silence never imply approval.
- Gift recipients: a date and approved destination, not a permanent third-party profile.

## Virtual cards
- **Deferred to Stage D.** Arbitrary-store browser checkout is out of the first live pilot.
- Design intent: single-use, merchant-locked virtual cards with an approved maximum. To settle with an issuer: which event consumes "single use", late capture, partial shipments, variable-weight adjustments, refund routing after deactivation, and what "merchant lock" means (merchant ID, group, MCC, descriptor, first-use binding).
- A virtual card gives neither exact-basket control nor PCI exemption: virtual PANs are in scope, CVV cannot be retained, and any Trollie checkout service entering card data needs formal scope review. Prefer partner-managed tokenisation.
- 3DS challenges are handed to the user; never intercepted or bypassed.
- **Issuer prospects (none validated for a SA rand consumer programme):** Onafriq (BIN sponsorship, multi-currency, single-use virtual Visa); Scale (getscale.africa — "Liners" was a directory, not the provider); Sudo Africa and Bridgecard publicly document Nigerian NGN/USD products only; Investec Programmable Banking is a founder demo within account terms. Send every candidate the same funds-flow diagram and require written answers before marking "supported". Track Visa Trusted Agent Protocol and Mastercard Agent Pay.

## QR in-person payments (spaza / informal retail) — later phase
- User shows a dynamic QR; the shop scans with its phone and is paid.
- Dynamic, single-use QR tied to the amount, expiring in ~60 seconds; shop needs only the Trollie merchant app or WhatsApp.
- Can run over WhatsApp at Trollie-registered shops: Trollie signs the payload; the shop reads authoritative status from Trollie's service (a WhatsApp message is a notification, not settlement proof). Specify presentation mode, who enters the amount, verified payee display, replay protection, duplicate scans, refund linkage, offline behaviour. Interoperability beyond registered shops depends on the SARB QR+ pilot (Q1 2027), scheme access and merchant acceptance — not promised.

## Store side

### Tiers
1. **Small shops:** Shopify / WooCommerce connector (test catalogue sync, variants, stock by location, tax-inclusive prices, order acceptance, idempotent webhooks, cancellations, refunds, reconciliation). No website: assisted WhatsApp catalogue with confirmed catalogue and accepted order states. Onboarding promise split into draft catalogue, integration tested, verification complete, payment enabled, delivery ready.
2. **Mid-size retailers (Stage D):** Retailer Connect API — one stable internal commerce contract with adapters; MCP is an optional facade, not a merchant requirement.
3. **Large chains (Shoprite/Checkers Sixty60 + Pixie, Pick n Pay asap! + Penny):** partnership track after the evidence package exists.

### Verification and risk
- **Legal-form-aware verification:** sole proprietors and informal traders have no CIPC number or directors. Verify the actual proprietor or entity, authority to transact, beneficial owners where applicable, bank-account entitlement and operating permissions (municipal trading permit; R638 food-premises certificate where food is handled). "Informal" or "foreign-owned" is not a legality test.
- New stores volume-capped until a trust history builds; payout-destination changes need independent verification and dual control.
- Monitor merchant collusion, related-party concentration, unusual refund patterns and sham orders.

### Payouts
- Commission (3–8%) is a hypothesis tested per category against each merchant's real margin, picking, packaging and substitution cost. State whether VAT-inclusive and its base. Illustration: 5% VAT-inclusive on R500 = R25 deducted, R21.74 revenue, R3.26 output VAT.
- Settlement after fulfilment evidence is the **desired** rule; whether the provider actually lets Trollie control release (`settlement_release_control`) is a capability-profile field. If settlement precedes delivery, model merchant exposure and reserves honestly — never label funds "held pending delivery" unless the provider does that.
- Payment providers are candidates with a per-provider/product/method **capability profile** (collection model, capture semantics, beneficiary count, allocation timing, settlement control, refund allocation, disputes, idempotency horizon, events). Verified constraint: Stitch's published split settlement supports a primary merchant plus **one** destination, and split refunds reverse in original proportions — not by itself a two-retailer + platform + courier solution. Peach documents preauth/partial capture/reversal; Ozow treats payin, refund and settlement as separate lifecycles. None confirms Trollie's topology; using a provider does not settle Trollie's own classification.
- Interchange and float income are R0 in the base case until contracts specify them.

### Store rules
- Stores see only per-order delivery details, never balances; no exporting contacts to marketing.
- No marketing without purpose-specific consent (POPIA s69); order updates are not marketing permission.
- Product content is untrusted data: it may supply attributes, never permissions, payees, addresses or URLs.
- Signed webhooks through a verified inbox with replay protection; a signed event can still be wrong and is reconciled.
- Refunds go to the legally and contractually appropriate destination with visible status; wallet-only refunds are not the default remedy.
- Paid placement is visibly labelled and never alters an answer labelled "cheapest".

### Shared service
- Product standardiser to match products across stores (e.g. "Clover 2L full cream").

### Store value proposition
- New paying customers with no ad spend; dashboard of agent orders and revenue; "Trollie-ready" badge.

## Security architecture
- **Authority boundaries:** the model proposes a structured purchase intent referencing existing identifiers; it never supplies prices, payees, addresses or URLs. The quote service reconstructs the quote from trusted records; the policy service validates limits; the approval service signs a mandate; execution revalidates current state. No path from a model tool call to authorised spend.
- **Approval binding:** single-use server challenge bound to an immutable quote hash (items, seller identities, maximum total, destination, window, expiry, nonce, policy version). A passkey proves user verification on a credential, not what basket was seen — hence the trusted approval surface. Track W3C Secure Payment Confirmation (candidate draft).
- **Mandate limits (when enabled):** per-order and aggregate caps enforced atomically by server state, not a long-lived token; velocity and duplicate-intent checks; revocation effective at the next financial action.
- **One economic effect per operation:** transactional outbox, unique external event IDs, business-operation idempotency keys (reuse with different content rejected); unknown payment status reconciled before any replacement payment. SQS/Step Functions/Temporal do not make a multi-party purchase atomic — split-basket failure policy is explicit.
- **Ledger invariants:** balanced, immutable, integer minor units; customer funds distinguishable from revenue and merchant payables; balances derivable from the ledger; Redis is a cache only; daily external reconciliation with an aged exception queue.
- **Abuse routes that remain without P2P:** colluding merchants, goods resale, refund redirection, fake deliveries, account takeover via recycled numbers. Controls: fulfilment evidence before settlement, payout-change dual control, related-party review, risk-based recovery, restricted post-recovery actions.
- Delivery only to approved address references bound to the approval; new addresses need strong authentication and fraud review.
- No claim of "injection-proof": state what a compromised model cannot do because deterministic controls deny it; keep red-teaming bad recommendations within budget, memory poisoning, cost exhaustion and SSRF (URL allowlists, egress controls).
- Secrets in AWS KMS / Secrets Manager; isolated checkout adapter; redaction of logs, traces, screenshots and support tools; kill switch that stops new financial actions while reconciliation, refunds and support continue.
- **SARB NPS Directive 1/2024 (cyber resilience)** applies directly to TPPPs/system operators: owned control register, annual review, third-party assessments, quarterly recovery testing, recovery-time classification confirmed.

## Privacy (POPIA)
- Personal-information impact assessment and data-processing register first, then boundaries and notices.
- Grocery data can reveal special personal information (health, religion, pregnancy, children). Store user-confirmed constraints, not inferred profiles; never use them for advertising or pricing. Section 71 safeguards and a human appeal route for fraud freezes and refusals.
- Cross-border map by service (WhatsApp, model provider, transcription, Cloudflare, KYC vendor, couriers, backups, support) with a documented s72 basis and operator contracts.
- Record-class retention: short transcript retention coexists with durable consent/quote/approval evidence, FICA (5+ years from trigger) and SARS requirements; "delete everything" is not promised. SARS authorisation needed if electronic tax records sit offshore (TAA s30(2)).
- Information Officer registered; incident matrix with every clock (POPIA s22 "as soon as reasonably possible", partner/processor notices, NPSD/PA/FSCA where applicable); do not cite Cybercrimes Act s54 as commenced.
- Memory page with fact, provenance, confidence, purpose, edit/delete and export; deletion propagated to indexes, caches and backups.

## Infrastructure and data residency
- **AWS af-south-1 (Cape Town, 3 AZs)** for core storage. Core storage location is not end-to-end local processing: model inference (Anthropic lists global/US inference; Bedrock cross-region profiles can leave the region), WhatsApp, KYC vendors, telemetry and support may process elsewhere — keep a service-by-service processing map.
- Cloudflare at the edge: Regional Services for South Africa is an enterprise Data Localization add-on; a default proxy does not give local TLS termination or log storage.
- Cloud permitted under a risk-based approach; no physical servers required. Partner contracts flow down audit/regulator access, location, subprocessor, incident, continuity and exit terms. Exit plan with realistic volumes, key custody and reduced-service mode.

## Regulatory landscape (verify with counsel)
- **Payments reform (moving target):** PASA functions moved to SARB (11 Aug 2026) and PayInc (2 Sep 2026); Prudential Communication 10/2026 (20 May 2026) consulted on a non-bank exemption/authorisation framework; SARB Governor (20 Oct 2026) targets publication by end-November 2026 and a QR+ pilot in Q1 2027. Owner assigned to track the final instrument.
- **Classification:** Directive 1/2007 (payments to third persons) and TPPP/system-operator registration may apply to Trollie's own activity regardless of provider; Directive 2/2024 governs third-party EFT initiation (no bank credentials in chat or model context). Written classification against the final funds flow.
- **Customer funds (Stage D):** NPS 01/2009 e-money position paper; CODI excludes e-money from deposit insurance; safeguarding, insolvency, redemption, interest entitlement and wind-down policy before the first top-up.
- **CRS/FATCA:** Notice R.6886 (effective 1 Mar 2026) brings specified electronic money into scope (USD10,000 90-day-average exclusion); a payment facilitator differs from an account maintainer. Written classification before any stored value.
- **FICA:** classify the entity (Schedule 1), register within 90 days of becoming accountable (pilot gate: before activation), RMCP, risk-based CDD, sanctions screening, monitoring, reporting, records; GN7B (3 Aug 2026) replaces GN7/7A; PCC 118A is a draft.
- **Cloud:** PA D3/2018 and G5/2018 apply to banks (flow-down via partner); Joint Communication 2/2025 is best practice; a Joint Standard is planned (FSCA plan: 2027/28 consultation); NPS Directive 1/2024 is the binding cyber instrument.
- **Consumer:** ECTA s20 (electronic agents, error correction), ss43–46 (supplier disclosure, review/withdraw; s42 excludes everyday food from cooling-off); CPA quality/remedies, s63–65 prepaid value, s14 subscriptions. Approval screen names the contracting retailer per sub-order.
- **Merchants/food:** municipal trading permits; R638 food-premises certificate; Competition Commission OIPMI findings on ranking transparency; catalogue content rights contracted.
- **Credit (later):** NCA registration threshold is nil; stock credit is a separate regulated product.
- **Tax:** VAT 15%; thresholds R2.3m compulsory / R120k voluntary administered from 1 Apr 2026 pending B34—2026; zero-rated foodstuffs classified in the catalogue service, never by the LLM; principal/agent role per supply with counsel; tax invoices and credit notes per seller; versioned tax-rule table.
- **AI policy:** draft National AI Policy withdrawn (June 2026); no AI licence exists, everything above still applies. IFWG sandbox can resolve a defined perimeter question, confers no approval.
- Legal review gates architecture, contracts, prototype claims and every money-moving release.

## Technical architecture (detailed)

### Agent layer
- Modular monolith first (FastAPI + Postgres) with separate service identities: channel adapters, shopping session, intent extraction, product/offer service, deterministic optimiser, quote/purchase-intent service, policy service, approval service, payment adapter, order/fulfilment orchestration, reconciliation, support console, audit store.
- The LLM proposes and explains; it never decides funds, approval, supplier authorisation or payment retries. Claude is the candidate model, benchmarked on task success, hard-constraint errors, language extraction, latency and cost per completed and abandoned session (repeated trials on persisted outcomes).
- **Product data is a system of record:** canonical product (GTIN where available, brand, variant, declared quantity, pack, perishable flag) separate from offers (store, VAT-inclusive price, tax code, promotion rules, stock status/confidence, freshness, slots, minimums). Matching: verified GTIN → verified mapping → exact attributes with review → user-confirmed similarity.
- **Optimiser:** integer programming / enumeration over allowed store combinations; objective = total the household pays (items, delivery per leg, fees, tax, valid discounts, tip); max two stores initially; outputs one-store, lowest-delivered-total and fewer-deliveries options; names the blocking constraint instead of shrinking quantities. Savings shown against a reproducible baseline; quoted vs realised tracked separately.
- Each retailer behind one internal commerce contract; MCP facade optional.

### Backend
- FastAPI on AWS Cape Town (af-south-1).
- Postgres on RDS with double-entry ledger.
- One durable-workflow approach (chosen after the state machines are defined) for scheduled/future purchases that must survive restarts.
- WhatsApp Business Cloud API; webhooks behind Cloudflare.

### Frontend
- Mobile web for onboarding, approval and status is the pilot scope; Next.js for web, merchant portal and operations console. A native app (React Native) only after a demonstrated need.
- Passkeys (WebAuthn) for approvals, with PIN-based user verification supported — Face ID is not the only path.

### Privacy-by-design (critical)
- **Structured memory:** user-confirmed facts with provenance, confidence, purpose and expiry; short transcript retention alongside a bounded authorisation record.
- **Envelope encryption, not a KMS key per user:** customer-managed KMS keys cost ~US$1/key/month (10,000 users ≈ US$10k/month base). Use a small set of controlled KMS keys with per-user data keys, tenant-bound access checks (encryption context is non-secret and logged — no sensitive values in it), crypto-erasure and legal-hold design. A service with broad decrypt rights is still a single point of compromise; isolation, least privilege and audit remain necessary.
- **Allowlisted context assembly:** pseudonymous task context with only needed fields; redaction of free text; delivery details added by the checkout service after the model is done.
- **Provider terms, not slogans:** document the exact Anthropic organisation, API, model, feature, ZDR eligibility, geography and subprocessors; a user's own Claude/ChatGPT account is outside Trollie's agreement.
- **User memory page:** view, correct, delete, export; deletion propagated to indexes, caches and backups.
- **Real isolation:** separate service accounts, restricted joins, purpose-specific APIs, separate backup policies, narrow support access. Product search cannot read KYC; couriers get one order's delivery details.

## Monetisation
- Retailer commission per completed, non-refunded order (contractual basis and VAT treatment per merchant).
- Subscription tiers with fair-use allowance (R29 → R25.22 net; R49 → R42.61 net).
- Base case R0 for interchange, float/interest and breakage until contracts and legal analysis establish entitlement.
- Later, separately gated: QR merchant fee; B2B wholesaler commission/listing; delivery margin; credit margin with a licensed lender.

## Go-to-market
1. **One locality first:** a single dense Gauteng area; count authorised complete-basket coverage, viable merchants and delivery polygons, not logos. Sign up merchants in person: "no upfront listing charge, disclosed fee on completed orders".
2. **Grow via WhatsApp and referrals, costed honestly:** R50-each referral is R100 of issued incentive; with R20×3 delivery subsidy that is R160 before field staff, influencers and onboarding support. CAC = total incremental acquisition spend ÷ activated households (completed, non-refunded order); report subsidised and unsubsidised cohorts separately.
3. **Evidence package for chains and investors:** repeat rate, complete-basket rate, realised net savings, fulfilment defects, support minutes, contribution per order including non-converting sessions, household concentration and subsidy.

### Investor questions to pre-empt
- **Unit economics:** show the contribution equation with real partner fees. Break-even goods value under the illustrative model is ~R628 at 5% commission.
- **Why we beat Penny/Pixie/Grocify:** Grocify optimises but does not buy; Penny and Pixie buy only within one retailer; Trollie completes cross-store purchases with explicit authority and fulfilment. A hypothesis to prove with repeat cohorts.
- **Why now:** FinScope 2025: 89% bank-account ownership but ~13m people use accounts only to withdraw; Trade Intelligence: shoppers use ~4 grocery stores and only 5% never look for deals; PayShap and the pending non-bank framework; card-scheme agent programmes. Quote sources with dates and populations.
- **Defensibility:** verified merchant relationships, SKU mappings, stock/price freshness, fulfilment quality and fraud controls. Memory is a trust feature with export, not lock-in.

## Delivery
**Principle:** no fleet. The router first rejects unsuitable routes (goods class, cold chain, weight, service area, readiness, SLA, liability), then compares acceptable ones on cost. Pilot scope: packaged ambient goods only.

### Delivery router
1. **Shop delivers itself** (declared and verified: polygon, cut-offs, capacity, proof of delivery, insurance, liability).
2. **Same-hour metro** → Picup (API documented; confirm grocery/temperature service, geography, fees, production credentials). Uber Direct: obtain a SA commercial offer. Bolt Send: no commercial API/SLA verified — excluded. "Pick & Drop": entity unidentified — removed.
3. **Next-day / bulky** → The Courier Guy (perishable exclusions); PUDO lockers (no refrigeration, rate unverified); Bob Go as aggregator with service-specific exclusions.
4. **Collection** fallback.

- Pingo is wholly owned by Shoprite (FY2026) → strategic conversation later.
- Pilot: Picup + shop-delivers-itself + collection only.
- Merchant workflow: acknowledge → confirm stock → accept deadline → pick/substitute per rules → ready signal → reconcile actual basket. A delayed WhatsApp reply is not confirmed stock.
- Failure policies for each case (reject after payment, late store, courier early, address not found, recipient absent, wrong/missing item, disputed delivery) with owner, evidence, remedy and clock.
- Customer sees merchandise, fees, delivery per leg, tip and maximum total; a single "one fee" is a priced promise and any shortfall is a subsidy in contribution.

### Delivery address intelligence
- Users keep named addresses (Home, Work, Mom's place, etc.), each verified.
- Every request resolves a destination: inferred from context and **always confirmed** in the approval summary ("Delivering to Home, 14:00–16:00 — OK?").
- Delivery only to verified address versions; adding a new one needs strong authentication.

## Partner directory (integration candidates)
- **Card issuing (prospects, none validated for SA rand consumers):** Onafriq, Scale (getscale.africa), Sudo Africa (NGN), Bridgecard (NGN/USD), Investec Programmable Banking (demo only).
- **Payments (role-by-role diligence):** Stitch, Ozow, Peach Payments, Yoco. Public benchmarks: Ozow 1.5% min R1 pay-by-bank/PayShap, R3 payouts/refunds; Stitch Express 2.95% cards, 2% Capitec Pay, R2/R10 payouts ex VAT; Peach Growth 2.95% + R1.50 ex VAT. Not quotes.
- **KYC (separate counterparties):** VerifyID, VerifyNow, Smile ID, iiDENTIFii — RFI on documents/populations, liveness, false accept/reject, manual review, KYB, data location, retry pricing.
- **Delivery:** Picup, The Courier Guy, PUDO, Bob Go; Uber Direct pending SA terms; Pingo later.
- **Store platforms:** Shopify, WooCommerce, Yoco Online, WhatsApp catalogues; Takealot sellers later.
- **Messaging:** WhatsApp Business Cloud API via BSP or direct, with dated policy assessment.
- **AI:** Anthropic Claude under documented retention terms; smaller models for routine tasks.

## Merchant self-service onboarding
- Register via a secure web onboarding link (reachable from WhatsApp; never ID or bank details in chat). Legal-form-aware: company → CIPC + directors + beneficial owners; sole proprietor → proprietor ID + proof of trading; both → bank-account ownership, location, operating permissions, delivery options.
- Catalogue by Shopify/WooCommerce connect, CSV, shelf-photo extraction or WhatsApp import — all produce a **draft** with provenance and uncertainty flags that the merchant confirms before anything is orderable.
- Merchant states: draft → integration tested → verification pending → payment enabled → suspended/exited.
- Signed merchant checklist: terms, commission and VAT treatment, refunds, data use, hours, out-of-stock policy, prohibited categories, SLAs, payout-change control, emergency contact.
- Dashboard: orders, revenue, settlement statement (gross, tax, commission, delivery, refunds, reserves, net), stock alerts, payouts.
- Volume-capped until a trust history builds.

## User discovery
- Location-aware: shops within the user's vicinity, what they sell, delivery options and ratings. Separate "nearby" from "serviceable".
- Agent prefers nearby shops for perishables and same-day items.

## UX/UI principles (priority over backend)
UX quality is the make-or-break; users will not adopt a service they do not trust or understand.
- **Conversation-first:** WhatsApp text and voice notes; acknowledgement in under 3 seconds (p50/p95), honest progress and timeouts for multi-store quotes — a typing indicator is not a fulfilment promise.
- **Always show the authoritative basket before paying:** seller per sub-order, items, quantities, substitution rules, price, delivery per leg, fees, maximum total, destination, window — one trusted page, one passkey tap.
- **Trust signals everywhere:** every charge explained; `bank hold`, `charged`, `refund requested`, `refund confirmed` shown separately.
- **Zero-surprise rule:** no purchase without approval; one message starts cancellation and the UI states whether it stopped, is pending with the merchant, or a refund is owed.
- **Budget shortfall handled openly:** "Your full list is R2,260 delivered. To reach R2,000, choose items to postpone or approve these alternatives" — never silently shrink quantities or drop locked items. Market "this list under R2,000", not "all your monthly groceries".
- **Progressive depth:** WhatsApp for simple flows; mobile web for onboarding/approval; a native app only after a demonstrated need.
- **Accessibility and devices:** low-end Android, intermittent connectivity, shared phones, screen readers, text scaling; account recovery (lost phone, recycled SIM, lost passkey) designed as a payment-security flow with no silent SMS bypass.
- **Multilingual:** per-language measurement of items, quantities, money and constraints; read-back before commit.
- **Onboarding:** measured for pass-first-time, exception and manual-review cases; report median and tail, not a single "3 minutes".
- **Design process:** clickable prototype tested on concrete tasks (bring a real list/receipt) with 10–15 households across languages, phones and banking access, including in-store loyalists and digital-checkout abandoners; then a 50–100 household live cohort with pre-defined metrics.

## Product preferences (hard rules)
- Preferences are rules enforced by the optimiser. **Locked:** only the exact confirmed item or a user-defined equivalent set; out of stock → ask. **Preferred:** pre-approved fallbacks with conditions, or confirm each switch. **Flexible:** cheapest within category, unit, quantity, budget, dietary and safety constraints. A fallback list is not permission to buy anything on it forever.
- **Capture by photo or barcode:** barcode validated (format, check digit) and identity confirmed via GS1/merchant mapping; a photo may not distinguish fat content, size or multipack — ask before locking. Requested units stay separate from purchasable packs (2 litres does not authorise a 6-litre pack).
- **Fallback chain:** second and third choices captured at save time, stored per item with the conditions under which each is allowed.
- All preferences, fallbacks and provenance viewable and editable on the memory page.

## Minimum order and delivery economics
- **Illustrative contribution model** (assumptions, replace with signed fees): one merchant; R50 delivery passed through at zero margin; 1.5% net payment cost on goods + delivery; R3 settlement to merchant + R3 to courier; R3 AI/messaging; R5 support; 0.5% loss allowance; no subscription, subsidy, interchange or float. Commission VAT-inclusive. Equation at commission r: **CM = (r/1.15 − 0.020)·G − 14.75**.
- Results at **5%**: R150 ≈ −R11.23, R500 ≈ −R3.01, R1,000 ≈ +R8.73, R2,000 ≈ +R32.21. With an extra R35 subsidy: −R46.23 / −R38.01 / −R26.27 / **−R2.79**. (An earlier "≈ R25" figure did not reconcile with these assumptions and is withdrawn.)
- Break-even goods value: ≈ **R628 at 5%**, ≈ R2,423 at 3%, ≈ R298 at 8%.
- Two-store sensitivity (R2,000, 5%, R3 per paid beneficiary): one store/one delivery R32.21; two stores/two legs R25.46; two stores/one consolidated courier (R70 invented) R28.91 — before extra picking, waiting, refund and support cost.
- Sensitivities: 1-in-5 session conversion makes AI cost R15 not R3 per order; support R5 → R20 = −R15; each extra 1pt of rail cost ≈ −R5.50 on R550.
- **Soft minimum ~R150** stays as a UX nudge, not an economic floor. Small baskets need batching, merchant-funded delivery, collection or a transparent service fee.
- **Pilot subsidy only:** R20 off delivery for the first three orders, capped, booked as acquisition cost, reported separately.
- Report contribution per order including abandoned sessions, interventions, reversals and losses; LTV on contribution, not GMV × retention.
- Working capital: never fund settlement or refunds from other customers' money. The R500k timing-gap example (500/day × R500 × 2 days) applies only where Trollie funds obligations before incoming settlement; under provider-direct settlement it is smaller. Hold a finance-approved operating/refund reserve.

## Competitive landscape (Oct 2026)

### South Africa
- **Pick n Pay Penny** (Jul 2026): conversational grocery shopping inside asap! — text, voice, photos, recipes, basket building, established fulfilment and loyalty. Single retailer.
- **Checkers Sixty60 / Pixie** (Apr 2026): Shoprite's AI assistant with personalised basket and restock suggestions on a R25.5bn (FY2026) Sixty60 business with wholly-owned Pingo logistics. Include in every comparison.
- **Grocify** (Johannesburg): price comparison and whole-basket optimisation across 7–9 retailers (Checkers, Pick n Pay, Shoprite, Woolworths, Makro, Takealot…), splitting with fuel cost, saved/shared lists, barcode scanning, alerts, loyalty support; company-reported ~20% basket savings. Does not purchase or pay.
- **Retailer delivery subscriptions, Uber Eats, retailer apps:** existing purchase channels that bundle delivery and discounts; Trollie must beat a household's existing benefits.
- **B2B overlap:** Vuleka (wholesale comparison, ordering, WhatsApp, delivery), Yebo Fresh (general-trade ordering and logistics), Kazang and Shop2Shop (merchant payments, supplier payments, stock advances). Interview merchants who have tried them.
- **Hypothesis, not fact:** no local player appears to combine cross-store search, agent connection, completed payment and user-controlled memory. Being first to combine features is not customer value.

### Global
- OpenAI (24 Mar 2026) shifted from standalone Instant Checkout to product discovery and merchant-owned checkout; the lesson is merchant integration and trusted checkout.
- Google UCP (selected merchants; US/CA/AU) and Gemini shopping (India, English and Hindi); Amazon Alexa for Shopping / Buy for Me (US); Perplexity + PayPal Instant Buy (US); Meta Muse with Link checkout and one-time cards (US).
- Protocols: MCP, ACP (beta), UCP, AP2 (v0.2), Visa Trusted Agent Protocol, Mastercard Agent Pay. Internal domain model with adapters; none supplies SA bank access, inventory or fulfilment.
- McKinsey (Oct 2025): US$3–5tn global B2C goods revenue potentially agent-routed by 2030 — a scenario, not SA TAM.
- All built for home-market rails. None address rand payments, PayShap, WhatsApp-first, informal retail or SA compliance. The long tail of merchants is the unsolved problem globally.

**Pitch line:** "Trollie is the purchasing intelligence layer between South African households, independent businesses and retailers: you say what you need, Trollie works out where to buy it, what it should cost and how to get it — and you keep control of payment." Cohort evidence first, market context second.

## Spaza and township strategy (later phase)
**Insight (to be tested):** delivery from a spaza 200 m away is probably low value, but walking is not free for everyone — time, queues, carrying weight, safety, disability and lost trading time are real. Research the actual journeys of a caregiver, an older person and a shop owner before designing. Township sizing comes from a local merchant census and observed buying routes, not national informal-business counts.

### For township users
- **Reach:** bring Makro / Boxer / wholesale prices to the township, delivered to the spaza as a **collection point**. Spaza earns a holding fee and foot traffic — partner, not replaced.
- **Price checking:** "cheapest Ace, maize meal and oil within 2 km" — free, builds habit and trust even if the user walks.
- **Envelopes:** ring-fence payday money for groceries; value even with zero delivery (Stage D).

### For spaza owners
- Order own stock from wholesalers via Trollie with delivery sorted (B2B, separate cohort).
- QR payments so customers can pay without cash (Stage D).
- Onboarding by a field agent through the secure onboarding link (not ID photos over WhatsApp).
- **Collection point is a defined commercial role:** goods in transit ownership, counts, temperature, non-collection, loss; R638 food-premises certificate, municipal permits, storage, hours, security, insurance verified for the actual municipality.
- **Compliance:** legal-form-aware, risk-based eligibility. No invented "light FICA" exemption; a lower-limit receive-only product reduces exposure but is not an exemption; nationality is not a risk test.
- Suburbs first; townships a separate later pilot.

## B2B: Trollie for Shops (stock replenishment) — separate cohort

### Why shops would switch
Most small shops already buy from a cash-and-carry (Makro, Jumbo, Devland, local wholesalers), often in person, paying for transport and losing a half-day. Trollie's edge is not a new supplier; it is **less time, better price and no stock-outs**: wholesaler price comparison on the actual basket; delivery to the door; group buying to hit bulk tiers; stock budgeting; one WhatsApp number instead of three reps.

### Low-stock detection and auto-reorder
- **Signals are partial, not inventory:** QR/POS sales, "sold out" messages, shelf photos and cadence miss cash sales, spoilage, theft, credit sales and purchases elsewhere. Data model: opening stock, receipts, sales, returns, spoilage, adjustments, unit conversions, lead times, coverage.
- **Flow:** "Your cooking oil usually runs out around tomorrow (medium confidence). Reorder 10 cases from Jumbo at R1,240 incl. VAT, delivered Thursday? Yes / Change / No." Advisory with a merchant correction path; measure stockout prediction, false alerts and excess stock before automating.
- **Rules per item:** autonomous reorders only under an explicit business mandate with aggregate caps, stock/cash constraints and revocation tests (deferred); preferred wholesaler and brand locked.
- **B2B specifics:** case quantities, minimum orders, VAT invoices with the purchaser's legal identity and VAT number, price tiers, partial fulfilment; compare on cash payable and, for vendors with valid invoices, net economic cost.
- **Group buying (separate later pilot):** deadlines, minimum quantity, commitments, allocation, shortfall handling, principal vs agent role, competition-law safeguards.
- Applies to all small and mid-size shops.

### B2B monetisation
- Wholesaler commission or listing fees; delivery margin; subscription for the shop assistant. Credit margin excluded from the base case: stock credit is a separate regulated product (NCA threshold nil; sole proprietors are natural persons) needing a responsible lender, affordability processes and loss allocation, never funded from wallet float.

## Second review (investor lens) — adopted points
- **Lead with savings and convenience, not the wallet or the agent.** First customer promise: "Here's my list. I normally buy at Checkers; if Pick n Pay or Makro is cheaper, show me where I save R200. Don't change my brands." Not: "open a wallet, do FICA, deposit, connect your agent."
- **Evidence for the behaviour:** Trade Intelligence — SA shoppers use ~4 grocery stores, online shoppers ~2.4 apps, only 5% never look for deals. World Wide Worx — R159bn online retail forecast 2026 but only ~34% of adults shop online; adoption is concentrated among affluent, connected consumers.
- **Proposition ranking (subjective):** price comparison + savings assistant 8.5/10; B2B stock purchasing 8/10; WhatsApp household assistant 7/10; AI wallet with autonomous purchasing 4/10.
- **B2B deserves earlier attention:** a spaza spending R10–20k/week on stock has a recurring commercial reason to return several times a week; a household maybe twice a month. Validate as a separate proposition.
- **Unresolved product question:** does Trollie help people spend less, or shop without doing the work? A saver will collect from two shops; a convenience buyer pays more for one delivery. Choose the primary customer before optimising both.
- **Keep:** product matching engine, price intelligence, WhatsApp interaction, budget constraints, preferences, audit trail, merchant integrations, deterministic optimiser. **Conditional on demand:** wallet, virtual cards, QR, autonomous purchasing, third-party agents, full developer platform.

### 60-day commercial validation plan (the demo is step 0)
1. **Days 1–15 — Price intelligence:** basket comparison across three retailers with permissioned or lawfully sourced pricing; test real lists against actual checkout totals including loyalty discounts.
2. **Days 16–30 — WhatsApp experience:** submit a list, get a ranked basket with substitutions and savings. No wallet, no customer funds.
3. **Days 31–45 — Real purchasing:** two or three willing independent retailers; existing licensed payment channels and merchant fulfilment; no virtual cards.
4. **Days 46–60 — Commercial validation:** completed orders, actual savings, repeat use, merchant margin, delivery performance, willingness to pay. Separate small test with spaza owners.

| Metric | Initial validation target |
|---|---|
| Households recruited | 100 |
| Households completing an order | 30+ |
| Repeat purchase within 30 days | 30%+ |
| Verified net basket savings | 5%+ |
| Orders needing manual correction | <10% |
| Positive contribution per order | Required before scaling |

The decisive test: do customers return without a discount or incentive?

## Legal and partner launch gates (release blocked if missing)
| Gate | Evidence needed | Blocks |
|---|---|---|
| Defined legal model | Counsel-reviewed entity/role/funds-flow map; seller identified per order | Any real-money activity |
| Payment permissions | Registrations/authorisations under the final SARB framework; sponsor acceptance; contracts | Money movement, cards, wallet |
| Customer funds (Stage D) | Safeguarding/insolvency analysis, redemption, reconciliation, wind-down, CRS/FATCA | Stored balances |
| FICA allocation | Classification, RMCP, CDD/reporting responsibilities, vendor evidence, trained owners | Regulated activation |
| Consumer contracting | Mandate wording, seller disclosures, review/withdraw, cancellation/refund/complaints, subscription terms | Consumer purchases |
| Privacy | PIIA, data map, lawful bases, operator/transfer contracts, retention, user controls | Processing beyond validated scope |
| Cyber/resilience | NPS Directive 1/2024 control register, independent assessment, restore evidence, incident matrix | Money-moving release |
| Merchant legitimacy | Legal-form-aware verification, operating/food permissions, payout ownership, signed checklist | Merchant orders/payments |
| Delivery operations | Eligible goods/carriers, custody, claims, recalls, failed-delivery rules | Delivery-enabled categories |
| Channel | Dated WhatsApp policy assessment, templates, opt-ins, escalation, rate card, web continuity | WhatsApp-first launch |
| Economics | Signed partner fees; contribution reporting incl. non-converting sessions | Scaling beyond pilot |

## Acceptance tests before a live pilot
(Authoritative list: blueprint §17, T01–T60.) Product identity; optimisation known-answer baskets; user authority (post-approval alterations rejected); concurrency; idempotency; reconciliation; split failure; recovery; injection; privacy; continuity; language/accessibility; economics instrumentation.

## Pilot metrics and stop conditions
- Metrics (denominators defined before data): requested-list coverage before scope trimming; quote success; activation = first delivered non-refunded basket; whole-basket fulfilment vs expressly permitted partial outcome (reported separately); perfect order; repeat rate among households with the full observation window; realised net saving vs a documented comparable delivered basket; time benefit under a defined procedure; contribution incl. failed/refunded attempts and human assistance; refund latency (submission vs confirmation); financial integrity. Medians and tails; rescued orders stay in the denominator. 30% repeat and 5% savings remain hypotheses.
- **Immediate pause (security/financial):** any unauthorised debit, duplicate economic effect, locked-constraint violation, unbalanced posted ledger transaction, suspected credential exposure or approval bypass — pause the affected scope; refunds and reconciliation continue.
- **Operational pause / cap reduction:** payment status cannot be established safely, merchant permission withdrawn, unsupported payment topology, inadequate refund liquidity, unserviceable delivery capacity, support backlog threatening remedies.
- **Reliability target (not a stop condition):** ≥95% of accepted orders delivered as approved, assessed per 20 resolved orders and cumulatively; below target triggers review and a pause on cohort growth. A serious single incident pauses without waiting for the window.
- **Scale gate:** unsubsidised contribution and repeat use with acceptable service quality.

## Open decisions for the founder
- **Initial commercial focus:** households saving on groceries (larger audience) or spazas/small retailers buying stock smarter (stronger recurring revenue)? Validate both in the 60 days; pick one.
- **Primary benefit:** lower delivered cost, less effort, or spending control — pick one, report the others.
- **Money model:** pay-per-order until evidence and a cleared operating model justify a wallet.
- **Entity and IRONSKY:** one product name, one operating entity; state whether IRONSKY supplies technology, owns the product, contracts with merchants or provides security services.
- **Name:** Trollie (trollie.ai); formal trademark clearance before marketing spend.
- **Approval:** every order during the pilot; mandates later.
- **Splitting:** prefer one store; two with explicit benefit and consent.
- **Commission formula:** one explicit, VAT-stated formula per merchant.
- **Settlement timing and refund funding:** contractual recovery plus a funded operating reserve.

Decision register IDs (owner, blocks) are in blueprint §3.2: D01 legal/funds-flow roles; D02 aggregate payment topology; D03 reservation/cancellation obligations; D04 initial rail and late-payment handling; D05 delivery custody/claims; D06 CDD responsibilities; D07 commission base and VAT; D08 refund reserve; D09 WhatsApp eligibility; D10 signed customer promise and permitted partial outcomes.

## Third review — multi-retailer fulfilment platform (adopted)
**Reframe:** Trollie is not a price-comparison service; it is a multi-retailer shopping and fulfilment platform run by a purchasing agent. The value is completing the whole task — one list, one approval, one payment, orders placed with several stores, deliveries coordinated. Grocify becomes an adjacent player or data partner; the real competition is Sixty60, asap!, delivery marketplaces and existing habits.

### Purchasing strategies (user picks; optimiser executes)
- **Cheapest:** minimise total delivered cost, even with multiple deliveries.
- **Fastest (fastest-complete):** minimise the latest delivery completion time, possibly at higher cost.
- **Balanced (default):** minimise cost subject to a reasonable window and limited merchant splits.
- Approval always shows the delivered total per strategy, e.g. single-store R1,535 vs split R1,390 (two fees R70) = R145 / 9.4% saving — hypothetical figures.

### Retailer access — investigate before committing capital
For every merchant Trollie needs, in writing: (1) current prices and stock; (2) a way to reserve or confirm the basket; (3) an authorised order-placement mechanism; (4) payment confirmation, substitutions, refunds; (5) collection/delivery handover and tracking. Independents: Trollie's own merchant portal and order management. Chains: formal commercial integration — their consumer apps/websites must not be assumed to permit automated third-party purchases. Consolidated delivery is an operational capability to contract, not a routing decision.

### Merchant model decision
**Decision for the pilot: each retailer is intended to contract as merchant of record and seller; Trollie is intended to provide disclosed purchasing/coordinating services.** The customer contracts with the retailer for goods and with Trollie for the service. Payment is collected through a provider whose capability profile supports the beneficiary graph (to be proven — see D02); merchant share settled per the provider's actual release control; Trollie's fee invoiced separately.
- **The agency label is not a liability exemption or a tax conclusion.** Acquiring roles, payment permissions, consumer liability (CPA s54 service quality, s61(2) can treat certain service providers as suppliers), VAT treatment and revenue presentation (IFRS 15 control test) are determined from the actual transactions and contracts — written role map and funds-flow review (D01) before any build.
- Role map to complete: legal seller; purchasing agent; commission recipient; acquirer-facing merchant; payment beneficiary; delivery contracting party; issuer of each invoice; bearer of refunds and chargebacks.
- Revisit (Stage D): Trollie as merchant of record only where it adds value and the exposure is priced — consolidated-delivery baskets or non-partner stores via virtual card — with its own contract, tax, liability and working-capital analysis.

### Recommended first pilot (consistent with Stage C)
One Johannesburg delivery zone, five participating retailers, one courier partner, ~100 households; real end-to-end purchases with single-store and split-store baskets; no stored-value wallet. Success = completed orders, repeat customers, actual delivered savings, contribution margin — not number of comparisons.

## Fourth review — v2 critique (adopted)

### Core engine principle
**Find the cheapest successfully fulfilable basket that satisfies the customer's preferences, delivery requirements and approved budget** — not the cheapest set of listed products. The optimiser works on fulfilable offers: merchant acceptance, stock confidence, picking time, courier collection capacity within the window, minimum orders and quote expiry all affect the result. A basket that is cheapest at two stores but only deliverable by 5 PM from one is not the cheapest option.

### Four stages (separate services, separate evidence)
1. **Discovery:** products and nearby participating merchants.
2. **Quotation:** complete basket options including delivery, fees and expiry.
3. **Commitment:** customer approval, payment authorisation, merchant acceptance — in a defined, rail-specific order.
4. **Fulfilment:** picking, substitutions, collection, delivery, settlement, refunds.
Trollie's advantage lives in stages 3 and 4; a great recommendation that cannot be executed is worth nothing.

### Partial-fulfilment rules (customer-facing)
- At approval the customer chooses **Complete-required** or **Allow partial**, asked clearly, not preselected. Per-item **must-have** flags apply in both modes.
- **Precedence rule:** a must-have item overrides permission for partial fulfilment. If it becomes unavailable, the whole basket pauses for revised approval; remaining goods are not purchased automatically unless the customer expressly authorised that outcome.
- Optional removals proceed without reapproval only when the original approval expressly permits those exact removals and fees/delivery stay inside the approved conditions. A new merchant, new item, quantity increase, higher fee, extra delivery leg or later window always needs a fresh quote and approval. Money freed by a removal is not consent to add, swap or upgrade anything.
- Decision table: must-have unavailable → stop/reapprove (both modes); optional unavailable → reapprove unless removal pre-permitted; entire optional leg fails → continue only if every approved condition still holds; customer silent before expiry → cancel uncommitted attempt and release reservations.
- Commitment order is rail-specific (see below). Rejected legs before capture/immediate payment are released; refunds for legs failing after payment follow the refund model; the customer sees `bank hold`, `charged`, `refund requested`, `refund confirmed` separately.
- Refunds for failed legs are funded from Trollie's reserve where the rail cannot reverse; recovery follows. Disclosure at approval: separate retailers cannot give an atomic transaction.

### One payment, several merchants
- **Three things are separate records:** purchase approval (customer authority for a basket and defined outcomes), payment operation (authorise/capture/immediate charge/void/refund, with the semantics the chosen rail actually offers) and settlement allocation/receipt (who gets funds, when, under whose control). One approval need not mean one bank transaction; multiple captures do not prove multi-beneficiary settlement.
- **Topology options:** A — provider-supported marketplace collection with beneficiary allocation covering both retailers, delivery and Trollie (preferred, subject to proof); B — approved collection plus provider-executed disbursements (needs written approval of role, funds ownership, safeguarding, reserves — never an improvised operating-account flow); C — separate payments per retailer under one session (changes the one-payment promise; explicit founder decision, never a silent adapter fallback).
- **Rail-specific branches:** card with authorisation/capture — reserve stock → approve → authorise via hosted checkout → revalidate reservations → commit merchants → single final capture of the accepted total; void unused authorisation if a required leg fails. Immediate-payment rails (PayShap/pay-by-bank) — reserve and confirm → approve → pay → revalidate → commit; a payment arriving after a hold expires pauses the order and verifies supply; refund if supply cannot be secured. No adapter may fabricate an AUTHORISED state to force an immediate rail into the card branch.
- **Refund allocation:** track customer entitlement, provider beneficiary reversal and ultimate merchant liability as three records; a retailer-specific refund on a proportional provider split needs a reconciliation adjustment so the innocent retailer does not bear it. Refund initiation, provider confirmation and bank credit are distinct states; no second compensating payment because a card refund is slow.
- **Provider feasibility gate (D02):** demonstrate, synthetic first then low-value live, one authorisation with the exact number of charges, correct allocation to two retailers plus platform and delivery, a rejected retailer before capture, payment after reservation expiry, a Retailer-B-only refund with fee treatment, duplicate/delayed/out-of-order events, a timeout after the provider accepted, and reconciled settlement reports. A happy-path payment does not pass. The one-payment promise is not advertised until this passes. Unsupported capabilities fail closed.

### Delivery consolidation (modelled, not assumed)
Compare two separate deliveries against one courier collecting from two shops, including waiting time at each shop, handling, failed collection, perishables and courier liability. Consolidation is a contracted capability, not a software routing option. No hub is required for a two-pickup route; a hub is a separate operational design.

### Customer promise (narrowed)
Draft (counsel to approve; not a narrowing of statutory remedies): "We submit your approved purchase only to the named stores and within the amount and conditions you approved. We show each store's acceptance and delivery status. If goods cannot be supplied, we handle the applicable cancellation or refund and show its progress. A refund being initiated does not mean your bank has already credited it." Distinguish attempted order, merchant acceptance, temporary debit and refund entitlement; do not promise "never pay for undelivered goods" as an unconditional guarantee.

### Development plan — merchant integration feasibility gate first
**First engineering milestone (before the customer-facing agent):** one real shopping list → orders created at two cooperating independent retailers → their acceptance → coordinated collection → completed delivery → payment settled and reconciled. Initially **human-assisted** (ops staff place orders through the merchant portal). Signed pilot agreements with at least two merchants, with catalogue, acceptance, picking and refund workflows proven end to end. Then the same transaction with a deliberately failed retailer leg. Once this works, AI automation is an efficiency improvement, not an unproven dependency. The fictional-merchant demo remains the investor opener but is not the gate. Milestones M0–M8 are in blueprint §18.

### Gaps still open (priority)
- **Critical:** merchant integration demonstrated, not assumed (two signed pilot agreements).
- **Critical:** one-payment-multiple-merchants fully specified and demonstrated with the provider (Stitch one-destination limit noted).
- **High:** delivery consolidation modelled with real courier terms.
- **High:** commission, payment and delivery assumptions replaced with signed pricing and pilot measurements.

**Status:** PRD v2.1 is sufficient to guide a proof of concept; it does not authorise a production financial or fulfilment launch. Next milestone: signed merchant and payment-provider agreements, demonstrated end-to-end order execution, measured unit economics.

## Change log
- **v2.1 (28 Oct 2026, engineering blueprint):** edits applied in place — original opening marked historical; mobile-web-first stack; WhatsApp compliance moved to a dated gate; payment rewritten into separate approval / payment-operation / settlement records with rail-specific branches and a provider feasibility gate (Stitch one-destination split and proportional-refund constraints recorded); must-have precedence rule and partial-fulfilment decision table; merchant-model categorical liability/tax claims removed; customer promise redrafted; economics corrected (R25 example withdrawn; R2,000 with R35 subsidy = −R2.79; two-store sensitivity added); 95% made a reliability target with defined window, not a stop condition; settlement release control recorded as a capability field. The separate Engineering Review and Implementation Blueprint (2026-10-28) is adopted as the implementation baseline.
- **v2 (28 Oct 2026):** incorporated two independent reviews — wallet moved to a gated stage; pay-per-order Stage C; explicit per-order approval; contradictions resolved; regulatory register updated (SARB framework timeline, PASA transition, NPS Directive 1/2024, CRS R.6886, GN7B, VAT/B34); competitor corrections (Grocify, Pixie, Pingo, B2B incumbents); issuer prospect list corrected; delivery suitability-first; envelope encryption; unit economics, 60-day validation plan, launch gates, acceptance tests and open decisions added.
- **v1 (28 Oct 2026):** original agentic-wallet concept and PoC architecture.
