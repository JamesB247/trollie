# The identified-agent co-pilot: research and design

*31 October 2026 · research and proposal; not yet a founder decision · companion to [`STRATEGY_AGENT_TRUST_LAYER.md`](STRATEGY_AGENT_TRUST_LAYER.md)*

## The idea

Trollie runs an AI shopping agent **inside the user's own logged-in browser**, at the user's request, while they can watch. The agent:
- **announces itself** as an agent;
- **hands control back** at every CAPTCHA, login, one-time PIN and payment step;
- sends every purchase **through Trollie's checkpoint** (the owner's instruction, a merchant trust check and an anomaly check) before any money moves.

There is no disguise, no CAPTCHA solving, no mimicking of human mouse movement, and no hidden traffic. The pitch to retailers: *"Households' AI agents will shop on your site anyway. Let in the identified agents that follow rules, instead of fighting anonymous bots."*

The rejected alternative was evasion: a human-like mouse, getting past CAPTCHAs, hiding behind the user's IP. It breaks retailers' terms, puts the user's account at risk, can't win an arms race against bot detection, and contradicts the trust-layer strategy.

---

## 1. Where the ecosystem stands (October 2026)

### Agents can now prove who they are

- **The IETF Web Bot Auth standard** (`draft-ietf-webbotauth-httpsig-protocol-01`, updated 29 October 2026):
  - lets an agent cryptographically sign its HTTP requests (RFC 9421), with a public key directory;
  - is still a working-group draft, not yet an RFC;
  - **Cloudflare's reference code includes a browser extension that signs every outgoing request.** That is exactly our use case.
- **Cloudflare signed and verified agents:**
  - since 1 July 2026, signed agents count as "Verified", with a new *Intermediary* label for agents acting for an end user;
  - registration is through a dashboard form;
  - the allow-list is **global**, so it covers South African sites on Cloudflare;
  - operators get delisted for hiding their purpose or ignoring the crawl delay a site sets.
- **Other bot-protection companies:**
  - Akamai, DataDome, HUMAN, Kasada, F5 and Arkose all launched "verified agent" programmes in 2025–26;
  - most accept Web Bot Auth or Know-Your-Agent tokens from Skyfire, Visa or Experian.
- **The big AI companies:**
  - ChatGPT's agent signs its requests;
  - Google's agent announces itself as `Google-Agent` and is testing Web Bot Auth;
  - **Claude in Chrome is barred from bypassing CAPTCHAs** and pauses at logins and CAPTCHAs.

### Retailers: openness is arriving through protocols and deals, not open doors

- **Card networks:** Visa's Trusted Agent Protocol (built on Web Bot Auth) has been live in Europe since July 2026. **No South African merchants are named yet.** Visa Agentic Ready in South Africa is for issuers only so far.
- **Shopify** asks agents to identify themselves, avoid "scripted workarounds" and get a final human review before buying.
- **Amazon** blocks third-party agents in its robots.txt and runs its own agent.
- **eBay** bans buy-for-me agents that skip human review.
- **Walmart and Target** prefer their own agents inside AI platforms.
- **No retailer anywhere publishes terms that let any identified third-party agent use logged-in carts and checkout.** Access today comes through platform protocols or bilateral deals.

### Amazon v Perplexity: what the appeal court said, and what it didn't

On **4 August 2026** the Ninth Circuit lifted the injunction against Perplexity's Comet browser agent:
- it said *"it is the user who 'accesses' Amazon's computers"*;
- it called the agent *"a tool, not a person"*;
- a key fact was that Perplexity's servers never talked to Amazon's servers directly;
- rehearing was denied.

The limits:
- it applies to this case's facts only;
- it is US computer-crime law, so at most persuasive in South Africa;
- contract and terms-of-use remedies remain open;
- a different set of facts (for example, the operator controlling the traffic) could change the outcome.

**Design lesson:** run in the user's browser, with no traffic from Trollie's servers to the retailer.

---

## 2. South African retailers: what we observed

We checked on 31 October 2026 using read-only requests from an overseas server, honestly labelled as `TrollieResearchProbe/0.1`. Results from a South African home connection may differ.

| Retailer | Bot protection (inferred) | Robots and AI rules | Signal |
|---|---|---|---|
| **Checkers** | AWS CloudFront | **Explicitly allows** ChatGPT-User, Claude-User, Perplexity-User, GPTBot, ClaudeBot and Google-Extended. Disallows /login and profile pages. Publishes an **llms.txt "for AI agents"** | **The most agent-friendly of the group.** Sixty60's own domain, however, blocks everything (`Disallow: /*`), and Pixie is an in-house competitor |
| Walmart SA | Akamai + HUMAN + F5 | No robots.txt | Parent company is agent-forward (UCP, Sparky); the site itself is strictly protected |
| Makro | Akamai + HUMAN | Disallows cart, checkout and account pages | Its terms already say that if a third party uses your login, you accept responsibility for their transactions; publishes llms.txt |
| Woolworths | Cloudflare + F5 | Robots.txt request blocked for our probe; llms.txt says "use the live product page as source of truth" | Agent-aware; Cloudflare makes verified-agent rules easy |
| Pick n Pay | CloudFront | Disallows cart, checkout and search; 10-second crawl delay | Penny is deliberately closed; terms bar robots without consent |
| Takealot | Cloudflare | Disallows cart and account pages | Terms ban "any robot… to monitor" |
| Clicks, Dis-Chem | Cloudflare (Dis-Chem challenged our probe) | Disallow cart and checkout | Low priority: health data in baskets (special personal information under POPIA) |
| Spar | Azure | Permissive | Online shopping runs through Spar2U and Uber Eats |

**No South African retailer has said anything publicly about letting third-party agents in.** Since Cloudflare, Akamai and HUMAN verified-agent features work worldwide, these sites *can* honour a verified Trollie agent. Whether they will is their own choice.

**Rule we adopt:** where robots.txt disallows `/cart` or `/checkout` (Pick n Pay, Makro, Takealot, Clicks), or a domain blocks everything (Sixty60), **the co-pilot does not fill carts without the merchant's written permission.** Discovery and product reading follow each site's rules.

---

## 3. South African legal position

*This is research, not legal advice. Get an opinion from South African counsel before launch.*

| Law | What it means for the co-pilot |
|---|---|
| **Cybercrimes Act s2** (unlawful access) | "Access" is defined very broadly. "Unlawful" is not tied to terms of use in the text, and there is no South African case on this. Commentators argue that **continuing after a cease-and-desist** could be unlawful. **Risk is low** while the user is the account holder, is present, the agent declares itself and nothing is bypassed. **It becomes medium to high after a retailer objects**, so the agent must stop immediately on request |
| Cybercrimes Act s7 | Offence to acquire or use passwords to commit unlawful access. **Trollie never handles user credentials** |
| ECTA s86 | Repealed by the Cybercrimes Act |
| **ECTA s20** (electronic agents) | A person using an electronic agent is **presumed bound** by its transactions, with a material-error escape for individuals. This makes the **final human review and passkey approval essential** |
| Consumer Protection Act | Trollie probably counts as an "intermediary" acting for the consumer, with duties to disclose and deal fairly. Counsel to confirm |
| **POPIA** | s19: keep session data secure (the Regulator has already issued an enforcement notice against Dis-Chem). s72: sending page content or screenshots to an offshore AI model is a cross-border transfer, so get consent or use a compliant processor agreement. Pharmacy baskets can reveal health data |
| Contract | Breaching terms (for example, Takealot's) can mean account suspension or damages, so **get written permission per merchant** |

**The binding constraint is retailer permission, not criminal law.**

---

## 4. How to build it

### What the shipped browser agents teach us

| Lesson | Evidence |
|---|---|
| Keep site lists, credential handling and payment stops **in code, outside the model** | Google Chrome agent: "origin sets" and a separate critic model that sees only action metadata. Edge: the agent cannot reach passwords or the wallet. Claude in Chrome: no CAPTCHA bypass, and pauses at logins |
| **Stopping at CAPTCHAs must be enforced in code** | ChatGPT's agent clicked Cloudflare's "I am not a robot" box itself (July 2025) |
| Prompt injection is still real | Best published rate is about 1.4% of attacks succeeding (Anthropic, Nov 2025), "still meaningful risk". Comet bought from a fake Walmart and filled in a phishing login (Guardio). Near-invisible text in screenshots hijacked agents (Brave) |
| Shopping agents get variants and quantities wrong | Shopping benchmarks report wrong item, wrong quantity and wrong address as the main failures. Live-web success is around 60–70% in independent tests |
| Two reference products have shut | ChatGPT Atlas (stopped 9 August 2026) and Project Mariner (May 2026). Their safety patterns are still useful |

### Reach (corrected)

Earlier documents said about 77% of South African web traffic is mobile. **StatCounter (May–June 2026) shows South Africa at about 60–63% mobile and 37–39% desktop**; the 70%+ figures are Africa-wide. Chrome on Android doesn't run extensions, and iOS Safari extensions are fragile. So:
- **Desktop (Chrome/Edge extension):** the full co-pilot, reaching roughly 37–39% of traffic.
- **Mobile:** the user shares a list, link or screenshot with Trollie, Trollie prepares a checklist with deep links, and login and payment open in the real browser (Custom Tabs / Safari View Controller). A co-pilot inside the Trollie app's own browser comes **only per retailer that agrees**.
- **Don't** use Android accessibility automation; Google Play restricts it.

### Reference design

1. **Extension (Chrome/Edge, Manifest V3).**
   - Content scripts only. No `debugger` or `cookies` permission.
   - Optional host permissions only for named retailers.
   - A side panel showing "Trollie agent is acting", a live step log, and Pause/Stop buttons.
2. **Local controller with a closed action vocabulary:** `search`, `open(product)`, `setQty`, `addToCart`, `readCart`, `goto(allow-listed origin)`.
   - Per-retailer adapters.
   - **Hard-coded stops** at login forms, OTP fields, CAPTCHA frames, challenge pages and payment pages.
   - The model can only choose among elements the controller already found; it can't output URLs or scripts. Chrome's store policy forbids remotely fetched code anyway.
3. **Identity.**
   - Agent-tab requests carry a **Web Bot Auth signature** (based on Cloudflare's reference extension) and a user-agent token `(compatible; TrollieAgent/1.0; +https://…/agent)`.
   - Public key directory at `/.well-known/http-message-signatures-directory`.
   - Human pace; honour crawl delays; back off on HTTP 429.
4. **Model calls (server-side, quarantined).**
   - Personal data is removed before anything is sent (names, addresses, card fragments, loyalty numbers).
   - Only product and cart extracts go to the model.
   - No tools, no URLs.
   - Optional: a separate critic model that sees only action metadata.
5. **The checkpoint (the existing Trollie core).**
   - **Input:** the intent (canonical products and quantities, fixed *before* browsing), the retailer, a **deterministic cart extract and its hash**, and the owner's quote approval or mandate.
   - **Checks:** merchant trust, a line-by-line comparison of cart against intent (GTIN/SKU, pack size, quantity, unit price), spending caps and frequency, and anomalies (new payee, new address, price jump).
   - **Output:** a **single-use token bound to the cart hash**, or a stated reason for refusing. Any change means a new approval.
6. **Hand-off points.** Login, 2FA, CAPTCHA, address change, the passkey approval and payment are always done by the human, or paid through a Trollie-controlled rail.
7. **Evidence.**
   - An append-only step log: actions, origins, cart hashes, the checkpoint verdict.
   - Screenshots kept on the device only.
   - Linked to the purchase record.

**Honest limit:** a check on the user's device constrains the agent, not a compromised device. Real enforcement of "before money moves" only happens when payment goes through a Trollie-controlled rail. Checkout with a card on the retailer's own site stays a human step.

### Smallest first version (MVP)

- A desktop Chrome extension; **one partner retailer (or a fictional one)**; only "repeat my usual list".
- Deterministic adapters first, with a model used only to tell similar products apart.
- The cart-vs-intent check, the checkpoint token and passkey approval.
- Login and payment always by the human.
- **A red-team test suite in CI:** hidden-text pages, a fake CAPTCHA and a fake shop, with the target **"0% reach checkout without approval"**.

This maps directly onto the existing engine: quote-hash approvals, mandates (A2) and the agent guard (I-046).

---

## 5. Checklist: being a good, identified agent

1. Ed25519 signing keys in a key-management service; a published key directory; Web Bot Auth signatures on agent-tab requests.
2. An honest user-agent token. **Never impersonate plain Chrome.**
3. Register with Cloudflare (BotBase, as Intermediary/Agent), DataDome, Kasada and HUMAN. Reach Akamai and F5 through Visa's protocol or Skyfire. Engage Visa South Africa about its agent directory.
4. Attribute the end user with a pseudonymous `Forwarded` header (Cloudflare is piloting this). Keep a signed approval log for every order.
5. Human pace; honour crawl delays and request rates; back off on 429 / `Retry-After`.
6. Read and honour robots.txt and the terms of each site. A disallowed cart or checkout means **written permission first**.
7. Hand off every CAPTCHA, login, OTP, 3-D Secure and payment step. **No solvers, stealth plug-ins, fingerprint spoofing, residential proxies or stored credentials.**
8. Run in the user's browser. **No traffic from Trollie's servers to the retailer.**
9. A final human review before every order is submitted (Shopify/eBay norm; ECTA s20).
10. Treat merchant content (robots comments, agents.md, llms.txt, product pages) as **data, never instructions**.
11. Stop immediately on a retailer opt-out or cease-and-desist. Publish a contact address.

---

## 6. Which retailers to approach, in order

1. **Checkers / ShopriteX.** The strongest public signal: AI agents are explicitly allowed in robots.txt and it publishes llms.txt. The tension is the closed Sixty60 app and its own assistant, Pixie. **Ask:** a written access letter for signed, rate-limited, human-approved Trollie agent traffic. Start with a read-only catalogue pilot, then cart-filling. This can be added to the ShopriteX conversation.
2. **Walmart SA / Makro (Massmart).** The parent company is agent-forward, and Makro's terms already contemplate third parties transacting on a user's login. Approach through Massmart e-commerce or Walmart International, and lead with alignment to Visa's agent protocol and Akamai's know-your-agent programme.
3. **Woolworths.** Agent-aware llms.txt; Cloudflare makes verified-agent rules easy; its own assistant isn't due until 2027.
4. **Pick n Pay.** Penny is closed and its cart and checkout are disallowed. Pitch Trollie as complementary.
5. Takealot, Clicks, Dis-Chem, Spar: later.

**Every request asks for the same written access letter:**
- the agent's identity and signing keys;
- which pages it may use;
- a rate cap;
- a contact for revoking access;
- how data is handled.

**In return** we offer the retailer a dashboard of Trollie-signed traffic, so they can see exactly what our agents did.

---

## Decisions for the founders

1. Build the co-pilot as described: transparent, signed, human hand-offs, checkpoint-gated? This is a scope change from CLAUDE.md, which currently excludes third-party agents and AI model calls.
2. First retailer to approach for an access letter: Checkers/ShopriteX (recommended), or Massmart?
3. MVP target: a desktop extension with one retailer and "repeat my usual list", plus the mobile share-and-hand-off flow?

## Sources (main)

**Standards and agent identity**
- IETF Datatracker: Web Bot Auth drafts; AIPREF.
- github.com/cloudflare/web-bot-auth.
- Cloudflare blog, "Signed agents", 28 August 2025; Cloudflare verified-bots documentation, updated 8 October 2026.
- Akamai, 15 June 2026; DataDome via Experian, 2026; HUMAN AgenticTrust; Kasada, 21 January 2026; F5 and Skyfire, 18 March 2026; Arkose, 16 June 2026.
- OpenAI Help 11845367 (ChatGPT agent allow-listing); Google user-triggered fetchers, 19 August 2026; Claude in Chrome help pages.

**Card networks and retailer policies**
- Visa Trusted Agent Protocol, 14 October 2025; Visa Europe live launch, 2 July 2026; Visa Agentic Ready CEMEA, 20 May 2026.
- Shopify robots.txt and agents.md (observed 31 October 2026); Amazon robots.txt (observed 31 October 2026); eBay user agreement, February 2026.

**Amazon v Perplexity**
- Jones Day, September 2026; Troutman, 21 August 2026; order denying rehearing.

**South African retailers and law**
- Read-only checks of SA retailer sites (headers, robots.txt, llms.txt, terms), 31 October 2026.
- Takealot and Makro terms; TechCentral on Pixie and Penny; BusinessTech on My Woolies Chef.
- Cybercrimes Act 19 of 2020 (s2, s7, Schedule); ECTA s20; POPIA s19 and s72; Information Regulator enforcement notice against Dis-Chem.
- Legal500 (Swart, 2022) on scraping; UK CMA guidance on agentic AI, 9 March 2026; CERRE.

**Agent safety and reliability**
- Anthropic: Claude for Chrome, August 2025; prompt-injection defences, November 2025.
- Google security blog, 8 December 2025.
- Guardio Scamlexity; Brave on Comet and Opera Neon.
- Microsoft Magentic Marketplace.
- OWASP Top 10 for Agentic Applications 2026; CaMeL (arXiv 2503.18813).
- Online-Mind2Web (arXiv 2504.01382); DeepShop; Amazon-Bench.
- Chrome extension documentation (debugger, sidePanel, Prompt API, Web Store policies); StatCounter SA platform share; 1Password agentic autofill.

Full source lists with URLs are in this session's two research briefs from 31 October 2026.
