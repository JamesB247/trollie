# The hard bet: Africa's trust layer for money that AI agents move

*Strategy proposal · 31 October 2026 · for founder decision; nothing here is adopted yet*

It's based on seven research briefs from 31 October 2026: Asia, the United States, Europe and the UK, South Africa, the rest of Africa, consumer anti-scam tools, plus the earlier food-lifestyle and retailer research. Claims carry their source. Figures marked [UNVERIFIED] came from a single or secondary source and need checking before anyone outside the company sees them.

---

## 1. The point

Recipes, baskets, price comparison and "AI that shops" are all being commoditised:
- **The big grocers:** Pixie, Penny and My Woolies Chef already offer them for free.
- **The AI platforms:** ChatGPT, Gemini, Meta Muse and Grok are adding shopping themselves.

None of that can be defended.

What *is* hard is the layer between a person's money and an AI agent that wants to spend it:

1. **An authority layer.** Owner-signed, limited, revocable instructions ("mandates") that are checked by trusted software before any money moves, on the payment rails Africa actually uses: mobile money, PayShap, instant EFT and cards.
2. **An African scam and merchant trust graph.** Merchants, websites, payout accounts, phone and WhatsApp numbers and delivery outcomes, labelled with *confirmed* fraud. It's queried at the moment of payment, by people and by their agents.
3. **The licences and integrations to sit in the payment path** in several African countries: a payment-initiation licence in Rwanda, then Kenya and South Africa, plus telco and bank integrations.

Each of these takes years, relationships and data. That's exactly why a Visa, a Mastercard, a Lesaka or a telco fintech would rather buy than build. The groceries engine we built is not wasted: it becomes the **reference implementation and the first demo vertical** of this layer.

---

## 2. What the world is doing: the evidence

### Asia is ahead (as the founder expected)

| Who | What | Why it matters to us |
|---|---|---|
| **Alipay AI Pay / Agentic Commerce Trust Protocol** (China) | 100M+ users (Feb 2026). About 300M agent payments by May 2026. In *delegated* mode the user presets **spending limits and preferred merchants**, then the AI buys without asking each time. Backed by Alipay's "Full Compensation" guarantee | Proof that limit-bound delegation works at massive scale, *when someone stands behind it with a guarantee* |
| **Ant International Agentic Mobile Protocol** | Users approve a *task*, not an account: goal, budget, conditions, which wallet, and re-confirmation if the price rises. **Know Your Agent trust rating** sets each agent's autonomy. **AgentSafePay** money-back guarantee for purchases the AI got wrong. Being made to work with Visa and Mastercard through Singapore's central bank. Ten wallets in phase I, including GCash, Toss, KakaoPay and TrueMoney | The best design for task-level consent, and it's open-sourced |
| **India UPI Reserve Pay and UPI Circle** | Funds **blocked at the bank for one merchant**, capped (₹10,000) and expiring (90 days). Live in pilots with ChatGPT (Oct 2025) and Claude (Feb 2026). NPCI's doctrine: *"AI may recommend, but authentication and final settlement must follow deterministic auditable rules"* | Almost exactly the existing Trollie envelope-and-grant design, done at the bank level |
| **Singapore** | Shared Responsibility Framework: a 12-hour cooling-off on new devices, a self-service kill switch, and a fixed order for who pays. Money Lock. Police restriction orders. Government safety ratings for marketplaces. 42,000 scam sites taken down. 2025 scam losses **down 19%** | The best liability design, and it turns straight into product features |
| **Hong Kong Scameter** | Police-confirmed scam reports trigger a warning on the payee *at the moment of transfer*, across 32 banks | Shows that outcome-labelled data plus a warning at the right moment works |

### United States: rails built, little money moving, trust is the gap

- **The rails exist.** Visa Intelligent Commerce, Mastercard Agent Pay (with "Verifiable Intent"), Stripe's agent wallet and Shared Payment Tokens, Google's AP2 mandates (now at the FIDO Alliance), Amex's agent purchase protection. **Almost all are US-only.**
- **Very little money moves through them.** OpenAI **shut down Instant Checkout** in March 2026: only about 30 merchants went live, and Walmart saw conversion 3× lower. Visa's CEO called agentic commerce "nascent" this week and said "trust is the next growth vector".
- **The big money is buying trust, not checkout.** In 2026 deals: Visa → BioCatch **$2.4bn**, Mastercard → BVNK **up to $1.8bn**, Okta → Permiso about $200M. In 2024: Mastercard → Recorded Future **$2.65bn**. Standalone agent-payment startups raise $5–35M and have no exits yet.
- **Banks are pushing back.** JPMorgan, BofA, Citi and Morgan Stanley are restricting third-party agents found acting in customer accounts (Axios, Oct 2026). Nobody has settled who carries liability for agent payments.

### Europe and the UK: liability and mandates are being written into law

- **UK mandatory refunds for scams the customer authorised** (Oct 2024): 88% of money claimed returned; losses fell about 21% (about £73M a year). 60% of victims were purchase-scam victims. **The guarantee forced prevention.**
- **Pre-approved bank payments with limits** (UK commercial "VRP", live June 2026): a revocable mandate with per-payment, per-period and expiry limits.
- **EU payment law (PSD3/PSR):** banks and payment firms are liable when their fraud prevention is inadequate, and platforms that ignore fraud reports must repay the payment firm. The **EU digital identity wallet** includes a standard format for payment mandates.
- **Regulators say the core problem is unsolved.** The Bank of England (Breeden, June 2026) names it: *"how users securely give consent and authorisation to agents, especially for multiple transactions"* and *"how … liability [is] assigned"*. UK Treasury rates an agentic-payments trust framework a **"high" priority**.
- **Data in the payment path sells; lookup data doesn't.** ScamAdviser, a consumer site-checker, sold for **≤ €4.5M**. Featurespace (about £700M reported), BioCatch ($1.3bn, then $2.4bn) and Recorded Future ($2.65bn) are fraud data used *inside* banks' or networks' payment decisions.

### South Africa: real pain, no liability regime, no merchant register

- **Digital banking fraud R2.4bn in 2025 (+29%).** **88.6% of cases happen in banking apps**, mostly through social engineering. Average loss is R21,865.
- **The victim usually pays.** The Code of Banking Practice is voluntary. Only 40% of bank fraud leaders say they reimburse more than half of victims.
- **Online purchases are the top complaint at the Consumer Goods and Services Ombud,** and there is **no public, machine-readable register of verified SA online merchants**.
- **The rails for agents are arriving:** Visa Agentic Ready launched in May 2026 with **FNB and Discovery**; PayShap Request is live; Discovery offers up to 50 virtual cards with individual limits.
- **A licence route for non-banks is coming.** The new payment authorisation framework (including **payment initiation**) is due to be finalised **by the end of November 2026**. The Prudential Authority also proposes exempting some payment activities from banking rules.
- **No local startup offers an agent wallet with mandates.**

### The rest of Africa: a faster licence and better rails

- **Rwanda** has a ready licence: a **payment-initiation (Category IV) licence needing about US$35k of capital**, a **90-day decision clock** and a free sandbox. The central bank has **binding AI rules (No. 52/2026)** that treat payments and fraud AI as high-risk. The national instant-payment system (eKash) has a fee cap and a link to Tanzania under way.
- **Kenya** has **M-Pesa Ratiba**, a standing-order API the customer authorises with their PIN (40M active M-Pesa users). Mastercard ran its **first live Agent Pay transaction in Eastern Europe, the Middle East and Africa in Nairobi** (Nov 2025). A payment-initiation licence (KES 5M) is in the draft 2026 payments bill.
- **Nigeria's** central bank has a draft **fault-based framework for scams the customer authorised** (Nov 2025): the institution that fails to stop the money bears the loss. That makes banks **buyers** of prevention.
- **Across Africa,** INTERPOL (2026) finds mobile-money fraud reported by 97% of countries and AI linked to about 55% of cybercrime. Paystack's "Index" already lets Nigerians pay through Claude, ChatGPT and OpenClaw.

---

## 3. What we tested and dropped: the honest part

| Idea | Verdict | Why |
|---|---|---|
| Grocery ordering and delivery | Not the company | Retailers own it; their own AI assistants already do it |
| Food lifestyle app (recipes, photo to recipe) | Nice to have, not a moat | Commodity features; 3–4% of users still active after 30 days |
| A consumer "dodgy website" browser extension | Not a moat on its own | Guardio ($1.1bn valuation), Norton, McAfee, Bitdefender and Malwarebytes do it, and Chrome and Edge are building it in for free. In SA **88.6% of fraud cases are in banking apps**, and 77% of web traffic is mobile, so a browser extension sees a minority of losses |
| A per-user model watching for out-of-character behaviour | **Not a moat** | **Discovery's TRUST Alert and Capitec already do this free**, with the bank's own data, which is better than ours. Per-user cloud sandboxes cost about US$37 a user a month; most SA phones can't run on-device language models |
| Consumer protection for AI agents only | Contested | Gen Digital (Norton) launched an Agent Trust Hub and AI Agent Protection in 2026; Chrome confirms purchases inside its own agent |

What's left standing is the **payment-path layer**. Banks, wallets and telcos integrate it, and the consumer features feed its data.

---

## 4. The product: three layers

### Layer 1: Authority (the "trusted executor")

The software that decides *whether an agent may spend this money, here, now*. It's built from Alipay's delegated mode, Ant's task mandates, UPI Reserve Pay, the UK's limited mandates and Google's AP2.

- **Mandates.** Owner-signed with a passkey, versioned, scoped (merchant categories, merchant allow-list, per-transaction cap, monthly cap, expiry), revocable instantly. Every change to the payee, amount ceiling or merchant needs re-signing.
- **Two modes, as Alipay offers:** *approve each purchase* (the default) or *delegated within a mandate* (off by default).
- **Singapore-style protections:** a 12-hour cooling-off on new agents, new mandates and new devices; a self-service kill switch; real-time notifications.
- **Know-your-agent:** each agent gets its own credential and trust level. Refused attempts count as strikes, and repeated strikes suspend the agent.
- **An evidence chain for disputes:** a hashed quote, the signed mandate and what the owner was shown, exportable for banks and ombuds. It maps onto Mastercard's Verifiable Intent and Visa's agent tokens.
- **It runs over rails, not instead of them.** Mobile money (M-Pesa Ratiba, MTN MoMo), PayShap Request, virtual cards from issuers, and bank-held wallets.

**Already built in this codebase (synthetic):** quote-hash-bound passkey approvals, mandates off by default (A2), exclusive agent envelopes and scoped revocable grants, the rule that refunds never restore spending limits, agent strike suspension (I-046), a double-entry ledger, and evidence that survives crashes. *This is the reference implementation.*

### Layer 2: Trust graph (the data moat)

A graph that links **merchant → domain → company registration → payout account → phone/WhatsApp numbers → delivery and dispute outcomes → confirmed fraud**. It's queried at the moment of payment and returns *allow / warn / hold* with reasons. That's Hong Kong's Scameter and Singapore's marketplace ratings, built for Africa.

- **Inputs:**
  - outcomes from our own transactions (the merchant probation and overdue-leg logic is already built, I-044);
  - consumer reports from Layer 3;
  - partner bank and telco signals (SA's GSMA/SABRIC "Scam Signal" is the model);
  - checks on merchant identity and bank accounts;
  - lookalike-domain monitoring;
  - takedown results.
- **Output to people:** "This store is 3 weeks old, its bank account doesn't match its name, and 4 people reported non-delivery."
- **Output to agents:** a machine-readable verdict that the authority layer enforces.
- **Why it compounds:** every warning, block, refund and report makes it better, and it's local data that global players don't have.

### Layer 3: The consumer face (data funnel and brand, not the main revenue)

- **"Check this" on WhatsApp:** forward a link, an ad, a proof-of-payment screenshot or a seller's number, and get a verdict. WhatsApp is where South Africans live, and it works on any phone.
- **Android:** a warning at the moment of paying a new or high-risk payee, especially while on a call with an unknown number. Discovery's data shows calls are the danger signal. iOS gets the share-sheet check and the Safari extension.
- **The agent wallet ("Safe-Spend"):** the person's own AI agents spend only inside their mandate, and only with merchants the graph trusts.
- **Warn, don't block,** except where the owner chose a hard rule. Warnings are rare and specific, because frequent warnings get ignored (USENIX 2013: users clicked through 70% of SSL warnings, but only 9–23% of rarer malware and phishing warnings).

### Later: the guarantee

Once we have loss data, offer a capped **"nothing outside your mandate" guarantee**, backed by reserves or reinsurance. That's Alipay's Full Compensation, Ant's AgentSafePay and the UK's refund scheme. In a market where victims usually pay, this is the strongest consumer promise there is, and nobody can offer it without the loss history.

---

## 5. Who pays

| Buyer | What they buy | Why now |
|---|---|---|
| **Mid-tier banks and fintechs** (TymeBank, OM Bank, African Bank, Bank Zero/Lesaka, Access, Sasfin; later Kenyan and Nigerian banks) | A trust-graph API at payment time; mandate verification for agent payments; dispute evidence | They lack Capitec's or Discovery's AI teams. Pressure for SA refund rules is building. Nigeria's draft makes banks liable |
| **Telco fintechs** (MTN MoMo, Airtel Money, M-Pesa, VodaPay) | Agent mandates over mobile money, plus mule and scam signals | Agents will reach mobile money next. Airtel Money and MTN Fintech are being valued in the billions |
| **Insurers** (Phishield, Santam, funeral and household insurers) | Prevention bundled with scam cover; claims data | Only 2% of South Africans have cyber cover; prevention lowers claims |
| **Merchants and payment providers** (Stitch, Peach, Paystack, Yoco, Takealot) | "Verified merchant" status, so agents and customers trust them; agent-ready checkout | Agent traffic needs a trust signal (Visa's Trusted Agent Protocol, Mastercard's Know Your Agent) |
| **Agent platforms** (Paystack Index, local AI apps, global agents entering Africa) | A licensed, local authority layer and trust verdicts | Their US rails don't cover Africa |
| Consumers | Free core service; a premium Safe-Spend tier later | Mostly a data and brand funnel; South Africans rarely pay for security apps |

---

## 6. Where we launch, and in what order

| Phase | When | Moves |
|---|---|---|
| **0: Foundations** | Now to Q2 2027 | **South Africa (home):** the WhatsApp "check this" service and the first trust graph; 2–3 design partners (a mid-tier bank or fintech, an insurer, a payment provider); apply for payment-initiation authorisation once the SA framework is final. **Rwanda:** central bank sandbox, then the Category IV licence (about US$35k capital, 90-day clock); integrate eKash, MTN MoMo and Airtel; register data controllers; map controls to the AI rules (No. 52/2026). Optional: a Mauritius holding company |
| **1: Prove it** | 2027 | **Kenya:** agent mandates over M-Pesa Ratiba through a licensed partner; apply for the payment-initiation licence when the bill passes. **Rwanda to Tanzania** cross-border pilot over the eKash link |
| **2: Scale B2B** | 2027–28 | **Nigeria:** sell trust-graph and mule detection to banks under the scam-liability framework; agent payments once open-banking payment initiation is live. **Ghana** with a local partner (30% local equity required) |
| **3: Region** | 2028+ | **Southern Africa:** Zambia, Botswana, Namibia. **Portuguese-speaking:** Angola (central bank sandbox, KWiK instant payments). Egypt and Ethiopia later |

Why not South Africa alone? SA has the money and the fraud, but its non-bank licence is still being finalised and banks dominate. Rwanda gives us a **licensed, AI-regulated track record within a year**, and Kenya gives the best rails for agents. Holding licences in several countries, with telco integrations and one shared trust graph, is the asset a buyer can't quickly copy.

---

## 7. The calculated gamble: bets, risks and when to stop

**The bets:**
1. Agent payments reach Africa within 2–3 years. Visa Agentic Ready (FNB, Discovery), Mastercard in Nairobi and Paystack Index suggest it's starting. *Someone must govern them locally.*
2. Banks, telcos and insurers will pay for trust data with confirmed outcomes and for mandate checks, because liability is shifting onto them (Nigeria; the SA reimbursement debate; the UK precedent).
3. We can get data partnerships: banks, SABRIC, telcos, merchant payment providers. **This is the biggest risk.**

**The risks:**

| Risk | Mitigation |
|---|---|
| Global networks or Gen Digital move into Africa first | Partner with them: plug into their agent protocols and be their local trust and licence layer. Being partner-shaped makes us an acquisition target, not a competitor |
| Big banks build it themselves (Capitec, Discovery) | Sell to mid-tier banks, telcos and insurers. Sell agent mandate checks across banks, which no single bank can provide |
| Data partners say no | Start with our own data (WhatsApp reports, merchant outcomes); offer something in return (we share signals back) |
| Licence delays | Partner-licensed entry while applying; Rwanda first, because its timeline is defined |
| POPIA and data-protection laws | Privacy by design: minimal data, no message content kept, encrypted profiles, audit trails; register in each country |
| Liability for warnings | Warn, don't decide. Hard blocks only on the owner's own rules. Clear terms. The guarantee only once loss data supports it |

**When to stop or change course:**
- No paid pilot or signed letter of intent from a bank, telco or insurer within 6 months.
- No data partner within 9 months.
- No sandbox admission in Rwanda (or an equivalent) within 9 months.
- The WhatsApp checker gets fewer than 10,000 checks a month after 6 months.

---

## 8. Who buys this, and what they've paid

| Likely buyer | Why | Price anchors |
|---|---|---|
| **Visa / Mastercard** | Buying trust and fraud data globally; need African agent-payment coverage; Mastercard holds a stake in MTN's fintech | BioCatch $2.4bn; Featurespace about £700M; Recorded Future $2.65bn; Mastercard's minority stake in MTN Fintech at a $5.2bn valuation |
| **Gen Digital, Check Point, Okta** | Consumer and agent security; no African data | Check Point–Lakera about $300M; Okta–Permiso about $200M; F-Secure–Lookout consumer arm $223M |
| **Lesaka, Capitec, FirstRand, Discovery** | Scam leadership and agent readiness in SA | Lesaka: Adumo R1.59bn, Bank Zero up to R1.09bn, Recharger R507M |
| **Telco fintechs** (MTN MoMo, Airtel Money, M-Pesa) | Agent commerce on mobile money; fraud and mule control | Airtel Money IPO (Oct 2026) [valuation UNVERIFIED] |
| **Pan-African payment companies** (Flutterwave, Moniepoint, Paystack/Stripe) | Consent, fraud and licence coverage | Flutterwave–Mono $25–40M |

Honest note: most African fintech exits are **US$25–100M**. The global trust-and-fraud deals are **$200M–$2.65bn**. What moves Trollie from the first range towards the second is the combination of **licences in several countries, a payment-path data network with confirmed outcomes, and agent-mandate infrastructure**.

---

## 9. What happens to what we've built

| Asset | New role |
|---|---|
| Quote/approval engine, mandates, envelopes and grants, agent guard, ledger | **Layer 1 reference implementation.** Generalise it from groceries to any merchant and rail |
| Merchant probation, overdue legs, scam-store suspension, circuit breakers | **The seed of Layer 2** (merchant outcome labels) |
| Crowd simulation with fraud and agent-hijack scenarios | **The demo and evidence for banks and regulators** ("watch the controls stop a hijacked agent") |
| Groceries optimiser, catalogue and food-lifestyle ideas | The **first demo vertical**, not the company |
| Positioning "Your list. Taken care of." (I-048) | **Needs revisiting:** it's a groceries line. Candidates: *"Your money's bodyguard."* / *"Let AI shop. Never get scammed."* / *"Safe hands for your money and your agents."* The **Trollie** name may suit a consumer product better than B2B infrastructure; decide later |
| ShopriteX proposal v4.0 | **Hold.** It sells a groceries channel. If it's still sent, reframe it around Money Market plus safe agent payments, or treat it as a separate side deal |
| CLAUDE.md sprint scope | **Needs rewriting** for the new build: trust-graph service, WhatsApp checker, mandate API over a rail sandbox (M-Pesa Daraja/Ratiba sandbox, MTN MoMo sandbox) |

---

## 10. Decisions for the founders

1. **Adopt this as Trollie's core strategy?** It means the authority layer plus the trust graph plus multi-country licences, with groceries as the first demo vertical.
2. **First consumer touchpoint:** the WhatsApp "check this" service (recommended), the Android payment warning, or the agent wallet.
3. **Rwanda:** start a sandbox and Category IV licence application now (needs legal counsel in Kigali)?
4. **Design partners:** which 3 to approach first? Suggested: one mid-tier SA bank or fintech, one insurer, one payment provider.
5. **ShopriteX:** hold, reframe, or send as a separate groceries side deal?
6. **Brand:** keep Trollie for the consumer face and pick an infrastructure name later, or rename?

---

## Sources (main)

**Asia**
- Ant Group / Business Wire, 23 February 2026 (Alipay AI Pay 100M users).
- The Paypers, January 2026 (Agentic Commerce Trust Protocol).
- FinTech Global, 23 April and 18 September 2026.
- TechNode, 26 May 2026.
- Ant International release, 11 September 2026; CNBC, 10 September 2026.
- Business Today (India), 20 February 2026 (Razorpay, NPCI and Claude).
- Electronic Payments International, 10 October 2025.
- Pine Labs Reserve Pay documentation.
- MediaNama, September 2026 (NPCI doctrine).
- MAS/IMDA, 24 October 2024 (Shared Responsibility Framework).
- The Star, 25 February and 13 March 2026.
- MHA (marketplace safety ratings).
- GovTech (scam-site takedowns).
- HKMA, 1 August 2024 (Scameter).

**United States**
- Payments Dive, 28 October 2026.
- CNBC, 20 March 2026 (Instant Checkout shut down).
- Visa newsroom: 20 October 2026; BioCatch, 3 August 2026.
- Fortune, 17 March 2026 (Mastercard–BVNK).
- TechCrunch, 30 July 2026 (Okta–Permiso).
- Stripe newsroom.
- FIDO Alliance, 29 April 2026 (AP2).
- Axios, 22 October 2026 (banks restricting agents).
- Guardio Scamlexity research, August 2025.
- Microsoft Research, Magentic Marketplace.
- FTC, March 2026.

**Europe and UK**
- PSR, 8 October 2025 and 1 July 2026 (refund scheme results).
- FCA, 2 June 2026 (commercial VRP).
- Bank of England (Breeden), 30 June 2026.
- Pinsent Masons, 16 July 2026 (Treasury).
- Council of the EU PSD3/PSR texts, April 2026.
- Euronews, 16 September 2026 (EU digital identity wallet).
- Deal coverage: Featurespace, BioCatch, Recorded Future, Onfido, IDnow, ScamAdviser.

**South Africa**
- SABRIC, 4 August 2026; BusinessTech, 6 September 2026.
- Consumer Goods and Services Ombud via EWN, August 2026.
- Banking ombud via The Citizen, 16 March 2026.
- Visa Agentic Ready, 20 May 2026.
- Webber Wentzel (authorisation framework); Prudential Communication 10 of 2026.
- Capitec, Discovery, Lesaka and Stitch releases.
- Moonstone; Intelligent CIO, 13 May 2026 (bank reimbursement survey).

**Rest of Africa**
- BNR Regulation 74/2023 (primary text); BNR AI guidelines No. 52/2026 (via AU Startups).
- Safaricom Daraja / Ratiba documentation.
- CBK draft National Payment System Bill, 2026.
- TechCabal, 2 December 2025 (CBN scam-liability framework).
- INTERPOL Africa Cyberthreat Assessment, August 2026.
- GSMA State of the Industry Report 2026.
- Nairametrics (Flutterwave–Mono).

**Consumer anti-scam**
- Guardio, 3 September 2026; Gen Digital newsroom, February–April 2026.
- Capitec (Scam Check), October 2026; Discovery (TRUST Alert).
- Apple App Review Guidelines; Google Play accessibility policy.
- StatCounter, September 2026.
- Akhawe & Felt, USENIX 2013.

Full source lists with URLs are in the seven research briefs from this session.
