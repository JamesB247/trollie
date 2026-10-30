# Starting with local merchants: dark stores, independents and couriers

*Research and recommendation · 30 October 2026 · not yet a founder decision*

**The question:** the big grocers may not cooperate with a company that could compete with them. Can Trollie start with dark-store operators and local shops near the customer instead, while still submitting the ShopriteX proposal?

**Short answer:** yes, but not mainly through dark stores. South Africa has very few dark stores outside the big retailers. The real opportunity is the **independent grocery sector**, which is about a third of all South African grocery spend (FMCG), plus fresh specialists such as butchers and greengrocers. Couriers can be booked per order. Run it in parallel with the Shoprite proposal, and fix the proposal's exclusivity wording first (section 7).

Sources are numbered as in the two research briefs from 30 October; items marked [UNVERIFIED] need checking before we rely on them.

---

## 1. Dark stores: there are few, and most belong to the big retailers

In South Africa, quick delivery is mostly picked from ordinary supermarket shelves. Shoprite runs about **6 dark stores against 894 stores that fulfil Sixty60 orders**, and uses them only where stores are at capacity.

| Operator | Owner | Gauteng presence | Dark stores | Sells through others? | Partner for Trollie? |
|---|---|---|---|---|---|
| Checkers Sixty60 | Shoprite | Kempton Park (plus Western Cape) | ~6 | No | Only via the ShopriteX proposal |
| Woolies Dash | Woolworths | None found | 2 (Cape Town) | Woolies After Dark on Uber Eats | Unlikely |
| Pick n Pay asap! (incl. Bottles) | Pick n Pay | Johannesburg (clothing) | 1 | Groceries also on Mr D | Unlikely |
| OneCart | Massmart (Walmart) | National, from Makro/Game | None | Lists several retailers | No, a competitor owned by a retailer |
| TakealotNOW / Mr D | Takealot (Naspers) | Johannesburg, Pretoria | 4 | Is a marketplace itself | No, a competitor |
| **Zulzi** | Founder Donald Valoyi; **Shoprite owns 26%** and Zulzi builds Sixty60's tech | Johannesburg North, Pretoria, Centurion | 7, ~5,000 orders/day, 300 drivers [snippet] | Aggregates other stores | Possible, but a conflict risk; check its health |
| **Yassir Express** | Yassir (Algeria) | Johannesburg North, Centurion (Midrand, Edenvale in job ads) | "Several" | **Yes, sells on Uber Eats** | Possible; [UNVERIFIED] still active |
| Uber Eats Market | Uber, with Smart Kitchen Co | Johannesburg | 9 (2022) | Uber Eats only | Unlikely; [UNVERIFIED] since 2022 |
| APPTO | Independent | Sandton (liquor) | 1 | — | Later; liquor licensing |
| Yebo Fresh | Independent | Cape Town townships | Warehouse | Moved to supplying spazas (B2B) | Not Gauteng |
| Vuleka | Independent | Alexandra and Gauteng townships | Pooled buying | Spaza ordering by WhatsApp | Possible supply route; [UNVERIFIED] status |
| Bolt Market, Glovo | — | Not in South Africa | — | — | — |

**What failed and why:**
- Bolt Food left in December 2023.
- Uber Eats Market stalled at 9 sites.
- OrderIn shut its consumer app and became a delivery service for businesses.
- WumDrop, OneCart and Bottles were all bought by retailers.

**Lesson:** owning stock in dark stores is expensive in South Africa. Platforms that survive use stock that retailers already hold. That supports Trollie's model: **no stock, no premises, the merchant packs, a courier delivers.**

---

## 2. Where the supply really is: independent retailers

| Segment | Size | Source |
|---|---|---|
| Formal independents (independent supermarkets, hybrids, cash & carries, wholesalers outside the listed chains) | **R268bn, nearly a third of FMCG** (2025) | Trade Intelligence [2] |
| Informal (spaza-type) retail | R197bn, ~150,000 stores (2023) | Trade Intelligence [1] |
| Where informal traders buy stock | 95% from independent wholesalers | [1][2] |

**Who can say yes to joining Trollie:**

| Group | Who decides | Fit for a first pilot |
|---|---|---|
| **Independent supermarkets and hybrids** (e.g. members of buying groups UMS/IGA, BEC, Elite Star, Independent Cash & Carry Group) | The owner | **Best.** Usually registered, barcode POS, full range |
| **Kit Kat Cash & Carry** (Gauteng; 6 cash & carries, 19 express stores, 3 hybrids) | The owner | **Strong.** Serves households and traders |
| **Devland Cash & Carry** (20+ stores; Soweto area) | The owner | **Strong** |
| **Ten ex-Cambridge/Rhino stores** that the Competition Tribunal made Shoprite divest to independent owners (2022) | The new owners | Good, if we can identify them [buyers UNVERIFIED] |
| **Trade Link** voluntary group: **1,300+ independents** on central POS and back office | The owners; the group holds the data | **Very good:** one integration could reach many stores |
| SPAR / SUPERSPAR / KWIKSPAR (~80% owner-run) | Owner runs the store, but the Guild agreement nominates POS and supply; SPAR already has SPAR2U and an Uber Eats deal | Only with written Guild or group consent; approach at group level |
| Pick n Pay franchise, OK Franchise (Shoprite), Food Lover's Market | The franchisor | Assume no |
| Boxer, Usave | Owned by the chains | No |
| Spaza shops | The owner | **Defer** (food safety and data; section 4) |

**Fresh specialists for the second store in an order:**
- independent **butcheries** (PMBEJD tracks 36 butcheries because low-income households buy meat there);
- halaal butchers (show the certifier: SANHA, MJC, NIHT or ICSA);
- **greengrocers** (informal traders are about 30% cheaper on key vegetables, per Mail & Guardian, 2024);
- bakeries.

This fits the engine's two-store limit well: **an independent supermarket for packaged goods, plus one fresh specialist.**

---

## 3. Delivery: couriers booked per order

| Courier | How it's booked | Fit |
|---|---|---|
| **Uber Direct** | Dashboard, POS or API (API tier usually for higher volumes) | **First choice:** real-time, national zones, per-delivery fee, no commission; get a rand quote |
| **Picup** (Karooooo) | Platform / API | **Second courier** for backup; serves PnP and Dis-Chem |
| Droppa | Platform; resells Uber Direct, adds bakkies | Bulk and stokvel baskets later |
| Bob Go | One API across The Courier Guy, SkyNet, others | Scheduled or next-day, not same-hour |
| Pargo | Pickup points | Click-and-collect option, from about R49 per parcel [UNVERIFIED] |

Benchmarks for what customers pay: Woolworths delivery R70–R130; retailer apps about R35. Courier prices for one drop are not published. **Get quotes from Uber Direct and Picup before setting a delivery price.** One drop per order is the main cost: baskets need to be big enough, which suits the planned monthly shop.

---

## 4. Risks, and how we handle them

| Risk | What we found | What we do |
|---|---|---|
| **Food safety and liability** | After the Soweto deaths in 2024, only about 15,000 of 44,696 verified spazas hold licences (May 2026). The Consumer Protection Act (s61) makes retailers and distributors jointly liable for unsafe goods | Every merchant must have municipal registration and a current **Certificate of Acceptability**, a halaal certificate where one is claimed, and a food-handling record, re-checked on expiry. Indemnity and insurance in the contract. Get counsel's view on Trollie's s61 position. **No spazas in the first pilot.** |
| **Product data** | Packaged goods carry barcodes (GS1 GTIN-13); butchery and bakery items use scale or PLU codes; POS systems vary | Start with merchants whose POS can export products and prices. Match packaged goods by barcode, map fresh items by hand, and have customers confirm. The merchant's acceptance of each order is final (already how the engine works). |
| **Price** | Spazas are dearer on packaged staples; fresh specialists are often cheaper; there is no comparison study for formal independents | Benchmark baskets weekly against a chain. Never say "cheapest". This is exactly what "one honest total" is for. |
| **Payments** | Collecting money and paying several merchants can make Trollie a *third-party payment provider* that must register with PASA (SARB Directive 1 of 2007) | Use a registered provider's split or marketplace product: **Stitch** (one recipient per transaction, so two linked payments for a two-store order), **Paystack** split codes [UNVERIFIED in official SA docs], **PayFast** split payments, or **TradeSafe** escrow. Trollie never holds merchant money. Get counsel's and PASA's view before any real money. |
| **Merchant fees** | Uber Eats takes 30% (14% if the merchant delivers); Mr D about 22% [UNVERIFIED] | **This is our pitch to merchants:** new orders for a much lower commission, with the delivery charged to the customer at cost. |
| **Merchant fraud** | Many new merchants; the simulation's scam store | Probation for new merchants, a cap on money held for them, and refunds when an order isn't delivered: already built (I-044). Add checks of company registration (CIPC), owner ID and bank account before any payout. |

---

## 5. What we offer each side

- **Households:** "Your list. Taken care of." The shops near you, one honest total, nothing bought until you say yes.
- **Local merchants:** "Planned monthly orders from households near you, already approved and paid. You pack; we bring the customer, the courier and the support, for a fraction of a delivery app's commission." Merchants use the merchant screen (accept, reject, ready), which is already built in simulation.

---

## 6. Recommended "local first" pilot (to decide)

| | |
|---|---|
| **Where** | One Gauteng area with an independent supermarket or hybrid and a fresh specialist within a few kilometres. Candidates: around a Kit Kat or Devland store (Soweto, Mamelodi), or a suburb with an independent supermarket that belongs to a buying group |
| **Merchants** | 3 to 5: one or two independent supermarkets or hybrids, one butchery, one greengrocer. Optionally Yassir Express or Zulzi, if active and willing |
| **Households** | 30 to 50 invited households, the monthly pantry shop, with fresh items from the specialist |
| **Delivery** | Uber Direct first, Picup as backup |
| **Payment** | A registered provider's split or escrow product; Trollie never holds the funds |
| **Measures** | Same as the ShopriteX pilot: orders complete as approved, no spend without approval, honest total against the household's usual route, effort, repeat use at the normal fee, and merchant acceptance time |

**What it needs that isn't built yet.** These are outside the current synthetic sprint (CLAUDE.md), so each one needs a founder decision:

1. Merchant onboarding:
   - a document checklist (registration, Certificate of Acceptability, halaal certificate, bank account);
   - catalogue import from a POS export (CSV).
2. A real courier connection (Uber Direct).
3. A real payment provider using split or escrow payments.
4. Legal review of the payment structure and of Trollie's s61 position.

---

## 7. Conflict with the ShopriteX proposal: fix this before sending

The proposal (v4.0) says the pilot "uses Group channels only". It also says that **"as our first retail partner, we would understand if the Group wanted a period of exclusivity while the application is built out"**. If we sign up independent merchants now, we can't honestly offer that exclusivity.

Suggested change: *"Trollie works with participating retailers on a non-exclusive basis, including independent local merchants. The Group would be Trollie's first national retail partner; within the pilot area, the pilot uses Group channels only, and we are open to discussing exclusivity among national chains for an agreed period."*

Also be aware that Zulzi is partly owned by Shoprite and builds Sixty60's technology. Approaching Zulzi while pitching ShopriteX should be done openly, or not at all.

---

## 8. Shortlist to contact first

1. **Kit Kat Cash & Carry**: Gauteng independent; serves households; owner decides.
2. **Devland Cash & Carry**: Gauteng independent; 20+ stores; co-founded Elite Star buying group.
3. **Trade Link / its voluntary group**: 1,300+ independents on central POS; one data integration.
4. **UMS (IGA partner), BEC and Elite Star buying groups**: introductions to member supermarkets.
5. **The ten divested ex-Cambridge/Rhino stores**: independent owners by Tribunal order.
6. **Two or three independent butcheries and greengrocers** in the chosen area (by visiting them in person).
7. **Yassir Express**: dark stores, already supplies Uber Eats; confirm it is still operating.
8. **SPAR, at group or Guild level**: only with written consent; already on Uber Eats.
9. **Uber Direct and Picup**: courier quotes and accounts.
10. **Stitch, PayFast, Paystack, TradeSafe**: split-payment and escrow terms.

Deliberately left off: Mr D and TakealotNOW (competitor), and OneCart and WumDrop (owned by Massmart). Zulzi is listed only with the conflict above.

---

## Sources (main)

**Dark stores and quick commerce**
- Checkers dark stores: TechCentral, November 2024; MyBroadband, May 2026.
- Woolworths: IOL, 26 June 2026; EWN, 12 March 2025.
- Pick n Pay: JSE SENS, 9 February 2026.
- Takealot: Engineering News, 17 December 2024; TechCentral, December 2025.
- Zulzi: LaunchBase Africa, 16 October 2025; TechCentral.
- Yassir: ITWeb; htxt, November 2023.
- Uber Eats Market: ITWeb, 16 November 2022.
- SPAR and Uber Eats: ITWeb, 14 October 2025; BusinessDay, 3 February 2026 (Guild agreement in court).

**Couriers and merchant fees**
- Uber Direct ZA courier pages; Picup: Engineering News, 2021; Bob Go; Droppa: ITWeb, April 2024.
- Uber Eats merchant pricing (merchants.ubereats.com/za); Mr D: Stuff, 2023.

**Independent sector**
- Trade Intelligence / Bizcommunity, 20 August 2024 and 23 September 2025.
- Competition Commission Grocery Retail Market Inquiry final report, 25 November 2019.
- Shoprite/Massmart Tribunal conditions: Engineering News, 12 December 2022.
- Kit Kat: Rekord, 2021; Devland: FoodBusinessMEA, 2020; Trade Link: TechCentral, 29 July 2025.
- Mail & Guardian, 20 September 2024 (informal vegetable prices); PMBEJD, July 2026.

**Spaza registration and food safety**
- Presidency, 15 November 2024; DSBD/dtic, 29 May 2026.
- Regulation R638 of 2018; Cliffe Dekker Hofmeyr on CPA s61.

**Payments**
- Stitch split settlements documentation; PayFast Split Payments, 2019; TradeSafe.
- SARB Directive 1 of 2007; PASA TPPP registration.

Full source lists with URLs are in the two research briefs from this session (summarised here).
