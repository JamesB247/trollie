# Customer first: why, how easily, how safely, for whom, and for how long

*31 October 2026 · synthesis of five customer research briefs (three run on Fable 5.1, two on the standard model) · for founder decision*

This document puts the customer ahead of the technology. It answers the founder's questions (*why would a person use us? Is it convenient and easy? Is it sustainable?*) plus four more that decide whether those answers matter:
- **Will they trust it?**
- **Who exactly is it for, and how do we reach them?**
- **What do they use today, and why would they switch?**
- **What would make them leave?**

Claims carry their source. Most "wants AI" figures are attitudes in vendor-commissioned surveys. What people actually *do* (store-switching, payday spending peaks) is more reliable. **No survey has tested Trollie's exact offer**, so section 8 says how to test it.

---

## 1. Why would a person use Trollie?

### The reasons, ranked by strength of evidence

| # | Reason | Evidence | Strength |
|---|---|---|---|
| 1 | **"Find me the cheapest way to get my whole list"** | 52% of South Africans want AI mainly to find the lowest price across retailers (63% of 46–55-year-olds); only 8% want automatic reordering (iqbusiness, Apr 2026). The monthly shop is already spread over **about four stores** (Roots, 25,200 interviews, 2025). 42% switch to cheaper products; 43% buy whatever is on promotion (NIQ 2025) | **Strong** |
| 2 | **"Is this shop, link or seller real?"** | 37% were scammed in the past year, 53% of them via social media (Visa Stay Secure 2026). 41% have been victims and 46% got fake delivery messages; 88% think they can spot a scam but only 34% check links (Kaspersky, Apr 2026). 63% want tools to spot scams (infoQuest 2025). **No South African WhatsApp scam checker exists** | **Strong on need**; unproven that people will use one from an unknown brand |
| 3 | **"One honest total, no surprises"** | Delivery reliability (88%) and unexpected costs are top concerns (World Wide Worx 2026); refund waits frustrate 36% (iqbusiness) | Medium |
| 4 | **"I decide, it does the legwork"** | Only 23% of South Africans would trust an AI agent to complete checkout (Visa 2026); 60% won't allow any spend without prior approval (Visa US); 44% want to review every purchase (Worldpay) | **Strong**, and Trollie's approve-every-basket design matches it |
| 5 | **"Help me get through to month-end"** | Online spending peaks on the **25th**, and the last week of the month carries about 35% of volume (Stitch 2026); 72% say their finances stagnated or worsened (Rogerwilco 2026) | Medium |
| 6 | **"Save me the trip and the impulse buys"** | 40% use delivery apps to cut transport costs or avoid impulse spending in store (iqbusiness) | Medium |

### The reasons people won't use it

1. **"I don't let strangers touch my money."** Only 23% trust agent checkout, and 27% trust *no* organisation to run a shopping agent (Checkout.com 2026). **The agent wallet is a later feature, not the hook.**
2. **Loyalty points.** 85% of South Africans use loyalty programmes, about 10 each (Truth & BrandMapp 2025/26). If Trollie ignores Xtra Savings and Smart Shopper prices, **it won't actually be the cheapest for that person.** This is the biggest product risk we hadn't addressed.
3. **Habit and offline life.** Only 34% of adults buy anything online (World Wide Worx 2026). 40% of township residents have never ordered groceries through an app or website (Township CX 2025). People over 46 are anchored in physical stores.
4. **Two stores means two things that can go wrong:** two deliveries, two minimum orders, two places to fail. Reliability is the top concern.
5. **"Why not just ask Pixie or ChatGPT?"** Single-store assistants and general AI already compare and chat. Trollie's only defensible edge is **across stores, a basket that can actually be fulfilled, and an honest total, delivered visibly every time.**

### The pitch for each person

| Person | What we say |
|---|---|
| **Working mother doing the shopping** | "Send your list on WhatsApp. Trollie finds the cheapest way to get *everything* from shops near you, shows the real total with delivery, and buys nothing until you approve with your fingerprint." *(It must handle her Xtra Savings and Smart Shopper prices, or we lose her.)* |
| **Busy professional** | "One list, at most two stores, one honest total, done in a minute. No hopping between Sixty60, asap! and Dash." |
| **Older or non-technical person** | Don't mention AI. "Forward any shop, link or seller to Trollie on WhatsApp and we'll tell you if it's real, for free." Then: "We find the cheapest shop for your list; you still decide." |
| **AI enthusiast** | "Give your Claude or ChatGPT a Trollie skill: real South African prices, a basket that can actually be fulfilled, scam-checked merchants, and a spending limit your agent can't exceed." |

---

## 2. Convenience and ease of use

### What "easy" means in South Africa

| Reality | Evidence | Design consequence |
|---|---|---|
| Cheap Android phones with full storage | 83M smartphone subscriptions; entry phones at R399; about 84% Android; low-end share rising (ICASA 2026; GSMA) | **No mandatory app install.** Approval page under 1 MB |
| Days with only WhatsApp data | No zero-rating; operators sell WhatsApp-only bundles (from R15 a day); prepaid data is about R79 per GB | **The core loop must work inside WhatsApp.** Links are a fallback, not a requirement |
| Voice notes over typing | Billions of voice notes a day; Pick n Pay's Penny accepts voice notes and photos of lists | Accept text, voice notes and photos of handwritten lists |
| Low literacy, older users | 81% of Grade 4 learners can't read for meaning (PIRLS 2023); research on the "grey digital divide" among older users | Pictures of items, big Yes/No buttons, the total in plain words and the person's own language |
| People resent forced installs | 18% refuse when a browser alternative exists; 54% delete an app once done (Clutch 2026) | Build a native app only after people come back repeatedly |

### The ease-of-use standard

| Standard | Target |
|---|---|
| Customer actions from list to approved basket | **3 or fewer:** send the list, tap "see basket", approve with fingerprint or face |
| Acknowledgement after a list is sent | **3 seconds or less** ("Got it, 14 items, checking 3 shops") |
| First useful answer (basket plus honest total) | **60 seconds or less**; 120 seconds or less for a voice note in isiZulu, Setswana or Afrikaans |
| Size of a quote message | Text first, under 100 KB; images only on request |
| Approval page | Under 1 MB; works on Android 10 with 2 GB RAM; no install, **no one-time PIN** |
| Messages per order | **4 or fewer:** quote, approved, on the way, delivered or problem |
| Substitutions | Asked **once, when the list is made**, per item: Locked / Preferred / Flexible (about 90% of shoppers have something they'd never accept a substitute for) |
| Standing mandate | **Off by default**; small cap; weekly summary; revoke in one tap |
| Low data | Status, delivery time and "cancel" also available by SMS or USSD |

**Why the passkey approval:** it's the one authentication step proven to be faster and more successful than what it replaces. Passkeys succeed **93%** of the time against 78% for passwords and SMS codes, and are 2.8× faster (FIDO Passkey Index, Oct 2026). One-time PINs are also the most exploited fraud path in South Africa. The catch: not every phone supports passkeys, so we need a fallback and a recovery path (Entersekt, Oct 2026).

### The five things that kill convenience

1. **The install wall:** sending a WhatsApp user to the Play Store.
2. **Login loops:** one-time PINs that never arrive, re-login after updates, 3-D Secure challenges inside a retailer's app.
3. **Failing mid-way with no recovery.** WhatsApp Pay in India stayed under 0.4% of UPI volume, partly because transactions failed mid-flow. Users who hit a failure left.
4. **Surprises at the door:** a swap they didn't approve, or a total that changed.
5. **Nagging.** Retail apps send 27–34 notifications a month and get 5–8% opens (Airship 2025). 38% keep an app *because* it's quiet.

**The biggest untested risk is the hand-off.** No independent study measures how many people drop off when a link sends them from Trollie into the retailer's app. Measure it from day one.

---

## 3. Will they trust it?

### What we found

- **South Africans use AI to help them shop, but not to pay.** 77% use AI for shopping; only 23% would trust it at checkout. **76% want real-time alerts.** Banks are seen as the main protectors (76%) (Visa 2026).
- **People confirm on sites they recognise before paying.** 33% feel safer seeing a familiar logo at checkout. That's why Trollie's buying step ends in **the retailer's own app**.
- **Banks have trained people to distrust:** "never install remote-access apps", "never share an OTP", "don't tap links". **WhatsApp messages with links can look like a scam,** and fake delivery messages are the most common scam (49%, infoQuest). Trollie's own messages *will* be imitated.
- **Liking an AI isn't trusting it with money.** People want spending caps (30%), instant revoke (29%) and easy cancellation (28%) (Checkout.com 2026). **60% would stop using an agent after one mistake** (ACI/YouGov).
- **Family delegation is wanted but dangerous.** 78% of abuse of older people in one South African study was financial, usually by family.

### The trust ladder

| Step | What the customer is risking | What must be true |
|---|---|---|
| **0. Scam check** | A forwarded message | Free, no sign-up, no install. Trollie never asks for a PIN, OTP or card, and never replies to a check with a link. Plain verdict, reason, and who to call |
| **1. First basket** | Their list and address | Honest, complete total (delivery, minimums, missing items named); "why this basket"; one sentence on how data is used; **we weren't paid to rank anyone higher** |
| **2. First purchase** | Up to about R2,000 | Exact basket on a Trollie address they recognise; approve with fingerprint or face; **pay in the retailer's own app**; any change means a new approval; a named South African support line with a human |
| **3. Repeat and family** | A habit, and someone else's money | Activity feed and alerts; family roles with caps and expiry; only the owner can widen permissions; the owner is notified of every purchase made for them |
| **4. Agent wallet** | Money held in advance | **Held by a partner bank, never by Trollie**; caps per purchase and per month; only approved merchants; one-tap kill switch; a written refund promise |
| **5. Trollie skill for the customer's own AI** | A third party acting for them | Their AI can only *propose*; every spend is approved or within a limit set with their passkey; each agent can be revoked separately |

### How to talk about safety

- **Use the bank's own language:** *"Trollie will NEVER ask for your PIN, OTP, password or card number, never ask you to install an app or remote-access software, and never phone you to 'reverse' a payment."*
- **Pay where you already pay:** *"You pay inside the shop's own app. Trollie never touches your card."*
- **One way to verify us:** one official WhatsApp number and one website, shown everywhere. *"Forward any 'Trollie' message to us to check it's really us."*
- **A promise in rands:** *"If Trollie buys something you didn't approve, we refund you within 5 working days."*
- **Remove the shame:** *"Scammers fool smart people every day. Checking is the smart move."* One in three victims never report it.
- **Show, don't certify:** short videos of the approval screen and the kill switch. Security certificates (ISO 27001, SOC 2) matter to banks and journalists, not households.

### Five things that would destroy trust instantly

1. A charge they didn't approve, or a total higher than the one they approved.
2. Trollie asking for an OTP, PIN, login, install or remote access, or a phishing campaign pretending to be Trollie succeeding.
3. Hidden costs, silent swaps, or a partial delivery charged as complete.
4. A data breach, selling data, or a family member seeing purchases they shouldn't.
5. A refund nobody answers for.

---

## 4. Who exactly, and how to reach them

### First customers (90 days)

**Time-poor working mothers in Gauteng who do the household shopping, with a household income of roughly R15,000–R50,000 a month.** They already order from Sixty60 or asap! sometimes, and do a monthly big shop plus top-ups.

| Why them | Evidence |
|---|---|
| They do the shopping | Women are 60–71% of main grocery shoppers; 42.6% of households are female-headed (Stats SA GHS 2025) |
| Online, but under-served | In this income group, 84% can get online but only 36% shop online; Gauteng has the most online shoppers (46.9%) (World Wide Worx 2026) |
| The pain is visible and shared | Price gaps of about R114–R139 between chains on the same basket go viral on social media |
| Time-poor | 45.9% of children live with their mother only |
| Exposed to scams | 85% met a scam in the past year (GASA 2026) |
| They'll approve, not delegate | Only 23% trust agent checkout |

**Rough size:** about 0.3–0.6 million reachable primary shoppers. That's plenty for a pilot of 500–2,000 households. *(Estimate, not verified.)*

**Next:**
1. **Grocery-stokvel coordinators** (months 3–6). One trusted buyer for 20–45 households. A fixed quote and committee approval solve real problems for treasurers.
2. **AI-forward young professionals** (once the skill and wallet are ready). They're natural users for the Trollie skill.

**The scam checker is open to everyone,** including adult children checking things for their parents. It's the free front door, not a separate segment.

**Not first:**

| Group | Why not yet |
|---|---|
| Households living on grants, as basket buyers | Delivery fees and minimum orders cancel the savings; they pay cash and shop along their route. They get the free scam checker now |
| People aged 60+, as direct buyers | Most targeted by scams; reach them through their adult children |
| Affluent Woolworths and Sixty60 loyalists | Little price pain; the retailer already owns the relationship |
| Rural households | Patchy delivery coverage and connectivity |
| Big banks as scam-checker buyers | Capitec (Scam Check) and Discovery (TRUST Alert) build their own |

### The cheapest ways to reach them

1. **A WhatsApp loop.** Scam verdicts and "you saved R___" results designed to be forwarded to family and school-parent groups, with a referral link. About R0.12 per message.
2. **Creator videos comparing real baskets** on TikTok and Facebook ("same list: Trollie vs my usual shop"). These comparisons already go viral by themselves.
3. **Community ambassadors:** 30–50 coordinators in grocery stokvels, school and church groups, and workplaces, paid per active household. Trust in people you know is the route that works.

**Platform rule:** since 15 January 2026, WhatsApp bans *general-purpose* AI assistants on its business platform. A task-specific shopping and scam bot should be allowed. **Confirm this with a Meta partner or counsel.**

### Business customers (B2B): who pays

**Design-partner profile:** a **mid-tier or digital-first bank**, or a **personal cyber-insurance agency** like Phishield/Bryte, that:
- has rising losses from social engineering and online-purchase fraud;
- has an app but **no in-house scam scanner**;
- has an executive sponsor;
- can run a **90-day sandbox pilot**.

That pilot has to meet the regulators' Joint Standard 2 on cybersecurity: checks on third-party providers, defined security duties, and exit terms.

**What retailers need to see:**
- baskets they wouldn't otherwise get;
- the customer's loyalty ID passed through;
- no scraping (a feed agreement instead);
- attribution data.

---

## 5. What they use today, and why they'd switch

| Today | Its strength | Why switch to Trollie |
|---|---|---|
| Checking 4 stores by hand, flyers, driving around | Free, in their control | Same control; the comparison and the trips done for them |
| Sixty60 + Pixie / asap! + Penny / Dash | Fast, one store, loyalty built in | **Across stores**, with an honest total. Must keep their loyalty prices |
| ChatGPT or Claude for comparisons | General, flexible | Real South African prices, a basket that can actually be fulfilled, merchants checked, someone accountable |
| Grocify and other comparison apps | Comparison | Trollie goes beyond comparing: it builds the basket and follows through to delivery and refund |
| Bank scam tools (Capitec Scam Check, Discovery TRUST Alert) | Inside the bank they trust | Trollie works in WhatsApp, for any bank, focused on **shops and sellers** |

---

## 6. Long-term sustainability

### The hard truth

- **Serving a WhatsApp household is cheap:** about R2–R8 a month for messages, AI and hosting.
- **Winning customers is expensive:** an estimated R300–R800 per active household for a standalone brand, about R100 through a bank or retailer. *(Estimates.)*
- **A free consumer product alone never covers that.** Every South African consumer app that survived either became the default for a weekly need, or was **paid for by someone with margin** (Capitec, Sixty60, M-Pesa, Truecaller).
- **Third-party delivery and aggregators died or were bought:** Bolt Food, Jumia Food, Yebo Fresh, OneCart.

### Three business models

| Model | How it pays | Rough revenue per user | Risk |
|---|---|---|---|
| **A. Protection paid for by banks, insurers and telcos (lead)** | They pay per protected customer (about R1.50–R4 a month) or per check, for scam checks, merchant trust scores and agent spending controls | R2–R4 a month; payback under 6 months if the bank distributes us | Long sales cycles; data-sharing terms |
| **B. Labelled sponsored placements and brand insight** | Brands pay for clearly labelled "sponsored alternative" slots that **never displace the cheapest complete basket**; aggregated, consented insight | R2–R6 a month at 500,000+ monthly users | Needs scale; trust dies if labels blur (Instacart's $60M FTC settlement; the Honey lawsuits) |
| **C. Premium household tier and retailer deals (later)** | R29–R49 a month for family sharing, wallet limits and alerts; negotiated retailer fees once we can show baskets they wouldn't otherwise get | Small: Truecaller converts only 0.69% to premium | Don't build the plan on it |

### Retention built in from day one

1. **A weekly rhythm around payday and stokvel day.** The saved list comes back with one-tap reorder. *The list is the habit, not the app.*
2. **An honest-total ledger:** "quoted vs charged vs saved" each month.
3. **Household roles:** one list, many contributors, one approver. Stokvel mode with split totals.
4. **The scam checker as the everyday touchpoint** that leads people into lists.
5. **Visible merchant reliability scores.**
6. **No dark patterns:** no auto-enrolment, no unlabelled slots, one-tap revoke.

### Warning signs

| Signal | Red line |
|---|---|
| 30-day retention of list users | Under 5% after three cohorts (marketplace apps manage about 8%) |
| Weekly active lists ÷ monthly users | Under 35% |
| Quotes approved and fulfilled | Under 50% approved, or over 5% of baskets not fulfilled as quoted |
| Honest-total error (quoted vs charged) | Median over 2%, or *any* undisclosed fee |
| Payback on acquisition cost | Over 18 months |
| Cost per monthly user | Over R10 |
| Sponsored share of revenue | Over 60% with no bank, insurer or telco contract within 12 months |
| Scam-checker users → list users | Under 5% |
| Dependence on one retailer | Over 60% of baskets, or links breaking more than 1% a week |

### In five years

Trollie should be **the household's buying memory and guardian**, not another shopping app. It knows the family's brands, sizes, budgets and no-go items. It reprices the week's list across whichever shops exist. It's where a parent approves a child's or an AI agent's spending within limits. Its scam checker is the best because millions of households fed it. And it has **never once hidden a fee or ranked a sponsor above the cheapest complete basket.** It's free for households and paid for by banks, insurers and brands.

---

## 7. What changes in the plan

The research changes the 90-day focus in five ways:

1. **WhatsApp first, not the app.** WhatsApp is the main channel, approval happens on a light web page with fingerprint or face, and there's no app until people come back repeatedly.
2. **Loyalty prices are a must.** Let people add their Xtra Savings and Smart Shopper status. Where member prices are public, use them. Otherwise, say plainly *"member prices may be lower; we've shown the standard price"*. Never claim "cheapest" when it might not be true for that person.
3. **The scam checker focuses on shops and sellers,** inside WhatsApp, for any bank's customers. That's not where Capitec's in-app tool is aimed.
4. **The first business pitch goes to a mid-tier bank or a cyber-insurance agency, not the big banks.**
5. **Measure the hand-off into retailer apps from day one.** It's the biggest unknown.

---

## 8. Test before building (weeks 1–4)

| Test | Who | What we learn | Pass mark |
|---|---|---|---|
| **Concept test** | 200 people in the target group (online panel or community groups) | Does "send your list, get the cheapest complete basket, approve with fingerprint" appeal? Which of the four pitches wins? | 40% or more say "would use this month" |
| **Interviews** | 15 households (10 target mothers, 3 stokvel coordinators, 2 AI enthusiasts) | Their last real shop, what scares them, loyalty-card use, willingness to pay | Clear patterns, and no new fear that the design can't answer |
| **Concierge test** | 10 households over 2 monthly cycles | Their list on WhatsApp → a checked basket (built by the founder with our engine) → links into the retailer → did they buy? | 6 of 10 buy twice; hand-off drop-off measured |
| **Scam checker soft launch** | The founder's media and security network, community groups | Volume, share of real scams, forwarding | 300+ checks a month by day 60 |
| **Business conversations** | 1 mid-tier bank or fintech, 1 insurer, 1 retailer (Checkers/ShopriteX) | "What would you pay for or give us access to?" | One pilot, letter of intent or data-sharing discussion by day 90 |

**Decision rules:**
- **Concierge and concept both pass:** build the WhatsApp list-to-basket flow.
- **Only the scam checker passes:** lead with protection and add buying later.
- **Both fail:** stop and rethink before spending on licences or building.

---

## 9. Decisions for the founders

1. Adopt **working mothers in Gauteng** as the first customer group, with the **scam checker open to all**?
2. **WhatsApp first**, with fingerprint/face approval on a light web page and no app at launch?
3. Treat **loyalty prices as a launch requirement**?
4. Make the **public "Trollie will never…" promise** and the **refund promise in rands**?
5. Run the **week 1–4 tests** above (I can draft the concept test, the interview guide and the concierge WhatsApp scripts next)?

---

## Sources (main)

**Why people would use it**
- iqbusiness AfricanPulse, 8 April 2026.
- Visa Stay Secure 2026 (9 June 2026); Visa B2AI.
- Roots 8.1, 2025; NIQ 2025.
- Stitch Consumer Report 2026; Rogerwilco CX Report 2026; DHL E-Commerce Trends 2026.
- Checkout.com, June 2026; Accenture Consumer Pulse 2026; Worldpay 2025; Riskified 2025/26; ACI/YouGov.
- Kaspersky SA, April 2026; GASA State of Scams SA 2025 and 2026; infoQuest, October 2025; TransUnion 2025.
- World Wide Worx Online Retail 2026; Township CX Report 2025; Truth & BrandMapp 2025/26.

**Convenience**
- ICASA State of the ICT Sector, March 2026; GSMA; StatCounter.
- TechCentral on WhatsApp bundles; Standard Bank Township Informal Economy Report 2025.
- Clutch app-fatigue survey, April 2026.
- FIDO Passkey Index, October 2026; Entersekt, October 2026.
- Baymard; Airship 2025 benchmarks.
- *Journal of Retailing* on substitutions.
- Outlook Business on WhatsApp Pay India; TechCabal on Chowdeck.
- Capitec, Safaricom and MTN results.

**Trust**
- KPMG/University of Melbourne SA AI trust, May 2025; HSRC *Beyond the Hype*; Edelman Trust Barometer SA 2026.
- SABRIC 2024 and 2025.
- National Financial Ombud, December 2025.
- Standard Bank, FNB and TymeBank remote-access warnings.
- Capitec verified-call banner.
- UPI Circle; STRIDE elder-abuse study, 2026.
- UK PSR APP reimbursement results; Amex Agent Purchase Protection.

**Segments and reach**
- Stats SA GHS 2025; Stats SA mid-year estimates 2026.
- DataReportal Digital 2026 SA.
- NASASA; Microsoft AI Diffusion Report; Trade Intelligence, April 2026; Discovery/Visa SpendTrend26.
- GASA 2026; TechCentral on TymeBank and Sixty60.
- WhatsApp Business pricing and policy updates.
- Joint Standard 2 of 2024.

**Sustainability**
- Adjust, Phiture and AppsFlyer retention benchmarks.
- Truecaller Q3 2025.
- Sixty60, Capitec and Safaricom results; TymeBank CAC statements.
- Bolt Food, Jumia Food, Yebo Fresh and OneCart outcomes.
- Instacart FTC settlement; Honey lawsuits.
- Shoprite retail media (Moneyweb, July 2026); GSMA Scam Signal; Sleekflow WhatsApp rate card; Epoch AI inference trends.

Full URLs are in this session's five research briefs from 31 October 2026.
