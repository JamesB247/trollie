# Trollie: Engineering Review and Implementation Blueprint

**Review date:** 28 October 2026  
**Document version:** 1.0 - proposed implementation baseline  
**Source:** `Agentic Shopping Wallet - PoC Architecture(3).md` (uploaded filename uses an en dash; source SHA-256 recorded in Appendix B).  
**Status:** Suitable for internal product/engineering planning and partner diligence. Not a production launch approval, legal opinion, provider certification, or evidence of signed partnerships.  
**Product retained:** An end-to-end, multi-retailer purchasing and delivery service, not a price-comparison-only product.

## Executive decision

**Proceed with a bounded end-to-end pilot build. Do not add another general-purpose vision layer.** The PRD now describes the right product: one shopping request, a complete purchasable basket, explicit customer approval, retailer orders, coordinated delivery, and accountable after-sales support.

The remaining work is not primarily better prompting. It is turning commercial promises into precise transaction rules and proving that the selected providers can execute those rules.

Four immediate decisions control the build:

1. Select an approved collection/settlement topology that actually supports the parties in one basket. A provider advertising split settlement is not sufficient evidence.
2. Choose the first payment rail and define its reservation, payment, cancellation and refund sequence. Do not force card-authorisation semantics onto every rail.
3. Define exactly what may happen after a merchant declines: mandatory items, optional removals, delivery fees, fresh approval and refund ownership.
4. Replace the accumulated review appendices with one normative implementation baseline and an evidence register.

**Most consequential new verification:** Stitch's published split-settlement interface currently permits a primary merchant and only one additional destination merchant. That is not, by itself, an arbitrary two-retailer-plus-platform-plus-courier settlement solution. Its published split refunds also follow the original beneficiary proportions, which can differ from the retailer economically responsible for a missing item. These are specific integration constraints, not reasons to abandon the product. [S01][S02]

**Financial correction:** The PRD's own single-store assumptions produce R32.21 contribution on a R2,000 goods basket. An additional R35 delivery subsidy produces **minus R2.79**, not R25. The latter figure cannot be reproduced from that model. Section 16 shows the calculation and its limitations. [PRD: Minimum order and delivery economics; CALC]

## How to read this document

- **PRD requirement:** Already stated in the uploaded document. Section references identify the source.
- **Verified external fact:** Supported by the primary sources in Appendix A, checked for this review.
- **Recommendation:** A proposed design decision, not something silently attributed to the PRD or an approved partner.
- **Gate:** Evidence or a decision required before a capability can be enabled.
- **Illustration:** Synthetic data or assumptions, not quoted provider pricing or observed pilot results.

This is a new, focused review and implementation blueprint. It does **not** claim to reconstruct the previously unavailable research report. It does not independently recertify every market statistic, competitor statement, regulatory date or provider price in the source PRD. Claims outside the verification scope remain in the evidence backlog rather than becoming established facts through repetition.

## Contents

1. What is already settled
2. Final critical findings
3. Proposed pilot baseline and decision register
4. Payment-provider feasibility and funds flow
5. Customer authority, quotation and partial fulfilment
6. Architecture and trust boundaries
7. Domain model and database schema
8. State machines
9. Transaction workflows and compensation
10. API contracts
11. Product matching and optimisation
12. Merchant and delivery operations
13. Security, privacy and identity
14. Reconciliation, refunds and operating reserves
15. Observability and support
16. Corrected commercial model
17. Acceptance tests
18. Implementation milestones
19. Pilot measurement and stop conditions
20. Required PRD edits and release checklist
Appendix A. Primary-source evidence register
Appendix B. Source provenance and verification limits

---

## 1. What is already settled

The following are supported by the latest PRD and should not be reopened merely to generate another review:

| Subject | Existing decision | Source section |
|---|---|---|
| Product | Complete multi-retailer purchasing and fulfilment, not just information about prices | Third review - multi-retailer fulfilment platform |
| Initial payment model | Pay per order; no stored customer balance in Stage C | Phasing; User experience |
| Customer authority | Explicit purchase approval; immutable quote; server-enforced controls | Security architecture; User experience |
| Initial geography | One Johannesburg delivery zone | Recommended first pilot |
| Initial retailer split | At most two retailers per basket | Technical architecture - Agent layer |
| Goods | Packaged ambient goods; regulated and temperature-sensitive categories excluded | Stage C; Delivery |
| Commercial role intention | Retailers sell goods; Trollie coordinates and provides its service, subject to contractual analysis | Merchant model decision |
| Interfaces | WhatsApp entry/notifications; trusted mobile web for approval; merchant/support interfaces | Built-in agent; UX/UI principles |
| Payments and ledger | Provider integration, business-operation idempotency, double-entry invariants, reconciliation | Security architecture |
| Delivery | Merchant delivery, a suitable contracted courier, or collection; no owned fleet | Delivery |
| First proof | One actual list fulfilled by two cooperating retailers, initially with human assistance | Fourth review - Development plan change |
| Later capabilities | Stored value, cards, QR, standing mandates, external agents, B2B and credit are separately gated | Stage D |

**Interpretation:** The product question is no longer whether Trollie should become a comparison website. The test is whether it can reliably complete a cross-store purchase at an acceptable total cost. Human-assisted operations are permitted during validation, but their cost must be measured.

## 2. Final critical findings

### 2.1 Critical: three different kinds of approval are still conflated

The PRD's Fourth review says the customer authorises one aggregate payment and capture happens per accepted leg where split settlement is supported.

These are separate operations:

- **Purchase approval:** permission from the customer for a specified basket and defined outcomes.
- **Payment authorisation/capture:** operations supported by a particular payment method, acquirer and product.
- **Settlement allocation/release:** instructions and conditions governing who receives funds and when.

A single purchase approval need not mean one bank transaction. Multiple captures do not prove multi-beneficiary settlement. Settlement allocations do not prove that a beneficiary has received funds.

**Required correction:** Implement an explicit provider capability profile. Enable only combinations confirmed for Trollie's merchant account and commercial model. The proposed profile is in Section 4. [REC; S01][S03][S04]

### 2.2 Critical: the selected split product may not fit the beneficiary graph

**Verified:** Stitch's public integration documentation states that `splitSettlements` supports only one destination entry, in addition to the primary settlement. Destination identifiers must be provisioned by Stitch. [S01]

**Implication, not a provider rejection:** If Trollie is the primary beneficiary, two independently paid retailers require a different approved configuration, another product, or a different funds-flow design. Courier and platform compensation also need explicit treatment. Do not assume a second entry in an API array will work because the type is an array.

**Gate:** Demonstrate the exact two-retailer transaction, platform compensation, delivery compensation, a retailer-specific refund and reconciliation in the selected provider environment. Confirm the live account has the same enabled capabilities.

### 2.3 Critical: a retailer-specific refund may not map to the provider's refund allocation

**Verified:** Stitch's split-refund documentation describes proportional reversal across the original beneficiaries, with refund fees and no return of the original charge fee. [S02]

**Design consequence:** A refund caused by Retailer B can debit a different economic allocation from the one Trollie's merchant contracts require. Store two concepts separately:

`customer refund allocation` and `provider beneficiary reversal`.

A reconciliation/adjustment process must resolve the difference through permitted settlement adjustments, reserves or contracted recovery. Never debit a bank account merely because an internal ledger says a retailer owes money.

### 2.4 Critical: the card-first commitment sequence is not universal

The PRD says: authorise payment, ask all merchants to accept, then capture accepted legs. That is a possible workflow for a suitable card product. It is not a universal pay-per-order primitive.

Peach documents card preauthorisation, full/partial capture and reversal, but those features do not by themselves confirm Trollie's marketplace settlement model. Ozow documents payins, refunds and settlements as separate lifecycles. [S03][S04]

**Recommendation:** Confirm/temporarily reserve the basket before sending the user into an immediate-payment checkout. Where authorisation/capture is contractually supported, use a card-specific branch. Handle late payment after reservation expiry explicitly. No branch may invent an authorisation hold that its rail does not offer.

### 2.5 Critical: merchant acceptance is not a durable stock reservation

The source requires acceptance and stock confidence but does not define an enforceable reservation object.

**Recommendation:** Introduce a merchant reservation with exact SKUs, quantities, price, expiry, merchant order reference, release semantics and evidence of who accepted it. A human-operated portal can provide this during the pilot. If stock cannot be held, label the quote conditional and do not promise all-or-nothing prevention of charges.

A payment challenge can outlast an inventory hold. Queue delays can outlast a courier quote. Expiry handling is a core transaction feature, not a UI timer.

### 2.6 Critical: partial fulfilment does not define what happens to a must-have item

The PRD introduces both an allow-partial mode and a per-item must-have flag. It does not say which takes precedence or whether optional goods may be purchased after a mandatory item fails.

**Recommendation:** Mandatory requirements override permission for optional removals. In Stage C, any unavailable must-have item blocks commitment of the whole parent basket unless the customer approves a revised basket. Optional removals are allowed without reapproval only when the original approval explicitly permits those exact removals and the resulting fees and delivery arrangement remain inside the approved conditions.

Do not silently reduce quantities or repurpose money released by a removed item to buy something else.

### 2.7 High: delayed settlement is not established by the existence of split settlement

The PRD wants settlement after fulfilment evidence. An automatic provider settlement schedule may not be controllable by an arbitrary Trollie delivery event.

**Recommendation:** Record `settlement_release_control` and actual settlement timing in the provider capability contract. If settlement happens before delivery, model the resulting merchant exposure and reserve requirements. Do not label funds as held pending delivery unless that is actually what the provider does.

### 2.8 High: customer guarantees promise an outcome the system cannot always prevent

The proposed promise says the approved basket is ordered and the customer never pays for undelivered goods, while also acknowledging merchant rejection and irreversible payments.

**Recommendation:** Distinguish attempted order, merchant acceptance, temporary debit and ultimate refund entitlement. Use wording such as:

> We submit your approved purchase only to the named stores and within the amount and conditions you approved. We show each store's acceptance and delivery status. If goods cannot be supplied, we handle the applicable cancellation or refund and show its progress. A refund being initiated does not mean your bank has already credited it.

Counsel must approve the actual consumer terms. Do not use this drafting suggestion to narrow mandatory consumer remedies.

### 2.9 High: agency is not immunity, and merchant of record is not a single universal role

The source still says the model has no product-liability exposure as reseller, VAT only on the fee and cleaner IFRS 15 agent accounting. A later caveat does not remove those earlier categorical statements.

Consumer Protection Act section 54 concerns service quality, and section 61(2) can treat certain service providers as suppliers of goods for that section. IFRS principal/agent analysis turns on the specified supply and control, not the platform label. These support obtaining transaction-specific analysis; they do not decide Trollie's final classification. [S09][S10]

**Required role map:** legal seller of goods; purchasing agent for the customer; recipient of merchant commission; acquirer-facing merchant; payment beneficiary; delivery contracting party; party issuing each invoice; party bearing refunds and chargebacks. One entity may hold several roles, but that must be deliberate.

### 2.10 High: the financial example mixes incompatible assumptions

Under the written assumptions, R2,000 gives R32.21 before subsidy. Adding R35 of subsidy gives minus R2.79. Retain the approximately R628 break-even calculation only with its original assumptions. Remove the unexplained R25 example or identify the complete, different model that produces it. [PRD: Minimum order and delivery economics; CALC]

### 2.11 High: the document is an accumulated review log rather than one authoritative spec

Remaining inconsistencies include the original wallet-first opening, native-app stack versus mobile-web-first UX, reserve-money language before the wallet gate, the 60-day plan versus Stage B's 8-12 weeks, and separate services versus a modular monolith.

**Recommendation:** Move earlier drafts and reviews to a historical appendix. Keep one current pilot scope, one sequence, one provider profile and one decision log. No newer section should rely on readers guessing that it overrides an earlier instruction.

### 2.12 High: scope restrictions can invalidate the success claim

A successful ambient-goods pilot does not prove a complete fresh-grocery service. Two retailers with narrow catalogues may fail to supply ordinary household lists even when every integration works.

**Recommendation:** Measure requested-list coverage before excluding unsupported items. Report both full-list completion and completion of the explicitly agreed pilot basket. Do not market the latter as proof of the former.

### 2.13 High: onboarding requirements are not yet tied to the exact service

Risk-based CDD is already in the PRD, but mandatory identity/liveness checks at every shopper's first purchase remain an assumption. The FSCA describes CDD obligations for accountable institutions and a risk-based approach; it does not establish that this particular shopping flow requires universal selfie onboarding. [S12]

**Recommendation:** Separate ordinary customer account security from regulatory CDD. Obtain a written allocation for Trollie, the payment provider and each merchant. Apply necessary checks when required; do not remove required CDD, and do not invent blanket KYC requirements solely because a payment occurs.

### 2.14 High: 95% is currently written ambiguously as a stop condition

The source places `>=95% of accepted orders delivered as approved` inside its stop-conditions sentence. That is a success target, not the adverse trigger.

**Recommendation:** Define the denominator, observation window and minimum sample, then specify what happens when performance falls below the target. Security and financial-integrity failures have separate immediate pause rules.

## 3. Proposed pilot baseline and decision register

### 3.1 Baseline proposed for approval

| Decision | Proposal | Relationship to PRD |
|---|---|---|
| Customer | Households in one serviceable locality | Retains consumer pilot; B2B remains separate |
| Merchant count | Two integration-proof merchants, up to five activated pilot merchants | Retains the two-store proof and five-store cohort plan |
| Basket split | One or two retailers; never more than two in Stage C | Existing requirement |
| Product categories | Packaged ambient goods only; explicit supported-category notice | Existing requirement |
| Interface | Mobile web approval and status; WhatsApp adapter; merchant and operations web consoles | Resolves native-app contradiction |
| Basket modes | Cheapest, fastest-complete, balanced; all constrained by actual fulfilment | Retains three strategies; defines fastest |
| Fulfilment choice | Ask whether optional omissions are permitted; must-have items block the basket | Tightens the existing partial rules |
| Delivery | Separate legs by default; consolidated pickup only after a contracted/tested capability gate | Preserves both outcomes without pretending consolidation is available |
| Payment | One approved provider product and initial rail; topology demonstrated before live money | Makes the provider gate executable |
| One-payment promise | Retain as target; do not advertise it until the exact aggregate flow is proven | No silent downgrade to multiple charges |
| Wallet | None | Existing requirement |
| Agent | Suggests structured shopping intent, requests quotes and explains authoritative results | Existing authority boundary |
| Models | Candidate model benchmarked; no hard-coded capability assumptions based on brand | Existing requirement |
| App/service structure | One codebase with bounded modules and separately permissioned execution roles | Resolves logical module vs deployment confusion |
| Economics | Measure real costs per purchase attempt and per completed basket | Existing requirement |

### 3.2 Decisions that must remain explicitly open

Use records with `decision_id`, owner role, options, chosen option, supporting evidence, date, review trigger and affected requirements. Proposed owner roles do not imply that a person has been assigned.

| ID | Decision/evidence needed | Owner role | Blocks |
|---|---|---|---|
| D01 | Legal seller, agent, acquiring and funds-flow roles | Founder + payments counsel | Real-money activity |
| D02 | Aggregate payment with two retailers, Trollie and delivery allocation | Payment integration lead + provider | One-payment production promise |
| D03 | Reservation and merchant cancellation obligations | Operations lead + merchants | Complete-basket commitment |
| D04 | Initial rail and handling of payment after reservation expiry | Engineering + provider | Live checkout |
| D05 | Delivery party, custody, claim and failed-delivery allocation | Operations + courier + counsel | Delivery launch |
| D06 | Customer eligibility/CDD responsibilities | Compliance owner + provider | Regulated activation |
| D07 | Commission base, VAT treatment, fee allocation, merchant payout timing | Finance + tax adviser | Commercial settlement |
| D08 | Refund reserve and permitted settlement adjustments | Finance + provider | Refund promises |
| D09 | WhatsApp marketplace/AI-service eligibility and applicable terms | Channel owner | WhatsApp-first launch |
| D10 | Signed customer promise and permitted partial outcomes | Product + counsel | User approval UX |

**Default when a gate is unresolved:** keep the capability disabled. Continue synthetic testing and non-binding workflow rehearsals. Do not rename a live transaction a test to avoid its obligations.

## 4. Payment-provider feasibility and funds flow

### 4.1 Required capability contract

Maintain a versioned profile for each **provider + product + payment method + Trollie account configuration**. Public documentation is supporting evidence, not enablement.

| Field | Required answer |
|---|---|
| Account and legal scope | Which entity contracts with the provider? Which seller/submerchant model is authorised? |
| Payment methods | Exact supported rails and currencies for this account |
| Collection | Immediate debit, authorisation/capture, or another defined mechanism |
| Capture semantics | Single full, single partial, multiple partial; final-capture flag; expiry and void behaviour |
| Beneficiaries | Primary recipient; maximum additional recipients; onboarding and verification requirements |
| Allocation | When allocations are fixed; whether changes after acceptance are allowed |
| Settlement | Who controls release; whether delivery evidence can delay it; schedules, reserves and statements |
| Refunds | Partial/full; original-source routing; beneficiary allocation; fees; funding and status evidence |
| Disputes | Chargeback party, deadline, evidence, recovery and negative-balance treatment |
| Idempotency | Supported endpoints, retention horizon, lookup by merchant reference, duplicate protection |
| Events | Signatures, event IDs, delivery/replay ordering, status-query endpoints |
| Customer experience | Hosted checkout, 3DS/bank-app interaction, statement descriptor and receipt identity |
| Operational support | Incident escalation, outages, production certification, contractual SLA |

**No automatic capability inheritance:** card support does not imply pay-by-bank support for the same split/refund workflow. A marketing page for payouts does not establish marketplace collection permission.

### 4.2 What this review established, and what it did not

| Candidate/documentation | Verified in this review | Still requires written confirmation and testing |
|---|---|---|
| Stitch card split settlement | Public two-beneficiary limitation and provisioned destination identifiers | A topology covering every pilot party, live-account enablement and release timing [S01][S16] |
| Stitch split refunds | Original split proportions affect beneficiary reversals | Retailer-specific economic recovery without charging an innocent party incorrectly [S02] |
| Peach card management | Separate authorisation, capture and reversal operations are documented | Marketplace structure, beneficiary allocation and exact account configuration [S03] |
| Ozow payins/refunds | Separate financial object lifecycles; refund operation and funding requirements documented | Approved collection/disbursement roles, aggregate multi-retailer settlement and contracted charges [S04][S05] |

This is not a ranking or vendor selection. No provider has been contacted, commercially approved or integrated as part of this review.

### 4.3 Three possible topologies

**Topology A - provider-supported marketplace collection and beneficiary settlement.** The customer makes one payment; the approved provider maintains the necessary beneficiary allocations and permitted release/refund controls. This best matches the target experience, subject to actual support for the whole graph.

**Topology B - approved collection plus subsequent provider-executed disbursements.** One customer payment is collected under a specifically approved model; later payouts satisfy retailer and courier obligations. This is not merely a technical workaround. The legal role, funds ownership, safeguarding, settlement delay, insolvency treatment, reserves and reconciliation require approval. Do not improvise it through an ordinary operating account.

**Topology C - multiple retailer payments under one shopping session.** Each retailer receives its own payment; Trollie coordinates the basket and delivery. This may be a discovery-stage fallback, but it changes the one-payment promise and can create multiple checkout/3DS interactions. It must be an explicit founder-approved UX change, not an invisible adapter fallback.

**Recommendation:** Seek Topology A first; assess B only with written approval. Keep C as an explicit alternative rather than presenting it as equivalent. The ability to deliver from two shops must remain a pilot test whichever topology is selected.

### 4.4 Commercial beneficiary graph

For every chargeable amount, record both the **economic owner** and the **provider settlement recipient**. They are not automatically identical.

Example categories: Retailer A goods, Retailer B goods, delivery leg 1, delivery leg 2, customer service fee, merchant commission, payment processing cost, tip, subsidy, refund and dispute reserve.

A merchant-funded commission reduces merchant proceeds; it is not a second customer fee. A courier invoice paid by Trollie is different from a direct courier allocation. A displayed delivery fee is customer revenue or agency collection according to the approved arrangement, not automatically pure pass-through.

### 4.5 Provider feasibility test - mandatory evidence

Use a synthetic basket first and a low-value live test only after the legal gates. Prove:

1. One customer authorisation and the exact supported number of charges.
2. Correct allocation for two retailers and the agreed platform/delivery compensation.
3. A rejected retailer before capture or before immediate payment.
4. A payment that completes after the inventory reservation expires.
5. A refund attributable solely to Retailer B, including beneficiary adjustments and fees.
6. Duplicate, delayed and out-of-order provider events.
7. A timeout after the provider accepted a charge or refund.
8. Settlement reports and actual receipts reconcile without treating gross sales as Trollie revenue.

A happy-path payment alone does not pass this gate.

## 5. Customer authority, quotation and partial fulfilment

### 5.1 Distinguish estimates, firm quotes and accepted orders

**Estimate:** prices or capacity may be stale/unreserved; not purchasable.

**Firm quote:** all selected offers and required delivery capacity have evidence valid until a stated deadline. Only merchants with an adequate reservation mechanism qualify. A qualified quote may still require a payment step before a binding sale, according to the contracts.

**Approved purchase intent:** the customer has authorised the precise quote and any explicitly stated conditional outcomes. Approval is not proof of payment or merchant delivery.

**Committed order:** the required payment evidence and merchant commitments exist, with any remaining fulfilment risks identified.

Never display an estimate as a confirmed order. Never use payment success as proof that the items exist.

### 5.2 Quote contents

Each immutable quote version must contain:

- Currency and integer-minor-unit amounts; item identifiers, product variants, packs and quantities.
- Legal seller and merchant location for every leg; offer revision and merchant reservation reference.
- Substitution conditions, mandatory items and any permitted optional omissions.
- Merchandise, discounts, delivery, service fees, tips, tax treatment and maximum payable amount.
- An approved address **version**, not a mutable address pointer alone.
- Delivery mode, number of deliveries, windows, carrier capability and quote expiry.
- Customer-selected strategy and complete-list coverage.
- Payment product/method constraints that affect fees or authority.
- Cancellation/refund terms version and the permitted failure outcome.
- Quote ID, revision, canonical payload hash and applicable policy versions.

The final total must not double-count VAT already included in product prices. Tax-code metadata remains available for invoices and reconciliation.

### 5.3 Approval is a bounded contract, not permission to spend up to a number

The maximum amount is necessary but insufficient. A cheaper replacement merchant, a different destination, a different item or a materially later delivery can still violate authority.

Store the approved snapshot separately from the eventual execution snapshot. Permit differences only when a deterministic predicate, itself part of the original approval, allows them. A subsequent order must reference either the original approval and its permitted transformation, or a fresh approval.

For Stage C, a conservative rule is preferable: any new retailer, new product, quantity increase, later window, extra delivery leg or increased fee requires a new quote and approval.

### 5.4 Partial fulfilment decision table

| Event | Complete-required basket | Explicitly allow-partial basket |
|---|---|---|
| Any must-have item unavailable | Stop before commitment; request revised approval | Same result; must-have overrides partial mode |
| Optional item unavailable | Stop and request revised approval | Remove only if removal is explicitly permitted; otherwise reapprove |
| Entire optional retailer leg fails | Stop and request revised approval | Continue only if removing that leg meets every approved condition |
| New merchant needed | New quote and approval | New quote and approval |
| Delivery fee increases after a removal | New quote and approval or platform absorbs the increase | Same; spare budget is not implied consent |
| Full basket was committed, then a merchant fails | Compensation/refund workflow | Compensation/refund workflow |
| Customer does not respond before expiry | Cancel uncommitted attempt and release reservations | Do not treat silence as permission |

For routine groceries, ask the partial-fulfilment question clearly; do not hide it in a preselected term. The source's partial-default proposal is changed here **as a recommendation**, not as an already adopted founder decision.

### 5.5 Reservation and approval timing

Recommended rule:

`latest_start_time = earliest relevant expiry - measured execution safety margin`.

Relevant expiries include stock reservations, merchant prices, courier offers, approval validity and any provider authorisation. The safety margin is calibrated from observed checkout/execution latency, not chosen by an LLM.

Before accepting an approval and again before each economic action, verify the records needed for that action. During checkout, do not cancel a live payment attempt merely because the browser closed. First obtain authoritative provider state.

### 5.6 Customer money-at-risk display

A revised basket can cost less while the customer's bank temporarily shows the original full authorisation or a refund still pending. Display separately:

`current purchase total`, `bank hold`, `charged`, `refund requested`, `refund confirmed`.

Do not release an internal planning budget as though the bank has released funds. In Stage C there is no customer wallet balance to restore.

## 6. Architecture and trust boundaries

### 6.1 Recommended shape

Use a **modular monolith codebase** with a small number of separately permissioned runtime roles. Logical modules are not an instruction to build a microservice per table.

```text
WhatsApp adapter / mobile web / merchant portal / operations console
                              |
                  Application and approval API
                              |
          +-------------------+--------------------+
          |                   |                    |
     Shopping session    Product / offer       Quote / policy /
     and intent module   / reservation        approval records
          |                   |                    |
     Restricted AI            +---- Optimiser -----+
     worker                         |
                            Purchase orchestrator
                                    |
                       Durable operation + outbox
                                    |
                    Restricted financial executor
                         /                    \
                Payment adapter        Settlement/refund adapter
                                    |
                         Financial event inbox
                                    |
                      Ledger + reconciliation

Merchant-order and delivery adapters are separate from the model.
Customer notifications read authoritative projections, not model claims.
```

This is a proposed service-boundary representation, not a deployed architecture.

### 6.2 Minimal deployment roles

| Runtime role | Can do | Must not do |
|---|---|---|
| Application/approval API | Customer sessions, authoritative quote rendering, verified approval ceremony, merchant portal requests | Accept unverified client totals; expose provider credentials to browsers |
| AI worker | Interpret list input, query a limited product view, explain structured results | Read KYC, write approvals, move funds, change payees or fetch arbitrary URLs |
| Commerce worker | Merchant reservations, order state, delivery requests, durable workflow progression | Bypass approved purchase conditions or invent payment success |
| Financial executor/reconciler | Provider calls for approved operations, verified events, ledger postings, reconciliation | Accept arbitrary payees/amounts from model output; edit posted ledger entries |

The worker roles can share a repository and build artefact. Their credentials, network access and database privileges must remain separate. Merely labelling functions as separate services inside one privileged process is not a trust boundary.

### 6.3 Persistence and delivery guarantees

Use PostgreSQL as the transactional system of record. Store a business state transition and its outbox event in the same database transaction. A dispatcher publishes committed events; consumers deduplicate deliveries. The outbox pattern addresses the database/message dual-write problem, not atomicity with an external merchant or bank. [S07]

Critical concurrent decisions use row locking or serializable transactions with bounded retries. PostgreSQL's default isolation level is Read Committed; choosing PostgreSQL alone does not prevent business-level races. [S06]

Provider calls happen **outside** long-running database transactions. Persist the intended operation first, send it, then persist observed results. An ambiguous result enters reconciliation rather than a new payment attempt.

### 6.4 State ownership

- Product service owns identity and verified mappings.
- Merchant adapter owns observed offer/reservation/acceptance evidence.
- Quote service owns immutable basket snapshots and totals.
- Approval module owns credential-bound consent evidence.
- Orchestrator owns permitted next actions and compensation plans.
- Payment adapter owns provider-specific financial observations.
- Ledger owns append-only monetary postings.
- Reconciler owns exception resolution and external-match evidence.
- Support console exposes controlled commands; it is not a second source of truth.

### 6.5 Stack choices

Retain FastAPI and PostgreSQL from the PRD as a reasonable baseline. Use one durable-job approach initially rather than implementing Temporal and Step Functions simultaneously. A managed queue plus a database workflow state machine is sufficient for an initial bounded implementation if its retry, timeout and recovery behaviour is tested.

Retain the proposed Cape Town core-region preference, but verify service availability, contractual processing locations and backup arrangements during deployment design. This document does not certify end-to-end South African residency. Use a web client before a native app. Do not introduce Redis until a measured requirement exists; never make it the authority for financial state.

## 7. Domain model and database schema

**Status:** Proposed logical schema and constraints, not a tested SQL migration. Final types, indexes, privileges and posting procedures require implementation and migration tests.

### 7.1 Data conventions

Use UUID identifiers; timezone-aware UTC timestamps with Africa/Johannesburg presentation; integer cents for money; ISO currency codes; immutable versions for prices, addresses, quotes and policies. Quantities retain both requested units and purchasable pack counts. Do not use floating-point arithmetic for money.

Every tenant-owned record carries an owner/account reference. Cross-tenant access is denied independently of whether a caller knows a valid UUID. Every external identifier is scoped by provider/merchant account and environment.

### 7.2 Core tables

| Table | Key fields | Required constraint or behaviour |
|---|---|---|
| `customer_accounts` | id, status, created_at, recovery_state | One adult owner per pilot account; phone is not durable proof of identity |
| `auth_credentials` | id, account_id, credential_id, public_key, flags, revoked_at | Unique credential ID; approval evidence survives credential retirement |
| `address_versions` | id, account_id, encrypted_address, validated_service_area, created_at | Immutable versions; approving a pointer cannot approve later edits |
| `preferences` | id, account_id, product/category, rule, provenance, version | User-confirmed constraints; never promoted from an untrusted suggestion |
| `merchants` | id, legal_party_id, state, payout_destination_version | Legal, integration and operational readiness represented independently |
| `merchant_locations` | id, merchant_id, opening_hours, service_polygon, order_limits | Store-specific prices, stock, hours and capacity |
| `merchant_capabilities` | merchant_location_id, version, reserve/commit/cancel/status flags, evidence | No inferred support from a Shopify/WooCommerce brand label |
| `products` | id, GTIN_nullable, brand, variant, size, unit, pack, category | Identity is distinct from a store offer; ambiguous mappings are not exact |
| `product_mappings` | merchant_sku, product_id, revision, verification_evidence | Unique active mapping per merchant SKU/version; auditable correction |
| `offer_versions` | id, location_id, product_id, price_minor, tax_code, promo_rules, stock_observation, observed_at | Immutable observation; freshness and availability are explicit |
| `shopping_sessions` | id, account_id, intent_version, budget_minor, mode, status | Parent for attempts and session cost, including abandonment |
| `requested_items` | id, session_id, requested_quantity/unit, locked_set, optional, must_have | Must-have/optional conflict rejected; ambiguous units require confirmation |
| `reservations` | id, merchant_id, external_ref, lines_hash, expires_at, state | Unique merchant/client reference; release/expiry does not mean sale cancellation |
| `quotes` | id, session_id, version, snapshot, hash, total_minor, expires_at | Immutable payload; unique session/version; state is a separate projection |
| `quote_lines` | quote_id, line_id, offer_version_id, packs, line_total_minor, leg_id | Same snapshot values as quote hash; no mutable live-price lookup at approval |
| `quote_legs` | id, quote_id, merchant_id, reservation_id, amount_minor, delivery_plan_id | Every monetary/item line has a contracting party |
| `approval_challenges` | id, account_id, quote_id/hash, nonce, expires_at, consumed_at | Single use; bound to session, origin, account and exact quote |
| `approvals` | id, challenge_id, credential_id, verified_evidence, conditions_hash | Unique accepted approval per challenge; insert only via trusted verification |
| `orders` | id, account_id, quote_id, approval_id, state, execution_snapshot_hash | One active execution per approved purchase intent unless explicit versioned amendment |
| `order_legs` | id, order_id, merchant_id, external_order_ref, amount, state, version | Unique merchant/client order reference; separate leg state |
| `delivery_jobs` | id, route_quote_ref, service, state, external_ref, capacity/expiry | One job may cover multiple retailer legs |
| `delivery_leg_links` | delivery_id, order_leg_id, package_ids, pickup_sequence | Many-to-many mapping supports consolidation without merging seller liability |
| `financial_operations` | id, order_id, action, provider, request_hash, idempotency_key, state, amount_minor, external_ref | Durable logical operation; keys never reused for a different request |
| `payment_allocations` | operation_id, economic_party, provider_beneficiary, gross/fee/net | Allocation is not proof of settlement; unknown fees stay null |
| `refunds` | id, order_id, line/leg allocation, original_payment_ref, reason, state, amount_minor | Cumulative requested/executed refunds controlled under lock |
| `settlement_items` | provider_report_id, operation_id, beneficiary, gross/fees/net, settled_at | External report provenance; prevent duplicate report imports |
| `ledger_accounts` | id, owner_type/id, currency, account_class | Operational control-account meanings approved by finance |
| `ledger_transactions` | id, business_operation_id, event_type, posted_at, reverses_id | Unique business posting; append-only after posting |
| `ledger_entries` | transaction_id, account_id, debit_minor, credit_minor | Exactly one side positive; transaction balances per currency at posting |
| `event_inbox` | provider/account/environment, event_id, payload_hash, received_at, state | Unique external event identity; payload conflict quarantined |
| `event_outbox` | id, aggregate_id/version, event_type, payload_ref, published_at | Created with the corresponding business transition |
| `reconciliation_cases` | id, type, refs, difference_minor, owner, age, resolution_evidence | No unexplained balancing entries |
| `support_cases` | id, order_id, category, evidence_refs, status, owner | Support cannot directly edit orders or mark payments settled |
| `audit_events` | actor, action, object, version, result, correlation_id | Redacted append-only evidence with defined retention |
| `cost_events` | session/order/leg, cost_type, amount, VAT_basis, source | Includes failures, human assistance and non-converting sessions |

### 7.3 Monetary constraints

Implement these in trusted transactional posting/operation code with database enforcement where practical:

```text
sum(ledger debits) = sum(ledger credits), for each posted transaction and currency
captured amount <= effective customer authority for the original charge
captured amount <= provider authorisation, where that concept applies
refunds completed + refunds in flight <= refundable amount
sum(order-line and fee allocations) = customer charge amount
no posted entry can be updated or deleted by an application role
one original economic operation cannot produce two distinct successful charges
one provider settlement line cannot be imported twice
```

A refund does not automatically replenish permission to buy another basket. A replacement purchase needs fresh customer authority unless an expressly approved amendment covers it. Dispute/chargeback exposure is accounted for separately from ordinary refunds so simultaneous processes do not produce an unnoticed double reimbursement.

A cross-row balance invariant cannot be implemented by a simple row-level `CHECK` alone. Use a transactionally controlled posting procedure or equivalent validated mechanism; revoke direct application writes that could bypass it.

### 7.4 Data not to store in the main commerce database

Do not place raw card security codes, payment credentials or biometric templates here. Store KYC-provider references and necessary verification results rather than indiscriminately copying source documents. Keep raw user media, addresses, legal evidence and analytics in appropriate access/retention classes. Record only the minimum model inputs and outputs needed for troubleshooting and accountability.

## 8. State machines

The following states are a **proposed implementation contract**, not provider status names. Each adapter maps verified provider states into these records while retaining the original event/status for audit.

### 8.1 Quote and reservation

```text
Quote projection:
DRAFT -> ESTIMATE -> FIRM -> APPROVED -> EXECUTING -> CONSUMED
                    |          |
                    +-> EXPIRED+-> INVALIDATED / REPLACED

Reservation:
REQUESTED -> HELD -> CONSUMED
     |         +-> RELEASE_REQUESTED -> RELEASED
     |         +-> EXPIRED
     +-> REJECTED / UNKNOWN
```

The quote payload never changes. `REPLACED` links to a new version. `UNKNOWN` requires merchant lookup or verified manual contact, not another reservation/order with a new reference.

### 8.2 Parent purchase and merchant leg

```text
Parent purchase:
CREATED -> PREPARING -> AWAITING_APPROVAL -> PAYMENT_PENDING
        -> COMMITTING -> FULFILLING -> COMPLETED

Branches:
PREPARING / AWAITING_APPROVAL -> EXPIRED / CANCELLED
PAYMENT_PENDING / COMMITTING -> NEEDS_ATTENTION / COMPENSATING
FULFILLING -> PARTIAL / COMPENSATING / DISPUTED

Merchant leg:
DRAFT -> RESERVED -> COMMIT_REQUESTED -> ACCEPTED -> PICKING
      -> READY_FOR_COLLECTION -> COLLECTED -> DELIVERED

Branches: REJECTED, CANCEL_REQUESTED, CANCELLED, FAILED, UNKNOWN
```

`ACCEPTED` must have a contractually defined meaning. It does not, by itself, imply that payment is captured, goods are picked or the courier is booked. A parent can show a delivered leg and a refund-pending leg at the same time.

### 8.3 Financial operations

Represent each economic operation separately: authorise, capture, immediate charge, void, refund, payout and adjustment. Each has its own identifier, amount, external reference and lifecycle:

```text
CREATED -> QUEUED -> SUBMITTED -> SUCCEEDED
                         +-> PENDING
                         +-> FAILED_FINAL
                         +-> UNKNOWN -> RECONCILING
```

Do not use a single `payment_status` to mean authorisation, charge and settlement simultaneously. The purchase has a financial summary derived from the underlying operations, for example `authorised_minor`, `captured_minor`, `refund_pending_minor`, `refunded_minor` and `settled_minor`.

A refund cannot rewrite a successful charge as though the charge never happened. It is a new operation linked to it.

### 8.4 Delivery and refund

```text
Delivery:
QUOTED -> BOOK_REQUESTED -> BOOKED -> COLLECTING
       -> IN_TRANSIT -> DELIVERED
Branches: BOOKING_UNKNOWN, CANCEL_REQUESTED, CANCELLED, FAILED, DISPUTED

Refund case:
REQUESTED -> ASSESSED -> APPROVED -> SUBMITTED -> PROVIDER_CONFIRMED
Branches: REJECTED_WITH_REASON, PENDING, UNKNOWN, FAILED_REQUIRES_ACTION
```

Where the provider can establish only submission rather than customer receipt, the interface must say so. The status name must not imply more evidence than exists.

### 8.5 Transition control

Every state transition checks actor authority, current version, required evidence and allowed predecessor. Optimistic version checks or locks prevent stale actors from overwriting current state. Late events are evaluated against the full history; they are not ignored just because they arrive after a locally final-looking state.

For example, a late successful debit after cancellation creates a refund obligation and incident, not an unlogged discrepancy.

## 9. Transaction workflows and compensation

### 9.1 Recommended general sequence

1. **Interpret:** convert the customer's list into structured requests and confirm ambiguities.
2. **Discover:** use participating merchant offers and eligible delivery options.
3. **Prepare:** obtain merchant stock/price reservations and viable delivery quotes; clearly mark anything unconfirmed.
4. **Quote:** create an immutable, complete basket with an expiry that respects all dependencies.
5. **Approve:** show the trusted snapshot and collect customer approval for its exact conditions.
6. **Pay:** follow the selected rail's approved branch below.
7. **Commit:** confirm the merchant orders exactly once per logical leg, with evidence and lookup/recovery support.
8. **Fulfil:** pick, verify, collect, deliver and record exceptions.
9. **Settle/reconcile:** follow the actual provider and merchant agreement, not an imagined release switch.
10. **Resolve:** complete cancellations, refunds and disputes while retaining the complete history.

Preparation may involve a human merchant operator. Their action is authenticated and time-stamped and has the same contract as an API adapter response.

### 9.2 Branch A - approved card authorisation/capture

**Recommendation:** Reserve merchant inventory first, approve the quote, then authorise the card through provider-hosted checkout. Revalidate the reservations and approved delivery plan after payment authentication. Confirm the required merchant commitments, then capture the permitted total through the provider's supported capture mode.

If any required commitment fails before capture, void/reverse the unused authorisation and release the reservations. A submitted void is not a guarantee that the bank's hold has already disappeared.

If capture succeeds but a merchant later fails, use the agreed refund/compensation path. If capture fails after merchants committed, execute the contracted release/cancellation path; do not silently dispatch unpaid goods. A capture timeout requires lookup before any replacement charge.

Use **one final accepted-total capture** initially if the product supports it and the topology permits it. Multiple leg captures add complexity and are not a requirement merely because the basket has two retailers.

### 9.3 Branch B - immediate payment

Reserve and confirm eligible goods first; approve the final quote; create the immediate-payment request. On authoritative successful payment evidence, revalidate reservations and commit the order. If the payment arrives after a hold expires, pause the order and verify supply rather than assuming it still exists.

If fulfilment cannot be secured inside the customer's approved conditions, initiate the applicable refund using the original payment reference. A top-up of an operational refund float is a company liquidity action, not a customer wallet feature.

**Important:** A normal bank-app payment permission is not a delayed-capture authorisation. The adapter must never return a fabricated `AUTHORISED` status to make this rail fit Branch A.

### 9.4 Unknown state and safe retries

A timeout says the response was not received; it does not establish that the provider did nothing. Persist the operation ID, exact request digest, idempotency key and any provider reference before sending.

Stitch currently documents a 24-hour idempotency-key retention period and requires identical retries. It also warns against assuming a retry beyond that period replays the earlier result. [S13]

**Recommendation:** Internal operation records outlive provider retry windows. After an ambiguous result, query by external/merchant reference or use the documented safe replay inside the supported horizon. After the horizon, block automatic replay until reconciliation establishes the state. Escalate rather than issue a fresh key because a user pressed Buy again.

### 9.5 Compensation matrix

| Failure | Immediate action | Financial action | Customer explanation |
|---|---|---|---|
| Merchant rejects before payment | Release other holds as required; revise quote | None | Basket changed; approval required |
| Card authorised, mandatory merchant rejects | Cancel uncommitted legs | Void unused authorisation | Hold release requested; no goods charge captured |
| Immediate payment succeeds, stock unavailable | Stop dispatch; verify alternatives only with permission | Refund affected amount or whole basket under policy | Paid amount and refund status shown separately |
| One retailer fails after the other commits | Apply approved partial/complete policy; contact operations | Refund/compensate according to actual commitments | Identify fulfilled and failed parts honestly |
| Courier booking response lost | Look up the booking | No duplicate courier charge until status known | Collection confirmation pending |
| Courier fails after collection | Activate custody/claims workflow | Remedy as required; recover from liable party separately | Trollie owns the support case |
| Customer cancels during payment | Mark cancellation requested; reconcile payment | Void or refund according to observed result | Request received; outcome pending |
| Provider callback says success twice | Deduplicate and verify | One posting for the economic event | No duplicate customer notification/charge |
| Refund request times out | Query existing refund | No second refund or fresh-key replacement blindly | Refund verification in progress |
| Provider payout fails | Keep payable open and investigate destination/status | Controlled retry only after final failure established | Merchant sees unsettled amount |

A compensating action is not a time machine. Completed captures, picked goods and courier work may incur costs even when the customer ultimately receives a refund. Those costs enter contribution and the incident record.

## 10. API contracts

**Status:** Proposed internal HTTP contract, not an assertion about any provider's actual endpoint names. Provider adapters translate these operations to their independently verified APIs.

### 10.1 Customer and agent endpoints

| Endpoint | Caller | Contract |
|---|---|---|
| `POST /v1/shopping-sessions` | Customer / channel adapter | Create list context; no payment authority |
| `POST /v1/shopping-sessions/{id}/items` | Customer or restricted agent | Structured requests; server validates quantities and ownership |
| `POST /v1/shopping-sessions/{id}/quotes` | Customer or restricted agent | Request candidates; async response allowed; no invented prices |
| `GET /v1/quotes/{id}` | Authorised account | Server-renderable immutable quote and current validity |
| `POST /v1/purchase-requests` | Restricted agent | Reference a quote for the user's attention; cannot approve or pay |
| `POST /v1/quotes/{id}/approval-challenges` | Authenticated customer session | Single-use challenge for current quote/hash |
| `POST /v1/approvals` | Customer | Verify WebAuthn assertion, origin, account, challenge, conditions and freshness |
| `POST /v1/orders` | Customer / trusted orchestrator | Consume valid approval; idempotently start the permitted execution |
| `POST /v1/orders/{id}/checkout-sessions` | Trusted service for authorised customer | Return provider-hosted checkout reference; no card data returned |
| `GET /v1/orders/{id}` | Customer | Parent/leg/delivery/financial status and evidence-backed messages |
| `POST /v1/orders/{id}/cancellation-requests` | Customer | Create request; not immediate proof of cancellation |
| `POST /v1/orders/{id}/issues` | Customer | Missing/wrong/damaged delivery case; attachment restrictions |
| `GET /v1/orders/{id}/receipts` | Customer | Seller receipts and platform fee documents by entitlement |

No public endpoint accepts an arbitrary bank account or payment beneficiary. Refund destination comes from the approved original-payment flow and any independently verified exception process.

### 10.2 Merchant contract

Each adapter or portal implementation provides:

`get_offers`, `prepare_reservation`, `get_reservation`, `release_reservation`, `commit_order`, `get_order`, `cancel_order`, `propose_substitution`, `mark_ready`, `get_receipt` and `resolve_issue`.

`commit_order` receives a server-generated business reference and an accepted quote/reservation reference. It must support deduplication or reliable lookup by that reference. When a merchant cannot provide either, automatic retry is disabled and the integration remains assisted.

An incoming merchant event cannot change a beneficiary, raise a maximum total, choose a new customer address or authorise a substitution.

### 10.3 Financial and event endpoints

Financial commands are internal-only and require service identity plus a persisted authorised operation:

`submit_authorisation`, `submit_capture`, `submit_charge`, `submit_void`, `submit_refund`, `query_operation`, `ingest_settlement_report`.

External event endpoints verify the correct provider/account signature over the original request representation before parsing into trusted events. Invalid events are rejected; valid events enter the inbox and are processed asynchronously. Provider callbacks and browser return URLs are not interchangeable. [S04]

### 10.4 Example authoritative quote

**Synthetic example:** R600 of goods at Store A, R400 at Store B, R40 delivery per leg and a R20 customer service fee. Merchandise commission, if any, is a merchant settlement deduction rather than an additional customer charge. All amounts below are cents. This is a shortened payload; item snapshots and evidence are referenced rather than reproduced.

```json
{
  "quote_id": "q_demo_001",
  "version": 1,
  "currency": "ZAR",
  "account_id": "acct_demo_001",
  "address_version_id": "addr_demo_v3",
  "strategy": "balanced",
  "fulfilment_policy": {
    "mode": "complete_required",
    "allow_new_merchants": false,
    "allow_new_items": false,
    "allow_fee_increase": false
  },
  "legs": [
    {
      "leg_id": "leg_a",
      "seller_id": "seller_a",
      "merchant_location_id": "location_a",
      "item_snapshot_id": "items_a_v1",
      "reservation_id": "res_a_001",
      "goods_minor": 60000,
      "delivery_minor": 4000,
      "delivery_window_id": "window_a"
    },
    {
      "leg_id": "leg_b",
      "seller_id": "seller_b",
      "merchant_location_id": "location_b",
      "item_snapshot_id": "items_b_v1",
      "reservation_id": "res_b_001",
      "goods_minor": 40000,
      "delivery_minor": 4000,
      "delivery_window_id": "window_b"
    }
  ],
  "customer_service_fee_minor": 2000,
  "tip_minor": 0,
  "discount_minor": 0,
  "total_minor": 110000,
  "maximum_payable_minor": 110000,
  "expires_at": "2026-11-02T09:10:00Z",
  "terms_version": "pilot-terms-1",
  "approval_policy_version": "pilot-authority-1"
}
```

The hash covers the resolved immutable item/address/window/terms snapshots, not merely these references. The server must reject references whose underlying content is mutable or not included in the approved digest.

### 10.5 Error semantics

Use structured error codes such as `QUOTE_EXPIRED`, `RESERVATION_EXPIRED`, `REAPPROVAL_REQUIRED`, `MUST_HAVE_UNAVAILABLE`, `CAPABILITY_NOT_ENABLED`, `PROVIDER_STATE_UNKNOWN`, `DUPLICATE_OPERATION_CONFLICT`, `INSUFFICIENT_REFUND_RESERVE` and `MERCHANT_SUSPENDED`.

Return `202` when an operation is durably accepted but still pending. Return a conflict for the same idempotency key with changed semantic content. Preserve the original operation response for exact replays. Never return a generic success message that the model can mistake for delivered goods or completed payment.

## 11. Product matching and optimisation

### 11.1 Canonical identity before prices

Retain the PRD's split between products and offers. Match verified product identifiers and merchant mappings before using fuzzy descriptions. Record uncertainty instead of allowing a model to certify identity from packaging alone.

Examples requiring clarification: 2 litres versus two 2-litre bottles; a single unit versus a multipack; full cream versus low fat; a preferred brand versus a mandatory dietary restriction. A lower unit price does not authorise buying a larger total quantity.

Only confirmed catalogue records can become order lines. Shelf photos and voice notes create draft interpretations, not an orderable source of truth.

### 11.2 Feasibility is a hard constraint

For each candidate, require product/quantity compatibility, acceptable merchant status, usable reservation evidence, permitted price/promotion, serviceable destination, merchant readiness, suitable courier capacity and customer timing constraints.

Reject a solution when any hard constraint cannot be satisfied. Do not convert hard requirements into a small penalty that an optimiser can trade for a cheaper basket.

### 11.3 Objective functions

For a feasible candidate `x`:

```text
customer_total(x) = goods_inclusive_of_applicable_tax
                  - applicable_discounts
                  + delivery_charges
                  + disclosed_service_and_other_fees
                  + approved_tip

cheapest = minimise customer_total(x)
fastest_complete = minimise latest_delivery_completion_time(x)
balanced = minimise customer_total(x) subject to customer time and split limits
```

For equivalent solutions, deterministic tie-breaks can prefer fewer deliveries, fresher confirmed data and higher measured fulfilment reliability. Disclose relevant policy choices. Never insert merchant commission into an undisclosed preference while labelling the result cheapest.

### 11.4 Solving a two-store basket

With five eligible stores, evaluate five single-store sets and ten two-store sets. Within a set, assign purchasable packs to requested quantities subject to promotions, minimum spends and stock; integer programming or a bounded exhaustive solver for small baskets can be appropriate.

The fifteen store sets do **not** mean there are only fifteen item assignments. Promotions and assignments still make the inner problem nontrivial. Compare the implementation against exhaustive small-instance oracles. A greedy item-by-item minimum can fail once delivery thresholds and bundle discounts apply.

On solver timeout, present a feasible incumbent only if it satisfies every hard rule, and label it the best evaluated option rather than a proven global minimum. If none exists, explain the blocking constraints.

### 11.5 Savings evidence

Store the comparator basket, time, merchant locations, exact quantities, applicable customer benefits, availability and delivery conditions. Report price savings, total delivered savings and delivery-count change separately.

An unavailable comparator, a different pack size or an unearned loyalty discount is not a valid savings baseline. Keep quoted savings and realised savings separate. Do not quietly remove unfulfilled items from both baskets to manufacture a favourable percentage.

## 12. Merchant and delivery operations

### 12.1 Merchant readiness is operational, not just technical

Before activation, verify catalogue accuracy, picking ownership, device/portal access during trading hours, stock hold procedure, packing cost, readiness notifications, cancellation procedure, receipts, refund responsibility and a named escalation role.

Pilot support can correct a catalogue draft with merchant approval. It cannot pretend that a late WhatsApp response is live inventory or mark goods reserved without someone actually making the commitment.

A merchant pause blocks new orders but leaves existing order support, refunds and settlement visible.

### 12.2 Separate deliveries

Each leg has its own collection readiness, fee, window, courier reference, package identifier and proof of delivery. The customer sees that two deliveries are coming before approval.

Define whether a failed delivery leg permits the other to proceed. Delivery to a neighbour, security desk or alternate address must follow the customer's approved recipient rules; a driver cannot unilaterally redefine the approved destination.

### 12.3 Consolidated collection

Enable only after proving multi-pickup quoting and booking, vehicle capacity, merchant readiness synchronisation, waiting charges, route order, package separation, collection evidence and liability.

The router compares the **actual** consolidated route quote against separate legs. Do not assume one courier trip costs one ordinary delivery fee. A late store can delay the whole route and degrade the customer's total experience.

No hub is required for a two-pickup courier route. A hub would add custody, storage and handling obligations and is a separate operational design, not a default shortcut.

### 12.4 Category and location scope

Keep ambient-only restrictions in catalogue eligibility and fulfilment checks, not merely a marketing disclaimer. Test damaged packaging, expiry dates, recalls and wrong-product complaints even for ambient goods.

Separate `nearby` from `serviceable`. Route duration, store cut-offs, building access, address quality and courier capacity can make a physically close store unsuitable.

### 12.5 Operations evidence

For each pilot basket, retain the approved quote, merchant acceptance/reservation evidence, actual picked list, authorised substitutions, collection record, delivery outcome, payment record, settlement match and support time. Do not store unnecessary identity documents or unredacted financial credentials as proof.

## 13. Security, privacy and identity

### 13.1 Approval implementation

WebAuthn provides credential-based authentication with user-verification options; it does not itself prove that a particular grocery basket was displayed. User verification can involve a PIN or biometric mechanism, and biometric data is not disclosed to the relying party. [S08]

**Recommended implementation:** Render the approval view from the server's immutable quote, bind a random single-use challenge to its resolved hash, require user verification, and verify the assertion using a maintained library with explicit expected origin, relying-party ID, credential/account binding and expiry checks. Consume the challenge and create the approval atomically.

Do not require the app to collect fingerprints. Do not make Face ID the only supported user experience. Recovery, shared-device use, synced credentials and revoked devices need explicit tests. A customer account is not safely recovered merely because someone now controls its former phone number.

### 13.2 Model permissions

The model may read a bounded product/offer view and submit a structured proposal. It may not create merchants, change payout details, insert approvals, issue bank transfers, decide refunds or alter policy.

Tools accept identifiers resolved by trusted services. Disallow arbitrary URL fetching and merchant-supplied checkout destinations. Prices, totals, discounts, identities and permissions are reconstructed from system records rather than trusted because the model repeated them.

Treat product descriptions, uploaded photos, OCR output, merchant notes, retrieved text and prior model summaries as untrusted inputs. Test attempts to poison preference memory or change what the customer sees before approval, not only attempts to invoke a payment tool.

### 13.3 Customer and merchant account abuse

Proposed controls include per-account and per-merchant limits, duplicate intent detection, related-party review, payout-destination change verification, refund-to-source controls and restricted financial actions during account recovery.

Human operators cannot approve on behalf of customers through a support-console shortcut. Exceptional recovery or destination changes require a separate approved process with evidence, dual control where appropriate and visibility to the customer.

A verified merchant can still collude with a customer. Removing wallet-to-wallet transfers does not remove sham-order or refund-diversion risk.

### 13.4 Privacy scope

Retain the source's purpose-specific memory and data separation. Implement a data register for chat, media, product preferences, delivery addresses, identity checks, transaction authority, receipts, fraud records and support evidence.

Each class has an owner, lawful-basis assessment, access policy, storage/processing locations, operator contracts, retention trigger and deletion/legal-hold behaviour. User deletion cannot be implemented by silently removing required transaction evidence; equally, audit needs do not justify permanent retention of all raw chats.

Use encrypted data keys and narrow service access, but do not claim that encryption renders a breach harmless when a compromised service can legitimately decrypt broad records.

### 13.5 Channel policy is a release dependency

The reviewed WhatsApp Business policy requires appropriate opt-in, templates outside the service window, escalation paths for automation and restrictions on requesting sensitive identifiers. It also applies commerce-policy requirements to commerce experiences. [S14]

**Unresolved:** The complete linked Business Platform terms were not accessible in this check. Consequently this review does not certify Trollie's eligibility under any separate AI-provider/marketplace provisions, or the PRD's October 2026 pricing assertion. Keep a dated channel assessment and current account rate card as launch evidence. A shopping-only prompt is not proof of policy compliance.

Keep web receipts, order status and support usable during a WhatsApp outage or suspension. Channel loss pauses new channel-originated activity if necessary, not customer access to money and complaint resolution.

### 13.6 Operational security

Use environment-separated credentials and provider accounts, restricted egress, signed/verified webhooks, dependency and secret scanning, least-privilege database roles, redacted telemetry, tested backups, authenticated merchant tools and a controlled deployment process.

The kill switch disables **new economic commitments** and unsafe retries. It must not disable reconciliation, security logging, receipts, support or properly controlled refunds. Define separate switches per merchant, payment product, category and geography so a local incident need not unnecessarily disable everything.

## 14. Reconciliation, refunds and operating reserves

### 14.1 Ledger scope without a wallet

A no-wallet pilot still requires reliable financial records. Those records track charges, obligations, commission, refunds, settlements and fees. They do not create a stored-value account merely by being called a ledger.

The legal ownership of each control balance must follow the actual contracts and funds flow. Where providers settle merchants directly, maintain a reconciled operational mirror rather than implying that Trollie holds the funds as its own assets. Formal balance-sheet presentation is a finance/accounting decision.

### 14.2 Illustrative allocation example

Using the synthetic R1,100 quote from Section 10:

| Component | Customer amount / allocation |
|---|---:|
| Store A goods | R600.00 |
| Store B goods | R400.00 |
| Delivery, both legs | R80.00 |
| Customer service fee | R20.00 |
| **Customer total** | **R1,100.00** |

Assume for this illustration that merchant commission is 5% VAT-inclusive on goods and Trollie is VAT-registered. Store A commission is R30 and Store B commission R20. Their net goods proceeds before any separately allocated provider fees are R570 and R380. Delivery receives R80. The platform's gross fee/commission allocation is R70. These sum to R1,100.

R70 of standard-rated VAT-inclusive fees corresponds to R60.87 net platform fee revenue and R9.13 VAT, subject to invoice-level rounding and the actual approved tax treatment. Goods VAT belongs to the relevant supplies and is not calculated by applying 15% to the entire R1,100. The standard VAT rate is sourced separately; the arrangement is an illustration, not tax advice. [S11; CALC]

This allocation example is **provider-neutral**. It must not be read as a claim that the reviewed Stitch interface can settle all four parties directly.

### 14.3 Illustrative posting logic

For an approved control-ledger model, a collection can first allocate gross obligations to the retailers, delivery party and deferred platform fee. The commission contract then determines when merchant payable is reduced and commission revenue/tax recognised; fulfilment/service conditions determine when the customer service fee is earned.

Processing fees are separate entries allocated to the contractually responsible party. Refunds and chargebacks use new compensating entries, not edits to the original sales record. Do not record GMV as platform revenue just because it passed through the payment request.

This is posting guidance, not a substitute for a signed chart of accounts. Reconciliation must work for the chosen topology, including provider-direct settlement where no customer collection reaches Trollie's bank account.

### 14.4 Four-way reconciliation

Reconcile:

1. Authorised purchase and actual merchant goods supplied.
2. Provider payment/refund/dispute events and financial reports.
3. Internal operation records, allocations and ledger.
4. Actual bank/beneficiary settlement evidence available under the provider model.

Classify differences: missing event, duplicate event, fee discrepancy, wrong beneficiary, partial refund allocation, failed payout, timing difference, chargeback, merchant short supply or manual adjustment.

Every break has an owner, ageing clock, amount, reference set and resolution evidence. A timing difference is not automatically a loss, but it cannot disappear from reporting while unresolved.

### 14.5 Refund responsibility and cash availability

Separate four questions: who owes the customer, who submits the refund, whose account funds it now, and who ultimately bears the cost. These answers can differ.

Ozow's current refund guide requires an adequately funded refund float and appropriate refund scope. That is an account capability and liquidity requirement, not a promise of universal instant customer credit. [S05]

For every approved refund, record the original payment, economic retailer allocation, provider allocation, fee treatment, expected timing and current evidence. Do not send a second compensating bank payment simply because a card refund is slow; that can reimburse the customer twice.

### 14.6 Reserve design

**Recommendation:** Finance approves a reserve based on peak unsettled refund obligations, merchant-default exposure, chargebacks, courier incidents and settlement delays, avoiding double counting. Available liquidity means funds the company can lawfully deploy, not another customer's balance or a theoretical future commission.

A reserve breach blocks new commitments that increase uncovered exposure. Existing customer obligations remain visible and must still be resolved. Define escalation to the responsible finance/operations owner.

The source's R500,000 timing-gap example is conditional: 500 daily orders x R500 x two days produces that gross exposure only where Trollie must fund relevant obligations before incoming settlement. It is not automatically required under a direct-to-merchant provider settlement model. [PRD; CALC]

## 15. Observability and support

### 15.1 Instrument the whole funnel

Every event carries session, quote, order, leg, financial-operation and correlation identifiers where applicable. Model usage is attributed to all sessions, not only completed orders.

Operational events include list received, clarification required, quote requested, coverage calculated, reservation confirmed/expired, quote displayed, approval attempted/verified, payment submitted, payment unknown, merchant committed, picking ready, courier collected, delivery completed, issue opened, refund submitted/confirmed and reconciliation completed.

### 15.2 Initial dashboards

| View | Required measures |
|---|---|
| Customer funnel | Real-list coverage, clarification rate, quote-to-approval conversion, payment abandonment |
| Merchant | Acceptance latency, reservation reliability, substitutions, pick time, short supply |
| Delivery | Quote validity, booking failures, collection wait, final-delivery time, failed handover |
| Money | Unknown operations, unmatched settlements, refund age, duplicate-effect incidents, reserve coverage |
| Model | Per-session cost, extraction error, tool failure, hard-constraint violation, latency |
| Economics | Contribution by one/two-store basket, delivery mode, cohort, subsidy and support effort |
| Support | Open cases, minutes per order, resolution age, repeat contact, unresolved customer harm |

### 15.3 Customer-facing status

Generate financial and delivery messages from validated state projections. The model may explain those projections but cannot create facts such as "your refund has arrived" or "your order is confirmed" without the necessary evidence.

Acknowledgement latency under three seconds is distinct from producing a fresh multi-store quote. Report median and tail latency for both. During outages, provide truthful progress and a durable status page rather than a fabricated immediate answer.

### 15.4 Support permissions

Support can inspect redacted evidence, communicate with merchants, request a revised quote, open a refund assessment and trigger an approved recovery workflow. Support cannot change an approved price, change a beneficiary, mark a payment as settled without evidence, delete ledger entries or consent for a customer.

Record human assistance as cost even when the founder performs it. Otherwise the pilot can appear profitable only because operational labour is unpriced.

## 16. Corrected commercial model

### 16.1 Reproduce the source model before changing it

The PRD assumes one merchant, R50 delivery passed through at zero margin, net payment cost of 1.5% on goods plus delivery, R3 merchant settlement plus R3 courier settlement, R3 AI/messaging, R5 support and a 0.5% loss allowance. Commission is VAT-inclusive. No subscription, interchange, float or subsidy is included.

Let `G` be goods value and `r` the commission fraction. Reproducing those assumptions:

```text
CM = rG / 1.15 - 0.015(G + 50) - 6 - 3 - 5 - 0.005G
   = (r / 1.15 - 0.020)G - 14.75
```

The 1.15 divisor assumes a VAT-registered platform and standard-rated fee. Cost inputs must consistently exclude recoverable VAT where applicable; actual cash settlement and input-tax timing need a separate model. The goods basket may contain different VAT treatments. [S11; PRD; CALC]

| Goods basket | 5% commission contribution | After an additional R35 subsidy |
|---|---:|---:|
| R150 | -R11.23 | -R46.23 |
| R500 | -R3.01 | -R38.01 |
| R1,000 | R8.73 | -R26.27 |
| R2,000 | R32.21 | -R2.79 |

Approximate goods-value break-even under the same assumptions: **R2,423.21 at 3% commission; R628.24 at 5%; R297.59 at 8%**. These are model outputs, not commercial validation. If the variable contribution coefficient is zero or negative, a larger basket cannot repair the model without changing costs or revenue.

### 16.2 Multi-retailer sensitivity

For a deliberately simple extension, assume each merchant settlement costs R3, each courier settlement costs R3, and other costs remain unchanged:

```text
CM = rG / 1.15 - 0.015(G + D) - 3M - 3C - 3 - 5 - 0.005G - S
```

`D` is customer delivery charges with exactly offsetting delivery cost; `M` is paid merchant beneficiaries; `C` is paid courier beneficiaries; `S` is additional subsidy. This assumption may not match a selected provider's pricing.

At G = R2,000 and r = 5%:

| Illustrative operating case | D | M | C | Contribution before subsidy |
|---|---:|---:|---:|---:|
| One store, one delivery | R50 | 1 | 1 | R32.21 |
| Two stores, two separately paid delivery legs | R100 | 2 | 2 | R25.46 |
| Two stores, one consolidated courier allocation | R70 | 2 | 1 | R28.91 |

The R70 consolidated route is an invented sensitivity input, not a market rate. The table holds goods spend constant; actual split-basket savings change both customer total and commission. Real splitting can also add picking, waiting, packaging, refund and support costs omitted from this simplified extension.

### 16.3 Conversion and support sensitivity

If an average shopping session costs R3 and only one in five sessions converts, equal-cost sessions imply R15 of session cost per conversion, not R3. Actual abandoned sessions may cost more or less; instrument them.

A support cost increase from R5 to R20 removes R15 from contribution. Non-returned processing fees, refund fees, incentives and goodwill remedies reduce it further. A merchant paying commission may have different margin and service-cost constraints by category.

### 16.4 Required live economics dataset

For each completed, cancelled and refunded attempt, collect goods value, net platform fees, merchant commission, processing and settlement costs, delivery revenue/cost, model and channel usage, human handling, packaging, refund and dispute costs, subsidy, loss and applicable tax treatment.

Report contribution before acquisition, acquisition cost per activated household, and cohort contribution after acquisition separately. Do not equate GMV, revenue, contribution, cash flow and founder income.

**Decision:** The PRD's illustrative economics support testing larger baskets; they do not yet support scaling or subsidising every small order.

## 17. Acceptance tests

**Status:** Proposed executable acceptance catalogue. These tests have not been run against a Trollie implementation because no implementation or provider credentials were supplied. Arithmetic and document-integrity checks are described in Appendix B.

| ID | Scenario | Required outcome |
|---|---|---|
| T01 | Exact item and verified mapping | Correct product, variant, pack and seller snapshot |
| T02 | 2 litres versus two 2-litre bottles | Ambiguity clarified; no silent quantity increase |
| T03 | Low-confidence shelf-photo match | Draft only; cannot become orderable without confirmation |
| T04 | Locked item unavailable | No unapproved substitute |
| T05 | Mandatory item fails in allow-partial basket | Whole commitment pauses for revised authority |
| T06 | Optional item removed under explicit permission | Only permitted removal; totals and fees remain valid |
| T07 | Near-zero stock observed but no hold | No firm-reservation claim |
| T08 | Reservation expires during 3DS | Revalidate; do not commit based on expired hold |
| T09 | Immediate payment arrives after expiry | Reconcile payment; recover supply or initiate correct refund |
| T10 | Merchant falsely reports or later loses reserved stock | Incident and remedy; reliability recorded, not hidden |
| T11 | Delivery threshold changes optimal store split | Known-answer optimum matches oracle |
| T12 | Promotion requires ineligible loyalty membership | Discount excluded |
| T13 | VAT-inclusive price enters optimiser | No second VAT addition |
| T14 | Larger pack has lower unit price | Cannot exceed permitted quantity merely to save per unit |
| T15 | Solver timeout with feasible incumbent | Honest best-evaluated label; constraints still satisfied |
| T16 | Cheapest basket cannot meet deadline | Excluded from feasible options |
| T17 | Fast first leg, slow final leg | Fastest-complete objective uses the final required delivery |
| T18 | Quote amount/item/address/window altered after approval | Authority rejected or fresh approval required |
| T19 | Mutable address record changes behind ID | Immutable approved address version remains authoritative |
| T20 | Replayed approval assertion | Second consumption rejected |
| T21 | Wrong WebAuthn origin/account/credential | Approval rejected |
| T22 | PIN-supported device without Face ID | Works through approved verification path; no raw biometric collection |
| T23 | Recycled phone number recovery | No silent takeover or spending permission |
| T24 | Parallel order requests from same approval | One logical purchase execution |
| T25 | Same idempotency key, changed payload | Conflict; no second economic effect |
| T26 | Provider accepts charge, response times out | Lookup/replay safely; no new-key duplicate charge |
| T27 | Unknown operation exceeds provider idempotency horizon | Automatic resend blocked; reconcile/escalate |
| T28 | Duplicate or out-of-order webhook | Idempotent state/posting; later valid financial evidence retained |
| T29 | Invalid webhook signature | Rejected/quarantined; no state change |
| T30 | Callback says success, provider lookup conflicts | Reconciliation case; no automatic dispatch from ambiguous evidence |
| T31 | Two destinations submitted to single-destination product | Capability gate rejects before live call |
| T32 | Retailer-specific refund on proportional provider split | Economic allocation reconciles; other retailer not left bearing wrong cost |
| T33 | Multiple partial refunds race | No refund beyond remaining entitlement |
| T34 | Refund timeout followed by user retry | Same logical refund, not a second reimbursement |
| T35 | Refund and chargeback overlap | Finance detects potential double recovery; controlled resolution |
| T36 | Merchant payout fails or is unknown | Payable remains; safe retry/reconciliation |
| T37 | Full basket fails before capture | Void requested, holds released, no fictional instant bank release |
| T38 | One leg fails after another is committed | Agreed compensation policy; customer sees both statuses |
| T39 | Cancellation races with capture | Observed financial outcome determines void/refund; no lost obligation |
| T40 | Courier booking times out | Lookup by reference; no duplicate courier dispatch |
| T41 | Consolidated pickup second store late | Contracted wait/failure policy; no unapproved customer surcharge |
| T42 | Delivery to unapproved alternate address | Rejected or separately authorised |
| T43 | Missing/damaged package | Evidence, remedy and merchant/courier liability workflow |
| T44 | Product recall affects previously delivered order | Affected customer/order identification and response workflow |
| T45 | Merchant description contains malicious instruction | No permission, payee, address or total change |
| T46 | Malicious URL in product/media | Egress policy prevents unauthorised fetch |
| T47 | Model claims successful payment without evidence | Customer projection ignores fabricated financial state |
| T48 | Model poisons stored preference | No unconfirmed permanent memory promotion |
| T49 | Another account's UUID supplied | Cross-tenant access denied |
| T50 | Restore after outbox committed but before dispatch | Work resumes with idempotent external operations |
| T51 | Restore after provider accepted but before local write | Reconcile before replay; no duplicate charge |
| T52 | Ledger posting would be unbalanced | Posting rejected; money path paused and alerted |
| T53 | Settlement report imported twice | No duplicate postings or payouts |
| T54 | Unexplained financial discrepancy | Owned exception; no manual fudge entry |
| T55 | WhatsApp unavailable | Web status, receipts and support remain accessible |
| T56 | User submits ID/card details in chat | Sensitive-data handling path; no model/log propagation |
| T57 | Non-converting sessions consume AI/support | Costs included in completed-order economics |
| T58 | Low reserve or support overload | New exposure limited; refunds/support/reconciliation continue |
| T59 | Language-specific money/quantity extraction fails | Clarification; no silent commitment |
| T60 | Entire requested list exceeds ambient pilot coverage | Coverage gap disclosed; no false complete-grocery claim |

Use deterministic fixtures and repeated fault injection. Property-based tests should verify sums, caps, allowed quote transformations and state transitions over many generated inputs. Repeated simulation of an ideal happy path is not evidence that external-provider failure handling is correct.

## 18. Implementation milestones

These are proposed delivery gates, not elapsed-time promises. The source's 60-day validation plan and 8-12-week assisted phase should be reconciled into a single plan by the team; neither overrides legal or provider dependencies.

| Milestone | Build / activity | Exit evidence | Live-money permission |
|---|---|---|---|
| M0 - One baseline | Freeze scope, requirement IDs, customer promise, risk owners and evidence register | One authoritative spec; unresolved decisions explicit | None |
| M1 - Commercial feasibility | Merchant preparation/commitment workflow; provider topology exercise; courier offer | Two willing merchant pilot agreements; provider answers against exact graph; category/courier fit | None unless separately approved |
| M2 - Deterministic commerce spine | Product/offer model, matching, optimiser, reservations, quote snapshots, merchant portal | Known-answer baskets and two-store synthetic execution | None |
| M3 - Authority and durable operations | Approval binding, outbox/inbox, operation IDs, ledger posting, unknown-state handling | Security/concurrency/recovery tests pass in sandbox | None |
| M4 - Provider and fulfilment proof | Selected payment adapter, merchant adapters, delivery booking, refunds, statements | Provider conformance test including rejected leg and targeted refund | Only after live gates signed |
| M5 - Assisted end-to-end purchase | Real list, two merchants, real customer approval, paid order, delivery, settlement and support | Complete evidence bundle and measured handling cost | Bounded approved pilot |
| M6 - AI and channel automation | Intent extraction, multilingual clarification, WhatsApp entry, explanation | Accuracy by task/language/device; no new financial privilege | Within existing pilot scope |
| M7 - Cohort validation | Expand to the approved 50-100 household cohort and up to five operational merchants | Repeat use, full-list coverage, realised savings/time benefit, contribution and defects | Caps retained |
| M8 - Scale or revise | Decide on economics and reliability, not feature count | Signed scale decision and refreshed risk/capability evidence | Only approved expansion |

Non-payment customer prototypes and the fictional-merchant demo can proceed in parallel. They do not replace M4/M5 evidence. Assisted testing involving real charges is a live transaction and uses the same relevant gates as automated charges.

### 18.1 Suggested workstreams

**Commerce engineering:** catalogue, quote, optimiser, merchant workflow and orchestration.

**Financial integration:** provider capability profile, payment/refund adapters, ledger, reconciliation and settlement statements.

**Customer experience:** mobile approval/status, accessibility, WhatsApp channel, clear failure and refund messaging.

**Operations and compliance:** merchants, courier procedures, customer terms, identity allocation, reserve policy and support.

**Quality and security:** known-answer fixtures, fault injection, authority boundaries, recovery, monitoring and release evidence.

These are responsibilities, not prescribed headcount. One person may cover several initially, but release approval should not consist solely of the builder declaring their own financial controls correct.

### 18.2 First engineering proof

The most useful initial scenario is deliberately narrow:

> A household supplies a real list. Trollie prepares a complete basket at two participating stores, shows the named sellers and total delivered cost, obtains approval, executes the supported payment flow, coordinates both deliveries, and reconciles the receipts, fees and settlements. A second run deliberately makes one retailer fail, and demonstrates the promised recovery.

The first run proves utility. The second proves whether the product can be trusted.

## 19. Pilot measurement and stop conditions

### 19.1 Metric definitions

| Metric | Definition / denominator |
|---|---|
| Requested-list coverage | Requested items and quantities that participating merchants can supply within original constraints, before scope trimming |
| Quote success | Complete eligible quotes / eligible shopping attempts; publish ineligible attempts separately |
| Activation | Household completes its first delivered, non-refunded basket |
| Whole-basket fulfilment | All originally approved mandatory and selected items delivered under approved conditions / committed baskets |
| Permitted partial outcome | Committed baskets ending in an expressly authorised partial outcome; report separately, not as whole-basket success |
| Perfect order | Entire approved basket correct, within promised window, without support rescue or unresolved financial issue |
| Repeat rate | Activated households with a subsequent completed order within the stated period, among households with that full observation period |
| Realised net savings | Matched delivered-baseline total minus actual customer total, using a documented comparable basket |
| Time/convenience benefit | Customer-reported and observed effort reduction under a defined study procedure; not inferred from savings |
| Contribution | Net earned platform revenue minus attributable variable costs, including failed/refunded attempts and assistance |
| Refund latency | Time from applicable refund entitlement/approval to submission and separately to best available confirmation |
| Financial integrity | Unaudited/unmatched amount, age of breaks, duplicate charges, unauthorised spend and ledger violations |

The PRD's proposed 30% repeat and 5% savings targets remain **hypotheses**, not industry benchmarks. An ambient-goods cohort and a full-grocery cohort cannot be silently pooled. Record unsuccessful and manually rescued orders in the denominators.

### 19.2 Stop rules

**Immediate financial/security pause:** any unauthorised debit, duplicate economic effect, violation of a locked constraint, unbalanced posted ledger transaction, suspected credential exposure or confirmed approval bypass. Pause the affected scope; investigate wider compromise; continue legitimate refunds and reconciliation.

**Operational pause or cap reduction:** inability to establish payment status safely, merchant permission withdrawn, unsupported payment topology, inadequate refund liquidity, unserviceable delivery capacity or support backlog threatening promised remedies.

**Reliability target:** retain 95% accepted-order delivery as an initial management target, but state exactly whether it measures complete or explicitly permitted partial delivery. For a provisional dashboard rule, assess each batch of 20 resolved accepted orders and the cumulative cohort; below 95% triggers a review/pause of new cohort growth. This 20-order window is a recommendation, not statistically validated evidence of quality. A serious single incident can trigger a pause without waiting for the window.

**Scale gate:** demonstrated unsubsidised contribution and repeat use alongside acceptable service quality. No hard claim of national demand follows from a small pilot. Growing order count while founder support, refunds or delivery subsidy grow faster is not a pass.

### 19.3 Failure remains informative

Low full-list coverage suggests merchant assortment/integration problems. Good conversion but poor repeat can indicate fulfilment or value problems. Positive item savings but negative delivered savings implicates delivery structure. High repeat with negative contribution calls for commercial redesign, not more acquisition spend.

Do not interpret every failure as a need for a better model. The measurements should identify whether the limiting factor is product understanding, supply, execution, customer value or economics.

## 20. Required PRD edits and release checklist

### 20.1 Consolidate instead of appending a fifth review

Create one active baseline with this precedence:

1. Current founder-approved pilot decisions and acceptance criteria.
2. Approved legal/provider/merchant/courier contracts and capability profiles.
3. Architecture and operational procedures implementing those decisions.
4. Historical vision and reviews, clearly marked non-normative.

When a contract makes the active product promise impossible, reopen the decision visibly. Do not silently downgrade the customer experience in code.

### 20.2 Specific edits

| Source section | Edit required |
|---|---|
| Original PoC opening | Mark historical/synthetic; remove ambiguity about funding a live wallet now |
| Suggested stack / Frontend | Mobile web is pilot scope; native app is not a parallel launch requirement |
| Future purchases | Mark real-money reservation and autonomous scheduling as gated; planning is not custody |
| Scope guardrail | Replace automatic WhatsApp-compliance assertion with dated channel eligibility gate |
| Fourth review - commitment sequence | Replace universal authorise-then-capture rule with payment-rail-specific branches |
| Fourth review - one payment | Separate approval, charge count, capture capability and settlement allocation |
| Partial fulfilment | Define mandatory-item precedence, allowed transformations and fresh-approval triggers |
| Merchant model decision | Remove categorical no-liability and automatic accounting/tax conclusions |
| Payouts | Distinguish desired post-delivery release from actual provider release control |
| Customer guarantee | Distinguish submission, acceptance, debit, refund obligation and bank credit |
| Economics | Correct subsidy arithmetic; replace approximate 8% break-even with the reproduced value |
| Metrics / stop conditions | Define denominators and make below-target performance the adverse trigger |
| Development plan | Put commercial/provider feasibility and a two-store recovery test before scaling the agent |
| Regulatory and market claims | Add primary source, effective/observation date, verification date, owner and status |
| Change log | Record each adopted decision; do not describe unverified research as independent legal clearance |

### 20.3 Ready-to-paste normative replacements

**Payment:**

> The pilot supports only provider/account/payment-method combinations documented in an approved capability profile. Purchase approval, payment authorisation, capture, settlement allocation and settlement receipt are separate records. One customer payment across two retailers is enabled only after the exact funds flow, refund allocation and settlement evidence have passed provider conformance testing. Unsupported capabilities fail closed.

**Partial fulfilment:**

> A must-have item takes precedence over permission for optional partial fulfilment. Changes are permitted without a new approval only when expressly covered by the original approved conditions and verified deterministically. New merchants, products, higher fees or materially changed delivery arrangements require fresh approval. Separate merchants do not create an atomic delivery guarantee.

**Refunds:**

> Every refund references the original payment and the affected goods/fees. Customer entitlement, provider beneficiary reversal and ultimate merchant liability are tracked separately. Refund initiation, provider confirmation and customer-credit evidence are distinct states. Duplicate reimbursement is prevented across retries, manual compensation and disputes.

**Role and liability:**

> Retailers are intended to contract as sellers of goods, and Trollie is intended to provide disclosed purchasing/coordinating services. Acquiring roles, payment permissions, consumer liability, tax treatment and revenue presentation are determined from the actual transactions and contracts. The agency label is not a liability exemption or a tax conclusion.

### 20.4 Release evidence checklist

Before a money-moving pilot, assemble one versioned release record containing the approved role/funds-flow map; provider permissions and live capabilities; merchant contracts and preparation procedure; courier service terms; customer terms and approval copy; privacy/identity/channel assessments; funded reserve policy; test results; incident/recovery rehearsal; financial reconciliation proof; operational staffing and stop controls.

Do not label missing items green because the PRD mentions them. A statement of intent is not the evidence itself.

## Final recommendation

**Build the commerce spine and prove the two-retailer transaction, including its failure and refund path.** Keep the AI agent as the interaction and planning layer, not the source of authority or financial truth.

The product remains the founder's intended service: Trollie actually buys and arranges delivery, potentially from more than one store. The narrower pilot makes that promise testable; it does not reduce the business to a comparison website.

The source PRD has enough product direction to start that work. This blueprint supplies proposed implementation detail, corrects specific financial/transaction ambiguities, and identifies evidence still needed. It does not establish signed commercial support, a legal right to move funds, national product-market fit, or production readiness.

---

## Appendix A. Primary-source evidence register

All entries below were consulted for this review on **28 October 2026**. Web documentation can change. Save the relevant version and obtain account-specific confirmation before implementation. URLs are included as portable source references, not as evidence of an existing integration.

### [S01] Stitch - Split Settlements Integration

`https://docs.stitch.money/payment-products/payins/card/split-settlements/integration`

Supports the documented destination limit, provisioned merchant identifiers, allocation fields and the distinction between allocation and actual payout. Does not approve Trollie's commercial topology.

### [S02] Stitch - Split Settlement Refunds

`https://docs.stitch.money/payment-products/payins/card/split-settlements/refunds`

Supports proportional beneficiary refund allocation, refund fee treatment and partial-refund accounting behaviour. Account-specific commercial terms still require confirmation.

### [S03] Peach Payments - Manage card payments

`https://developer.peachpayments.com/docs/card-manage-payments`

Supports the distinction between preauthorisation, capture and reversal, including documented partial-capture behaviour. It is not a confirmation of a multi-retailer marketplace programme.

### [S04] Ozow Hub - Transaction and settlement statuses

`https://hub.ozow.com/integration-methods/statuses/`

Supports distinct payin, payout, refund and settlement lifecycles and the need for authoritative payment evidence rather than a browser redirect.

### [S05] Ozow Hub - Refund a payment

`https://hub.ozow.com/integration-methods/apis/payment-operations/refund-a-payment/`

Supports the documented refund operation, access scope, funding requirements and partial-refund capability. Does not guarantee the timing of every customer credit.

### [S06] PostgreSQL - Transaction Isolation

`https://www.postgresql.org/docs/current/transaction-iso.html`

Supports the isolation/concurrency distinctions used to motivate explicit locking or serializable transaction design. Pin the chosen database release during implementation.

### [S07] AWS Prescriptive Guidance - Transactional outbox pattern

`https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html`

Supports the outbox approach to database/message consistency and the need to handle duplicate events. Does not make external purchases atomic.

### [S08] W3C - Web Authentication Level 3

`https://www.w3.org/TR/webauthn-3/`

Supports credential-based authentication, user verification and biometric privacy distinctions. The quote-binding design in this document is an application recommendation, not a claim that WebAuthn displays a shopping basket automatically.

### [S09] Consumer Protection Act 68 of 2008 - WIPO Lex legislative text

`https://www.wipo.int/wipolex/en/legislation/details/6619`

Sections 54 and 61 are relevant to service quality and potential supplier liability. This text does not determine Trollie's particular liability; current legal advice and applicable amendments remain necessary.

### [S10] IFRS Foundation - IFRIC Update April 2022, principal versus agent

`https://www.ifrs.org/news-and-events/updates/ifric/2022/ifric-update-april-2022/`

Supports assessment of specified goods/services and control rather than reliance on labels. The discussed fact pattern concerns a software reseller; this document uses the general analytical point, not its outcome as a ruling for groceries. Trollie's applicable reporting framework remains to be determined.

### [S11] SARS - Value-Added Tax

`https://www.sars.gov.za/types-of-tax/value-added-tax/`

Supports the current standard rate of 15%, the existence of zero-rated/exempt supplies and the VAT-vendor distinction. The calculations use explicit platform-registration and fee-treatment assumptions rather than certifying an agency model.

### [S12] FSCA - Regulated People and Entities, AML/CFT discussion

`https://www.fsca.co.za/Regulated-People-And-Entities/`

Supports accountable-institution obligations and risk-based CDD as a general framework. Does not classify Trollie or prescribe universal selfie verification for this checkout.

### [S13] Stitch - Idempotency

`https://docs.stitch.money/idempotency`

Supports exact-request replay requirements, the documented retention horizon and caution about retries after expiry. Internal operation retention and recovery procedures are Trollie design recommendations.

### [S14] WhatsApp - Business Messaging Policy

`https://whatsappbusiness.com/policy/`

Supports opt-in, messaging-window/template, automation-escalation and sensitive-information requirements. The complete linked platform terms were not retrievable in this review; AI/marketplace eligibility and account pricing remain open gates.

### [S15] SARS - Budget 2026 Frequently Asked Questions

`https://www.sars.gov.za/about/sars-tax-and-customs-system/budget/budget-2026-frequently-asked-questions/`

A limited additional check found SARS describing administration of increased VAT thresholds from 1 April 2026 while distinguishing the legislative process. This does not verify the PRD's particular bill identifier or establish an enactment date. Thresholds are not used to infer Trollie's registration status or to replace tax advice.

### [S16] Stitch - Split Settlements overview

`https://docs.stitch.money/payment-products/payins/card/split-settlements`

Supports the primary/destination merchant model, enablement requirement and current one-destination limitation. Its worked fee example is not used as a quoted Trollie rate.

## Appendix B. Source provenance and verification limits

### B.1 Source file

Original uploaded filename: `Agentic Shopping Wallet - PoC Architecture(3).md` (the actual filename uses an en dash in place of the hyphen displayed here).

Source SHA-256:

```text
3b34e6d1e177cca5ec5c3873073a113e71bb9433fe54dcf5eb1aea7c6659e199
```

The source file is not overwritten. References to [PRD] use its named sections, particularly the Third review, Fourth review, Security architecture, Minimum order and delivery economics, Legal and partner launch gates, and Pilot metrics and stop conditions.

### B.2 What was checked

The supplied latest PRD was reviewed for internal consistency and executable transaction semantics. Selected public primary documentation was checked for material payment-provider, accounting, consumer-law, VAT, authentication, database and messaging assumptions. The arithmetic in Section 16 was recalculated independently from the source inputs. Document checks cover section presence, source identifiers, JSON syntax, amount summation and numeric examples.

### B.3 What was not established

No merchant, bank, courier, regulator or payment-provider representative was contacted. No contracts, credentials, implementation repository, running system, customer cohort or commercial quote was supplied or tested. The acceptance catalogue is a specification, not a test report. The logical schema is not a production migration. No live money moved.

This review does not independently validate every Stats SA, Treasury, SARB, FIC, competitor, market-size, AI-protocol, cloud-service, card-issuer or pricing assertion accumulated in the PRD. Those claims require a separate dated evidence register before use as verified external research or an investor factual claim.

### B.4 Sharing status

This document can be circulated as a **proposed engineering review and implementation blueprint**, with its assumptions, open decisions and limits intact. It should not be circulated as regulatory approval, an audited financial model, proof of provider support, completed software or a fully verified market-research report.

