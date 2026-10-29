# How shopping services abroad work with stores

Research for the founders, 29 October 2026. Question: how do grocery-delivery and AI shopping
services in other countries get goods from shops? Do they work with the shops, around them, or
replace them? What does that mean for Trollie's plan: agents with their own wallet, wholesale
accounts and human pickers first, then a dark store in Gauteng, then retailer agreements?

Not legal advice. Most figures come from news and trade press; company filings are cited where
they were found. Claims that could not be confirmed are marked.

## The short answer

Services abroad have used four ways to get goods. Most successful ones went through them in
this order:

1. **Buy at the shop without an agreement and mark up the price.** Instacart started this way.
2. **Turn volume into agreements, so the retailer pays the platform.** Instacart, Uber Eats and
   Mr D work this way today.
3. **Own stock in dark stores.** This worked only where order density was already proven, and
   most European and African attempts failed.
4. **Retailers choose to open their checkout to AI agents.** These rails are still being
   built. Agents that shop on retailers' websites without permission end up in court.

Trollie's plan follows the same order. The evidence says the second step (agreements) is what
makes the business, and the third (dark stores) is the riskiest. A dark store should follow
proven density, not drive it.

## 1. Buying without an agreement, then converting

**Instacart (United States, 2012 to 2014).**
- It had no store agreements and no product feeds at first. Staff bought at shelf prices and
  delivered ([Jarvis](https://www.alexanderjarvis.com/instacart-doing-things-that-dont-scale/)).
- Instacart set its own prices. Its 2013 FAQ said "Instacart prices are our own and vary from
  the store's price", and markups of 5% to 30% were reported
  ([Jarvis](https://www.alexanderjarvis.com/instacart-doing-things-that-dont-scale/);
  [Contrary](https://research.contrary.com/company/instacart1)).
- The founder reportedly thought signing a large chain early "was just going to be
  impossible". The first major partnership, with Whole Foods, came in 2014, once Instacart
  could show volume.
- Today it reports over 1,400 retail partners covering more than 85% of US grocery
  (August 2023).
  - Revenue comes "primarily from fees paid on each order by retail partners and customers",
    about 6.3% of order value in 2022, plus about 2.6% from advertising
    ([Contrary](https://research.contrary.com/company/instacart1)).
  - Advertising and other revenue passed US$1 billion in 2025
    ([10-K FY2025](https://www.sec.gov/Archives/edgar/data/1579091/000157909126000018/cart-20251231.htm)).

**How Instacart's pickers pay.** The shopper never uses their own money:
- Instacart issues a prepaid card and loads it with the estimated order total, plus a buffer,
  when the shopper accepts the order.
- The card works only for Instacart orders.
- Later this moved to phone payment through the card-issuing platform Marqeta
  ([Chain Store Age](https://chainstoreage.com/instacart-unveils-new-shopper-payment-customer-delivery-features);
  [Payments Dive](https://www.paymentsdive.com/ex/mpt/news/instacart-adds-apple-pay-google-pay-in-partnership-with-marqeta)).

Sources disagree on whether the card worked at non-partner stores.

**Cornershop (Chile and Mexico).**
- Personal shoppers picked and packed at participating supermarkets and delivered within an
  hour.
- Walmart agreed to buy it for US$225 million in 2018. Mexico's competition regulator,
  COFECE, blocked the deal: it would give Walmart power over a service that Walmart's rivals
  depended on.
- Uber then bought a majority stake (about US$450 million, 2019 to 2020)
  ([FoodNavigator](https://www.foodnavigator-latam.com/Article/2019/06/10/Walmart-acquisition-of-Cornershop-blocked-by-Mexican-authorities);
  [Contxto](https://www.contxto.com/en/chile/uber-to-purchase-majority-stake-in-cornershop/)).

**OneCart (South Africa).** In-house shoppers bought at partner retailers for a 5–7% service fee
(see the earlier launch investigation).

**Lesson.** Buying without an agreement is a way to show retailers you can bring them sales,
not a permanent model. The markup plus the service fee paid for the pickers. The conversion to
agreements is where the value came from. Retailers can also leave: the US chain Heinen's ended
its Instacart relationship in 2023 to fulfil its own orders
([Contrary](https://research.contrary.com/company/instacart1)).

## 2. Agreements: the retailer opts in

- **South Africa already has precedents.**
  - Spar extended its 2U delivery service to Uber Eats in July 2025, with about 275 stores
    listed ([BusinessTech](https://businesstech.co.za/news/?p=830815);
    [ITWeb](https://www.itweb.co.za/article/spar-to-expand-uber-eats-delivery-to-800-stores/nWJadMbNm58MbjO1)).
  - Pick n Pay sells more than 27,000 products at in-store prices through Mr D, with over
    500 stores listed
    ([TechCentral](https://techcentral.co.za/pick-n-pay-partners-with-takealot-in-online-shopping-push/211192/)).
  - Shoprite/Checkers runs its own Sixty60 instead.
- **Competition rules in South Africa.** The Competition Commission requires Uber Eats and
  Mr D to tell customers that they charge the seller a commission and that platform prices may
  differ from in-store prices
  ([TechCentral](https://techcentral.co.za/compcom-takes-aim-at-uber-eats-mr-d-food/229187/)).
  Trollie should expect the same disclosure duty once it earns retailer commissions.
- **Retailers' fees.** Commission rates for grocery partners in South Africa were not found.
  One US summary puts Instacart's take from retailers at 5–8%
  ([Sacra](https://sacra.com/research/instacart)).

**Lesson.** The pitch that works is incremental sales with no fulfilment cost to the retailer,
backed by data. Trollie's order history from the buy-and-mark-up phase is that data.

## 3. Owning stock: dark stores

- **Europe.** Getir, Gorillas, Flink and Jokr raised billions for 10-minute delivery from dark
  stores. Getir bought Gorillas in 2022, and most of these companies later withdrew from most
  markets. Recurring reasons in the analyses:
  - each order lost money;
  - riders cost too much for the basket sizes;
  - companies expanded to new countries before one worked.

  City rules also bit: France classed dark stores as warehouses, and Amsterdam and Rotterdam
  moved to ban new ones in city centres
  ([Euronews](https://www.euronews.com/next/2022/12/11/europe-food-delivery-analysis);
  [IBTimes](https://www.ibtimes.com/analysis-european-food-delivery-shapes-getirs-gorillas-buy-3645938);
  [IdeaProof](https://ideaproof.io/failure/getir-collapse)). The secondary sources conflict
  on details such as Flink's current status.
- **Africa.**
  - Jumia closed its food-delivery business in all markets by the end of 2023, citing
    "challenging unit economics and big losses"
    ([Business Daily](https://www.businessdailyafrica.com/bd/corporate/companies/jumia-to-close-down-food-delivery-business--4464844)).
  - Glovo left Ghana in 2024 but grew quick commerce elsewhere. Its view is that density is
    the whole business ([TechCabal](https://techcabal.com/2025/05/10/glovo-bets-on-nigeria/);
    [Nairametrics](https://nairametrics.com/2024/04/30/glovo-exits-ghanaian-market-amid-profitability-challenges/)).
- **Latin America.** Rappi's Turbo dark stores carry partner supermarkets' goods, bought or held
  on consignment. Partners include Chedraui's premium Selecto format in Mexico. In 2022 there
  were about 330 dark stores in more than 25 cities, and Turbo was 10% of Rappi orders where it
  operated ([Milenio](https://www.milenio.com/negocios/chedraui-selecto-se-une-a-rappi-en-entregas);
  [Forbes Chile](https://forbes.cl/negocios/2022-02-24/turbo-el-nuevo-servicio-de-rappi-crece-a-toda-velocidad-en-chile-y-la-region/);
  [InfoMoney](https://www.infomoney.com.br/?p=1621322)).
- **India.**
  - Foreign-owned marketplaces may not own inventory, so dark stores run by foreign-funded
    platforms had to hold independent sellers' goods.
  - Blinkit switched to owning its stock after its parent capped foreign shareholding in 2025.
    Swiggy's Instamart is following
    ([MediaNama](https://www.medianama.com/2026/10/223-blinkit-instamart-inventory-ownership/);
    [TLH](https://www.tlh.law/insights/analysing-quick-commerce-models-and-fdi-regulations-in-india)).
  - The same question as in South Africa (agent or seller) decides the structure there too.

**Lesson.** Dark stores pay only with dense, repeat demand in a small radius and a narrow range
of fast sellers. Rappi's version is the cheaper one: goods held on consignment from partners,
not bought outright. For Trollie, the first phase's order data should pick the location and the
range. Promise "same day" or "within two hours", not 10 minutes.

## 4. AI agents and retailers' checkouts

- **Agents shopping without the retailer's permission are contested.**
  - Amazon sued Perplexity over its Comet browser agent shopping on Amazon.
  - In March 2026 a federal judge blocked it from logged-in parts of Amazon. The judge
    reasoned that it used accounts "with the Amazon user's permission, but without
    authorization by Amazon"
    ([CNBC](https://www.cnbc.com/2026/03/10/amazon-wins-court-order-to-block-perplexitys-ai-shopping-agent.html);
    [GeekWire](https://www.geekwire.com/2026/judge-blocks-perplexitys-ai-bot-from-shopping-on-amazon-in-early-test-of-agentic-commerce/)).
  - In August 2026 the Ninth Circuit lifted that order. Because the agent acts only on the
    user's instruction, the user is the one accessing Amazon, so the US anti-hacking claim is
    unlikely to succeed. The case continues, and Amazon may seek a rehearing
    ([The Next Web](https://thenextweb.com/news/amazon-loses-perplexity-comet-ai-shopping-ruling);
    [Engadget](https://www.engadget.com/2230471/perplexity-has-successfully-overturned-amazon-injunction-on-its-ai-shopping-bot/)).
  - Amazon also alleged that Comet was disguised as an ordinary Chrome browser.
  - It is a US ruling on one law. It took a year of litigation and has no South African
    equivalent.
- **The other direction draws complaints too.** Amazon's own "Buy for Me" agent buys from
  independent brands' websites. Brands complained they were enrolled without consent and had
  to email Amazon to opt out
  ([Modern Retail](https://www.modernretail.co/technology/brands-are-upset-that-buy-for-me-is-featuring-their-products-on-amazon-without-permission/);
  [GeekWire](https://www.geekwire.com/2026/why-some-independent-brands-are-upset-with-amazons-new-buy-for-me-shopping-tool/)).
- **Checkout inside the AI chat (OpenAI).** OpenAI launched Instant Checkout in ChatGPT on the
  Agentic Commerce Protocol, with merchants opting in.
  - Uptake was thin: about 30 Shopify merchants, and Walmart reported conversion three times
    lower than sending users to its own site.
  - In March 2026 OpenAI deprioritised it; merchants now mostly use their own checkout.
  - Instacart was the exception: it launched checkout inside ChatGPT in December 2025
    ([CNBC](https://www.cnbc.com/2026/03/20/open-ai-agentic-shopping-etsy-shopify-walmart-amazon.html);
    [Retail Dive](https://retaildive.com/news/walmart-sparky-chatgpt-instant-checkout/815647/);
    [OpenAI](https://openai.com/index/instacart-partnership/)).
- **Google's alternative.** Google's Universal Commerce Protocol was built with Shopify, Etsy,
  Wayfair, Target and Walmart for checkout in its AI products.
- **Card networks.** Visa Intelligent Commerce and Mastercard Agent Pay (both launched 2025)
  give agents their own payment tokens, limited to a merchant and to what the owner allowed.
  Google's AP2 standardises the signed instruction ("mandate") behind them.
  - Sources disagree on dates and governance.
  - None of these is universally accepted by merchants yet
    ([Opascope](https://opascope.com/insights/ai-shopping-assistant-guide-2026-agentic-commerce-protocols/);
    [ATXP](https://atxp.ai/blog/mastercard-agent-pay-stripe-acp-visa-x402-comparison-2026/)).
- **Agent wallets.** Crossmint and others issue virtual cards for agents with spending caps,
  approved merchants, expiry dates and owner revocation. Skyfire says its spending limits are
  not public yet ([Crossmint](https://www.crossmint.com/products/agentic-cards);
  [Skyfire](https://docs.skyfire.xyz/docs/agent-spending-limits)).
  These are the same controls as Trollie's envelopes and grants.
- **A government-backed open network (India).** ONDC lets any buyer app search and order from
  any seller app's catalogue across 400+ cities. Many early buyer apps have paused
  ([ThePrint](https://theprint.in/economy/three-yrs-since-launch-govt-backed-e-commerce-network-ondc-is-a-tortoise-running-with-the-hares/2659194);
  [PDP Spectra](https://pdpspectra.com/blog/india-ondc-architecture-deep-dive)).
  It is the nearest working example of "all the stores in one" by agreement, not by scraping.

**Lesson.** The world is moving towards retailers opting in to agents: catalogue feeds, agent
payment tokens and signed mandates. Even the biggest AI companies found that merchants want to
keep their own checkout. Trollie's design (an agent proposes, the owner approves within a
scoped budget, and the merchant accepts) already matches where these standards are going.

## What this means for Trollie's sequence

| Trollie stage | Closest example abroad | What the evidence says to do |
|---|---|---|
| **1. Agents with their own wallet; buying through wholesale business accounts and human pickers** | Instacart 2012–14 (pickers and its own prices), OneCart, Rappi shoppers | The agent plans, prices and pays; a person only does the physical pick. The picker pays with a card loaded for that order only, as Instacart's prepaid card does, funded from the agent's envelope. Trollie is the seller at its own price. |
| **2. One dark store in Gauteng** | Rappi Turbo (partner stock on consignment), Blinkit | Only after stage 1 shows dense repeat demand in one area. Stock the top-selling lines from stage 1 data, ideally on consignment from wholesalers or brands. Promise same-day, not 10 minutes. Check zoning, the food Certificate of Acceptability and the business licence first. |
| **3. Agreements with retailers and providers** | Instacart from 2014, Uber Eats–Spar, Mr D–Pick n Pay | Pitch with stage 1 order data. Ask for a catalogue and price feed, an order API, and delivery to the customer's address. Expect to disclose commissions and price differences, as Uber Eats and Mr D must. |
| **Later: open agent rails** | Visa and Mastercard agent tokens, AP2 mandates, ONDC | Keep the merchant interface standard so a retailer with an agent checkout plugs in like any other merchant. |

**The holes in a human-picker model when agents are the customer, and how others close them:**

- **The agent can't walk into a shop.** The pick list is exact (product, size, quantity,
  substitution rule), so the picker carries out the order and makes no choices.
- **The till price differs from the quote.** The picker's card holds the quote plus a small
  buffer. Trollie absorbs any difference, as the founders decided, and records it per store.
- **Substitutions at the shelf.** The picker app applies the customer's saved rule. If the rule
  doesn't cover the case, it asks the customer within the agent's limits. A dearer substitute
  never charges the customer more.
- **Proof.** A photo of the receipt matched to the order, and proof of delivery. This is the
  same evidence the existing ledger and reconciliation expect from a merchant.

**The wallet still needs a licensed partner.** As in the earlier launch note, a balance the
customer can spend later is e-money, which only banks may issue in South Africa. Paying
retailers on the customer's behalf needs payments registration. Abroad, agent wallets sit on a
licensed card issuer or bank, and that is the route here too: a sponsor bank or licensed
provider holds the money, and Trollie's ledger, envelopes and grants control how it is spent.
Until then the wallet stays simulated, and real purchases are paid per order.

## Questions to take further

1. Which South African bank or licensed provider can issue order-limited virtual cards for
   pickers and hold agent wallet balances?
2. Do Shoprite Cash & Carry, Red Star or Makro Business allow resale to households and delivery
   to a third-party address?
3. What commission rates do Uber Eats and Mr D charge grocery partners in South Africa? These
   set the benchmark for Trollie's retailer pitch.
4. Where in Gauteng would stage 1 orders be dense enough for a dark store, and what does the
   municipality require?
