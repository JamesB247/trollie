# Red-team critique: the trust layer, the co-pilot and "Trollie Home"

*31 October 2026 · written deliberately as the harshest critic, then a way forward · for founder decision*

This critiques [`STRATEGY_AGENT_TRUST_LAYER.md`](STRATEGY_AGENT_TRUST_LAYER.md), [`IDENTIFIED_AGENT_COPILOT.md`](IDENTIFIED_AGENT_COPILOT.md) and the "Trollie Home" idea: a computer-use agent on the user's Mac or PC, with the phone as the remote.

---

## Part 1: The critique

### 1. "Why not just use OpenClaw, Hermes, Claude or Gemini?"

- **The agents get better every month, and they're free or already paid for.**
  - Gemini in Chrome browses for you automatically.
  - Claude in Chrome runs inside the browser you already use.
  - Meta Muse and Grok pay through Stripe's wallet for agents.
  - OpenClaw and Hermes are open source.
  
  Anything Trollie's agent can click, theirs can click.
- **Checkers' robots.txt already explicitly allows the ChatGPT, Claude and Perplexity agents.** A Claude user can tell Claude to fill their Checkers cart today, without Trollie.
- **Pixie lives inside Sixty60 for free.** Any Sixty60 user who wants an AI to build the basket already has one.
- **"South African shopping skills" are a thin wrapper.** Retailer-specific click scripts break whenever a site changes, and general models need them less each quarter. That isn't a moat.
- **Verdict:** *another agent* loses. A South African startup cannot out-build Anthropic, OpenAI, Google or the open-source community on the agent itself.

### 2. "I'm scared to install that"

- **It looks like a scam.** South African banks keep warning customers never to install remote-access software. Scammers make victims install AnyDesk-style tools. A product that says "install our app, it controls your computer, and you can watch and take over from your phone" looks exactly like the scam we say we protect people from. For a company built on trust, that's fatal.
- **The operating system will warn the user.** macOS shows alarming prompts for Accessibility and Screen Recording access. Windows Defender and antivirus may flag an unknown automation tool. Many people's computers are shared, old, or company-managed (and locked down).
- **"Can it act on its own? Can someone hack it?"** Honestly, yes, at some level:
  - The best published prompt-injection rate is still about 1.4% of attacks succeeding.
  - About 15% of OpenClaw add-ons were found to contain malicious instructions.
  
  An agent that controls the whole machine can reach email, files and banking.
- **We become a honeypot.** Thousands of households' agent connections, purchase approvals and browsing sessions are worth attacking. A security founder's company would be judged harshest if breached.

### 3. "It has to be on, at home, online"

- A home computer must be **on, awake and connected** for the agent to work. Laptops sleep, power cuts and connectivity drops happen, and data costs money.
- **Reach is small.** Desktop and tablet are about 37–39% of South African web traffic. Of that, Mac is roughly 14–20% and Windows about 70% (StatCounter, mid-2026). **Many of our target households have no home computer at all.**

### 4. "It doesn't pay"

- **Screen-driving agents are slow and costly.** Published reports run from a few cents to several dollars per task, and some tasks take minutes. A 40-item grocery list can mean many screens and many model calls.
- **They aren't reliable enough yet.** Agents complete about 60–70% of live-web tasks in independent tests, with wrong variants and wrong quantities the top failures. Every failure is a support call, and grocery margins can't carry that.
- **Who pays, and how much?** Households won't pay R30–R50 an order for a bot, especially when Pixie and Penny are free.

### 5. "The retailer can switch it off"

- **Retailers control access.** Checkers allows AI agents today; it could change one line tomorrow. Sixty60's domain blocks all bots. Pick n Pay, Makro, Takealot and Clicks disallow cart and checkout. Takealot's terms ban robots.
- **Running from the user's own computer helps legally, but doesn't remove contract risk.** Amazon v Perplexity cost years of litigation, and that case is still going.
- **Building on someone else's platform without permission** is platform risk, the classic startup killer.

### 6. "The checkpoint is optional"

- **If the agent pays with the user's card on the retailer's own checkout, our checkpoint is only advisory.** A compromised or careless agent can skip it.
- The checkpoint only *enforces* anything when the money goes through a route Trollie controls: our wallet, a mandate held by a partner bank, a single-use virtual card, or a retailer partnership. **None of those exist yet.**

### 7. "The trust graph starts empty"

- **No data on day one.** Banks hold better fraud data (Capitec, Discovery), and big partners rarely share with a startup that has no data to share back.
- **A trust graph without volume is just ScamAdviser:** sold for under €4.5M.

### 8. "Too many directions, zero customers"

- **In two days we have proposed:**
  1. a multi-retailer grocery buyer;
  2. local merchants and dark stores;
  3. a food lifestyle app;
  4. a trust layer for banks;
  5. a consumer scam guardian;
  6. a browser co-pilot;
  7. a home computer agent;
  8. licences across Africa.
- **All of it is desk research.** Not one household interview, bank meeting or retailer conversation has happened.
- **The team is a founder and maybe one engineer.** Several of these alone could take years.
- **Verdict:** the biggest risk isn't technical. It's **spreading too thin before anything is tested with a real customer.**

---

## Part 2: The way forward

### The idea that survives

> **Don't build the agent. Be the part every agent needs in South Africa, and make the buying experience something people already trust: their phone and their own approval.**

Trollie works in three ways:
- **The shopping brain for South Africa,** which any agent can call.
- **The safety rails** in front of the money.
- **One phone app** where the household asks, approves and watches. **No software that controls the user's computer.**

### How it answers each critique

| Critique | Answer |
|---|---|
| "Why not OpenClaw or Claude?" | **They are our customers, not our competition.** Their agents call Trollie. They gain three things they can't do themselves. **(1) South African commerce intelligence:** canonical products across retailers, specials, minimum orders, delivery fees, the household's Locked/Preferred/Flexible brands, and the optimiser that answers "the cheapest *complete* order for this list at this address" in one call, instead of the agent browsing four shops for 20 minutes. **(2) Accountability:** a South African company that handles problems, refunds and complaints, under POPIA. **(3) Safety:** the checkpoint, merchant trust and spending limits. **For households without an AI,** the Trollie phone app (and later WhatsApp and voice) is the agent's front end |
| "Scared to install" | **Nothing is installed on the computer.** The phone app is the only Trollie software. Where a browser agent is used, it's one the user already trusts (Claude in Chrome, Gemini in Chrome), calling Trollie's skill. **Public promise: Trollie will never ask you to install remote-access software or give it control of your computer.** That promise is itself an anti-scam message |
| "Can it act on its own? Can it be hacked?" | **It can't spend without you.** No agent ever holds a card or password. Money moves only through a single-use approval (fingerprint or face) bound to the exact basket, or a limited mandate you set and can kill instantly. A **12-hour cooling-off** applies to any new agent or new mandate. Every step appears in a **live activity feed**. A plain-language **"What Trollie can and can't do"** page. Independent security audit and a public bug bounty. Later, a capped guarantee: if Trollie lets through something you didn't approve, we refund it |
| "Must be on at home" | Nothing runs on the home computer. Trollie's work (search, optimise, check) runs on Trollie's servers or inside the user's own trusted AI |
| "Doesn't pay" | Answering "cheapest complete basket" from our own product graph is **far cheaper than an agent screen-browsing four sites.** One structured call replaces dozens of screenshots. Revenue comes from labelled sponsored placements, retailer referral fees, and the trust layer sold to banks and insurers, not R50 a basket |
| "Retailer can switch it off" | **Phase 1** uses only what each retailer permits: product links and search links (Checkers and Woolworths publish llms.txt; Checkers allows AI user agents). **Phase 2** uses written access letters and basket hand-off (the ShopriteX ask). **No cart-filling where a retailer disallows it.** We become the identified agent traffic a retailer can see on a dashboard, not something to fight |
| "Checkpoint is optional" | Be honest in marketing. In Phase 1 the checkpoint *guards the plan* (right items, real merchant, within budget) and the human pays. It *enforces payment* only once there's a partner rail: a virtual card from a partner bank, a mobile-money mandate (M-Pesa Ratiba in Kenya, eKash in Rwanda) or retailer checkout. That's Phase 2–3, and the licence work in the strategy |
| "Trust graph starts empty" | Seed it from what we can see. **(1)** The free **WhatsApp "check this" service** (forward a link, ad, seller number or proof-of-payment). **(2)** Every basket and merchant outcome. **(3)** Public signals: domain age, company registration, lookalike domains. Offer banks and insurers **signals back** in exchange for theirs |
| "Too many directions" | **Pick one wedge for 90 days. Freeze everything else** (below) |

### The 90-day wedge

**Trollie: plan it, check it, approve it.** Phone only, no install.

1. **On the phone (Trollie app plus WhatsApp):** "Here's my usual list, under R2,000." Or forward a link: "Is this shop real?"
2. **Trollie answers in one step:** the cheapest complete basket at the user's nearby participating shops (from the optimiser), with honest totals; flags on dodgy merchants; and the merchant trust verdict on any link.
3. **The user approves on the phone** with a fingerprint or face.
4. **Buying in Phase 1:**
   - one-tap links into each retailer's own app or site (allowed today);
   - or, for users with Claude or Gemini in their browser, the Trollie skill fills the cart under the user's watch and stops at payment.

   The human pays in the retailer app, with their own card and 3-D Secure.
5. **Trollie follows up:** prices changed, items missing, merchant problems. Everything feeds the trust graph.

**What gets built (most of it already exists in this repository):**
- the optimiser and canonical product model;
- the quote and approval engine;
- merchant risk scoring;
- a new phone front end;
- a WhatsApp checker;
- a Trollie **MCP server** ("Trollie skill") with a small set of tools:
  - `plan_basket(list, address, budget)`;
  - `check_merchant(url | number)`;
  - `request_approval(quote)`;
  - `verify_cart(cart_extract, quote_hash)`.

**Frozen for 90 days:**
- the home computer agent;
- Trollie's own browser extension;
- dark stores and local merchants;
- the food lifestyle features (except saving a usual list);
- the Rwanda and Kenya licence work. *Except one exploratory call with Rwandan counsel, since that clock is slow.*
- the ShopriteX proposal rewrite. *Send only a short ask for an access letter and a product feed.*

### Test before building (weeks 1–4)

1. **15 household interviews,** using the personas in `WHO_IS_TROLLIE_FOR.md`. Ask about their last real shop, plus the "would you let an app do this?" and "what would scare you?" questions.
2. **A concierge test with 10 households.** They send their list on WhatsApp. The founder (a human) uses the existing optimiser to send back a checked, honest basket with one-tap links. Measure:
   - did they buy;
   - did it save time or money;
   - would they pay, and how much;
   - what scared them.
3. **Five "check this" users a day,** recruited through the founder's media and security network. Measure volume, and what fraction were real scams.
4. **Three B2B conversations:** a mid-tier bank or fintech, an insurer, and Checkers/ShopriteX. Ask each: *"What would you pay for, or give us access to?"*

### When to stop or change course

- Fewer than 6 of 10 concierge households buy through the prepared basket twice.
- "Check this" gets fewer than 300 checks a month by day 60.
- None of the three B2B conversations leads to a pilot, a letter of intent or a data-sharing discussion by day 90.
- The **"scared of it"** answers mention anything beyond what the phone-only design already removes.

If the concierge test fails but "check this" succeeds, the company becomes the **trust and anti-scam layer first** and buying comes later. If both fail, stop and rethink before spending money on licences.

### What Trollie Home becomes

It isn't killed; it's **postponed and changed**. If the 90 days show that households want buying done for them with no taps:
- it returns as a **Trollie skill for the user's existing trusted agent**, not our own controller, running in an **isolated browser profile**;
- it gets **live view and takeover only through the browser vendor's own mechanisms**, never a remote desktop;
- it is subject to the same checkpoint and the same retailer permissions.

---

## Decisions for the founders

1. **Accept the 90-day wedge** (phone-only plan, check and approve, plus the WhatsApp checker and the Trollie skill), and **freeze** the rest?
2. **Make the public promise:** "Trollie will never ask you to install remote-access software or take control of your computer"?
3. **Start the validation now:** 15 interviews, a 10-household concierge test and 3 B2B conversations?
4. **Keep the stop rules** above?
