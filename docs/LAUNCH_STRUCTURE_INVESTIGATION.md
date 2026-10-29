# Launch structure investigation: selling without a payments licence

Status: **proposal for the founders' decision, not adopted.** It would change the PRD's
phasing and parts of DECISIONS.md (the wallet, the multi-retailer funds flow). Research on
29 October 2026; not legal advice. Every "probably" below needs confirmation from a South
African payments lawyer before money moves.

Founders' direction, 29 October 2026: **the original plan stays** (retailers join the
platform and sell through it; the wallet follows later). Own dark stores are not being
pursued. To launch quickly, Trollie would first run a **concierge reseller phase**
(structure B, described under "Phase 0" below) and move each retailer to a direct
integration as agreements are signed.

## The question

Can Trollie launch agent-led buying (chat, voice, a photo or a description, then a shopping
list the customer confirms) without registering with a payments regulator, and grow from
there? And can Trollie run its own dark stores and partner couriers as part of that?

## The finding in one paragraph

Payments regulation turns on **whose money Trollie touches, and in what capacity**. Taking
payment for goods Trollie itself sells is ordinary trade: a licensed payment provider
handles the card or EFT and pays Trollie. Collecting money in order to pay someone else
(a retailer, a courier) is "payment to a third person", which needs registration (TPPP,
moving to direct SARB authorisation in 2026). Holding customers' money as a spendable balance
is e-money, which the SARB only allows banks to issue. So the low-regulation path is:
**Trollie sells as the merchant of record, from its own stock or as a reseller, takes
payment per order through a licensed provider, and does not run a wallet.**

## Four ways to structure it

| | Who the customer buys from | Who touches the money | Payments registration | Main burden instead |
|---|---|---|---|---|
| **A. Own dark store** | Trollie | Trollie, for its own sales, via a licensed provider | Probably none | Stock, premises, food rules, Trollie is the supplier under the CPA |
| **B. Trollie as reseller** | Trollie, which buys the goods from partner retailers first | Trollie, for its own sales; it pays retailers as a customer or under a supply agreement | Probably none (Trollie pays its own suppliers, not on the customer's behalf) | Trollie is the supplier: returns, defects, VAT on the full sale, price risk between quote and purchase |
| **C. Marketplace, provider pays sellers** | Each retailer | The licensed provider, which splits the payment to each seller | Trollie probably none; the provider carries it | Depends on a provider product that can pay several sellers (blueprint D02, still open) |
| **D. Trollie collects and pays retailers** (today's PRD wallet / multi-retailer flow) | Each retailer | Trollie, on the customer's behalf | **TPPP / SARB authorisation**; a wallet also needs a bank | Registration through a sponsoring bank, client-money segregation, reconciliation obligations |

The test that separates B from D: in B, Trollie sells to the customer at its own price and
separately buys from its supplier; in D, Trollie passes the customer's payment through to a
retailer the customer bought from. A "buying agent" that pays retailers *for* the customer
is structure D, whatever the app looks like. That line is where counsel's opinion matters
most.

## Recommended path

1. **Launch: A plus B, pay per order, no wallet.** Trollie's own dark store(s) for a narrow,
   fast-moving range, and reselling partner retailers' goods for everything else. Every
   order is paid through a licensed provider into Trollie's own account. Partner couriers
   deliver.
2. **When provider products allow: add C** for retailers who prefer to sell directly, with
   the provider paying them. Trollie earns a commission and never holds their money.
3. **Only later, with a bank partner: the wallet and agent envelopes** (structure D
   territory). The engineering already exists and stays dormant behind a switch.

Refunds go back to the original payment method. Closed-loop Trollie credit is possible, but
a prepaid voucher stays valid for three years under CPA section 63; whether a closed-loop
balance falls under the SARB's e-money position was not confirmed and needs counsel.

## Rules that apply whatever the structure

- **Consumer Protection Act.** As the supplier in A and B, Trollie is responsible for
  defective goods and for goods lost before delivery (goods stay at the supplier's risk
  until the customer accepts them). Terms cannot contract out of that. Recover from
  couriers by contract and evidence (see the lost-parcel table in the earlier note).
- **Electronic Communications and Transactions Act.** Section 20 makes agreements formed
  through an electronic agent valid, but the customer must be able to correct mistakes
  before the order is placed; otherwise they may cancel. Section 43 sets the information an
  online seller must show and requires a review-and-correct step before the order. The
  agent's "here is your list, confirm it" step, followed by passkey approval of the exact
  basket, is exactly that and must stay. Section 44 gives a seven-day cooling-off right for
  online goods; section 42 excludes some transactions (reportedly including everyday
  foodstuffs delivered to the home; confirm the exact wording).
- **POPIA.** Photos, voice notes and chat transcripts are personal information: collect them
  for a stated purpose, keep them only as long as needed, and keep faces and voices out of
  any identification use unless separately justified.
- **Dark store premises.** A Certificate of Acceptability for food premises (R638), a
  municipal business licence (Businesses Act) where perishable food is sold, zoning
  approval, fire compliance; a liquor licence only if alcohol is sold (leave it out).
- **FICA.** Selling groceries is not, on its own, an accountable-institution activity;
  becoming a payment institution (structure D) may bring obligations. Confirm with counsel.

## What changes in the product

- **The agent experience.** Chat, voice, a photo or a description becomes a structured list
  of catalogue items; the customer confirms the list, then approves the exact basket with a
  passkey. The model proposes; it never prices, pays or picks a payee (unchanged rule).
  Anything the agent cannot find in Trollie's own range or partners' ranges is shown as
  "not available", never bought elsewhere (see the earlier scam-site note).
- **Optimiser.** "Store" now means Trollie's own dark store and Trollie-resold partner
  ranges. The two-store limit still applies, now per delivery.
- **Money flows.** One payment per order to Trollie. Partner retailers are paid by Trollie
  as its suppliers, under supply terms, on Trollie's schedule. Reconciliation becomes
  "sales vs purchases vs deliveries" instead of a multi-party split.
- **Wallet code.** Kept, disabled, behind a feature switch until a bank partnership exists.
- **Simulation.** A dark-store merchant with Trollie as seller of record, and reseller
  purchasing with price movement between quote and purchase, can be added to the crowd
  market to test margin risk and stock-outs.

## Phase 0: concierge reseller (founders' direction, 29 October 2026)

Trollie buys groceries from existing retailers and sells them to the customer at Trollie's own
price, until retailers sign up. OneCart ran this model in South Africa: its personal shoppers
picked orders off partner retailers' shelves, paid at the till, and its drivers delivered,
for a 5–7% service fee.

**Decided by the founders**

| Topic | Decision |
|---|---|
| Payment | The customer pays Trollie in full first, into Trollie's own account. Trollie buys nothing until the payment is confirmed. |
| Problems | Trollie refunds the customer first, then takes the problem up with the retailer or courier. |
| After delivery | The sale is final: no change-of-mind returns or changes. |
| Price changes | Trollie absorbs them. The customer pays the quoted price. Prices must be updated quickly. |
| Substitutions | The customer sets substitution preferences when ordering. |
| VAT | Handled as normal business. |
| Retailer agreements | The founders are pursuing them. Full automation is the long-term aim. |

**Consequences for the design**

- **Wording makes Trollie the seller.** Quotes, terms and receipts say "Trollie's price for
  this basket, delivered". They never say "the retailer's price plus a fee", and never call
  Trollie "your agent paying the retailer". That keeps Phase 0 in structure B and out of
  third-party payments. It also means Trollie keeps any saving when the till price is lower,
  which an agent would have to pass back. Counsel to confirm (question 1 below).
- **The quoted price binds Trollie anyway.** CPA s23(6) bars a supplier from charging more
  than the displayed price, apart from obvious errors that are corrected and disclosed. So
  "price changes are on us" is also the legal position.
- **"Final once delivered" covers change of mind only.**
  - ECTA s42(2)(c) excludes everyday foodstuffs and beverages delivered to the home from the
    s44 cooling-off right, so change-of-mind returns can be refused for groceries.
  - Wrong, missing, damaged or expired items cannot be refused. Goods are at the supplier's
    risk until delivery (CPA s19). Defective goods may be returned within six months for
    repair, replacement or refund (CPA s56(2)).
  - Non-grocery lines (furniture, electronics) do get the seven-day cooling-off.
  - Terms should say: "no returns for change of mind; wrong, damaged or missing items are
    refunded".
- **Settlement method.**
  - Instant EFT or PayShap into Trollie's account cannot be charged back.
  - Card payments can still be disputed with the customer's bank whatever the terms say, so
    keep delivery evidence (proof of delivery, photo, OTP).
- **Substitution default.** Each item carries a preference:
  1. exact item only;
  2. similar item, same size, at no more than the quoted line price;
  3. shopper's choice.

  If the customer sets nothing, the default is option 2 (to be confirmed by the founders). A
  substitute never raises what the customer pays; a dearer one is Trollie's cost. A missing
  item with no acceptable substitute is refunded automatically.
- **Prices without scraping.**
  - Every completed purchase's receipt is a fresh, exact price observation for that store;
    that becomes the main price feed.
  - Staff check the weekly specials.
  - Lines not seen recently are quoted with a wider buffer or checked before the quote.
  - The gap between quoted and paid prices is booked as purchase-price variance, so
    pricing error shows up per retailer per week.
- **Placing the retailer order.** Phase 0 uses people: in-store pickers, or staff placing an
  agent-prepared order through a business account.
  - Automated ordering through retailers' consumer apps is not planned. The retailers'
    terms seen so far restrict automated access and limit some accounts to personal use, so
    accounts can be closed with paid orders in flight.
  - Each retailer moves to an automated channel only through an agreement (an API or an
    order feed).
- **System fit.** A retailer in Phase 0 becomes a "concierge" merchant adapter, where
  pricing, placement and receipt capture are tasks for a person, and the retailer's order
  number and tax invoice are stored as evidence. Quotes, approval, the pay-first rail,
  refunds, the ledger and reconciliation are unchanged. When an agreement is signed, the
  adapter is replaced and nothing else moves. The ledger gains accounts for stock purchased
  for resale and purchase-price variance; the wallet stays off.

**Buying channels built for resellers** (research 29 October 2026; current terms still to be
confirmed with each company)

| Channel | Who it serves | What is known | Fit |
|---|---|---|---|
| Shoprite Cash & Carry online (shopritecashandcarry.co.za) | Spaza shops and small retailers buying stock to resell | Launched July 2024. Online ordering with saved orders; free delivery within 50 km; card, EFT and store credit | Staples in case packs, delivered to a Trollie address |
| Red Star Wholesale (formerly Checkers Food Services) | Catering and hospitality businesses in Gauteng, the Western Cape and KwaZulu-Natal | Free delivery over R1 000, six days a week. A Business Buying Card gives 2.5% off at Checkers and Checkers Hyper, with 30 days' interest-free credit | A trade account plus a discount for in-store picking at Checkers |
| Makro Business (Massmart, owned by Walmart) | Businesses of all sizes | Online business site launched September 2023; a trade account; delivery, collection and lockers | Bulk and general merchandise |
| Pick n Pay | — | No current business-account channel found. Pick n Pay sells through Takealot's Mr D under a commercial agreement | Partnership route only |
| Checkers Sixty60 | Consumers | No business or corporate account found | Not a channel |

Unlike consumer delivery apps, these wholesale channels exist so that businesses can buy stock
to resell. That is Trollie's position in Phase 0.

**No premises (founders' direction).** Trollie holds no stock and runs no hub or dark store.
Each customer's basket is placed as its own order on Trollie's business account. The
retailer picks and packs it, and the goods move straight to the customer in one of three
ways, in order of preference:

1. **Retailer delivers to the customer's address.** This needs the retailer to agree to
   ship to an address other than the account address.
2. **Courier collects from the branch.** The order is placed for click-and-collect on
   Trollie's account, and a courier booked by Trollie collects the packed order and
   delivers it. This maps onto the existing leg states: merchant ready, courier collected,
   delivered.
3. **Shopper buys in store.** Used for fresh produce and single items that the business
   channels do not sell individually.

Business-channel minimums (for example, Red Star's free delivery from R1 000) suit larger
and stokvel baskets. Small baskets go through route 2 or 3.

**Still open**

- The default substitution rule.
- Minimum basket or minimum fee. Small baskets lose money once picker time, delivery and
  payment fees are counted.
- The service premium.
- Which retailers and which area to start in.
- Whether OneCart had formal agreements with every store it shopped at. It lists them as
  partner stores; the terms were not public.

## Questions for counsel

1. Does structure B (Trollie sells at its own price, buys separately from partner retailers)
   fall outside "payment to third persons" under SARB Directive 1 of 2007 and the new SARB
   authorisation framework? What contract wording keeps it there?
2. Is a closed-loop Trollie credit balance (refunds, promotions) e-money, or a CPA section 63
   prepaid credit?
3. Does ECTA section 42 exclude everyday groceries delivered to the home from the
   section 44 cooling-off right, and which of Trollie's ranges (furniture, electronics) it
   does apply to?
4. Who is the "supplier" to the customer in structure C, and what does that mean for
   Trollie's liability as the platform?
5. Courier contract: liability cap, insurance, evidence required (collection scan, proof of
   delivery) and the claims process.

## Sources

- [PASA: key role-players and TPPPs](https://pasa.org.za/national-payment-system/key-role-players/)
- [PASA: TPPP registration](https://authorisation.pasa.org.za/so-and-tppp/tppp-registration/)
- [SARB Directive 1 of 2007, payments to third persons](https://authorisation.pasa.org.za/wp-content/uploads/2024/07/SARB-Directive-1-of-2007-Third-Party-Payments-Providers.pdf)
- [ENS: Draft Directive on payment activities](https://www.ensafrica.com/news/detail/10384/new-rules-for-payment-providers-what-you-need)
- [Legal500: TPPPs at a regulatory crossroads](https://www.legal500.com/intelligence/south-africa/finance-and-banking/third-party-payment-providers-at-a-regulatory-crossroads)
- [SARB: PSMB transition](https://www.resbank.co.za/en/home/what-we-do/payments-and-settlements/psmb)
- [SARB Position Paper on electronic money (NPS 01/2009)](https://www.resbank.co.za/content/dam/sarb/what-we-do/payments-and-settlements/regulation-oversight/PP2009_01.pdf)
- [ECTA (SAFLII consolidated text)](https://www.saflii.org/za/legis/consol_act/ecata2002427/)
- [Michalsons: ECT Act v CPA](https://www.michalsons.com/blog/consumer-protection-in-electronic-transactions-ect-v-cpa/2631)
- [RateWeb: online cooling-off rights](https://www.rateweb.co.za/online-shopping-rights-south-africa)
- [Acts Online: CPA section 63](https://www.acts.co.za/consumer-protection/63_prepaid_certificates_credits_and_vouchers)
- [PMG: NCC reply on prepaid voucher validity](https://pmg.org.za/committee-question/35381/)
- [ASC Food Safety: Certificate of Acceptability](https://ascfoodsafety.com/certificate-of-acceptability/)
- [ASC Food Safety: South African food laws](https://ascfoodsafety.com/ultimate-guide-south-african-food-legislation-2026/)
- [Acts Online: CPA section 23, displayed price](https://www.acts.co.za/consumer-protection/23_disclosure_of_price_of_goods_or_services)
- [Acts Online: CPA section 56, implied warranty of quality](https://www.acts.co.za/consumer-protection/56_implied_warranty_of_quality)
- [Michalsons: ECT Act consumer protection, s42(2) exclusions](https://www.michalsons.com/blog/consumer-protection-provisions-of-the-ect-act/2380)
- [Elluminati: how OneCart works](https://www.elluminatiinc.com/?p=75329)
- [Checkers Xtra Savings Plus terms (personal use)](https://www.checkers.co.za/terms-and-conditions/legal-terms-and-conditions-xtrasavingsplus)
- [TechCentral: Pick n Pay partners with Takealot](https://techcentral.co.za/pick-n-pay-partners-with-takealot-in-online-shopping-push/211192/)
- [Supermarket & Retailer: Shoprite Cash & Carry online and bulk delivery](https://supermarket.co.za/index.php/innovation-and-technology/6603-shoprite-launches-online-shopping-and-bulk-delivery-service-for-spaza-shops-and-small-businesses)
- [Shoprite Holdings: Red Star Wholesale](https://www.shopriteholdings.co.za/newsroom/2023/red-star-wholesale-and-catering-services.html)
- [Shoprite Holdings: business buying cards](https://www.shopriteholdings.co.za/contactus/our-cards.html)
- [Bizcommunity: Massmart launches Makro Business](https://www.bizcommunity.com/DailyNewsletter/196/160/20230929.html)
