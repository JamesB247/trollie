# Trollie as a food lifestyle app: investigation

*31 October 2026 · investigation for a founder decision; nothing here is adopted yet*

## The idea being tested

Trollie stops buying and delivering groceries. Instead it becomes the household's **food companion**:
- **Recipes:** photograph a dish to find out what it is and how to make it, and save recipes from TikTok, Instagram or a photo.
- **Planning:** plan meals ("every Sunday, lamb"), get reminders ("buy this", "marinate tonight"), swap ingredients for a diet, find seasonal ideas and keep favourites.
- **Finding and buying:** see where the items are at the shops near you, then **buy them yourself on the retailer's own app**, with your own account and payment method.
- **Later:** retailer integrations, and optionally paying through the Trollie wallet.

This comes straight from the partner's voice note. It also removes the conflict with Shoprite: Trollie sends retailers customers instead of competing to fulfil orders.

---

## 1. The verdict in one paragraph

**The direction is right, but the app alone isn't a business.** Dropping payments and delivery removes the hardest legal and operational risks:
- no registration as a third-party payment provider;
- no couriers;
- no food-safety liability for goods we sell.

But the three core features are now free elsewhere. Pixie, Penny, My Woolies Chef, ChatGPT and Gemini all turn photos into recipes and recipes into a basket. Recipe apps also keep very few users (about 3–4% are still using them after 30 days), and no South African grocer pays referral fees today. The pivot works if Trollie becomes two things at once:
1. **The household's weekly food habit.** Planning, reminders and lists across shops, in South African terms.
2. **A demand channel that brands and retailers pay for.** Clearly labelled sponsored recipes now; basket-handoff and retail-media deals later.

That's how the survivors overseas make money: SideChef and Jow sell to retailers and brands, and Instacart pays recipe partners. Consumer subscriptions alone are shrinking even at Cookpad's scale.

---

## 2. What the partner asked for, and what the market already has

| Feature | Who already offers it | Trollie's angle |
|---|---|---|
| Photo of a dish → recipe | ChatGPT, Gemini, Samsung Food (paid), SideChef; Pixie and Penny accept photos | A commodity. Do it honestly: "looks like X, here is a typical recipe". Never claim exact ingredients or allergens: AI gets about half the ingredients wrong from a photo |
| Save recipes from social media | ReciMe (800k+ users, about US$40 a year), Pestle, Honeydew, Flavorish | South African import with a generous free tier and household sharing; private by default, linked back to the source |
| Meal plans and Sunday rituals | Penny (budget meal plans), My Woolies Chef (beta), Mealime, Plan to Eat | **South African rituals:** Sunday lunch, braai, month-end, school lunches, seasons. Reminders tied to cooking ("defrost tonight"), not just the cart |
| "You bought this 30 days ago" | Pixie (restock suggestions) | Across shops, and it says how sure it is: "may be running low" |
| Diet swaps | Penny (dietary preferences) | Only for a reason the user gives (for example, lower salt), backed by product label data; no health claims |
| Find the items, compare shops | **Nobody does this across retailers and hands off to buy** | **The real gap**, but it needs price data (section 4) |
| Buy on the retailer's app | Each retailer, inside its own app only | Hand off to the user's own account (section 3) |
| No annoying notifications | Most apps get this wrong | Quiet by default; one weekly plan-and-list message |

South African signals:
- About 80% of people braai regularly, and recipe searches are weekly habits.
- But in one Tshwane study, **64% of households never use recipes** and only 37% plan meals.

The lead feature should therefore be **the list and the plan**, with recipes in support. Recipes alone won't carry it.

---

## 3. Handing off to the retailer: what works today

We checked each retailer's site directly on 31 October 2026, including whether its links open its app.

| Retailer | Best hand-off today | Pre-filled basket? | Affiliate programme? |
|---|---|---|---|
| Checkers Sixty60 | Product-page link (pages show the barcode) | No | No |
| Pick n Pay (asap! inside the main app) | Product or search link; **opens the app** | No | No |
| Woolworths (Dash inside the main app) | Product link; opens the app | No | No |
| Walmart SA | Any link opens the app | No | No |
| Makro | Product or search link; opens the app | No | No |
| Takealot, Clicks | Product link; opens the app | No | No (Takealot closed its programme) |
| Spar2U, OneCart | Nothing reliable | No | No |

**What this means:**
- **Today the user has to add items one by one** after tapping through. That's real friction. A basket that opens pre-filled needs a partnership; Instacart and Kroger offer this overseas, but no South African grocer does.
- **Pick n Pay's terms forbid even "linking to"** its app or site without written consent (asap! terms, clause 2.16.1.4), and forbid scraping (2.16.1.5). Ask before launch. Treat Checkers' terms the same way; its site blocks automated access.
- **No grocer affiliate income exists in South Africa.** Overseas grocery affiliate rates are about 1% (Amazon, Walmart US).

---

## 4. The comparison problem: where prices come from

"Find it cheapest near me" is the one thing retailers' own assistants will never do, and it's the feature that most needs data.

| Source | Legal? | Usable? |
|---|---|---|
| Scraping retailer sites or apps | **No.** Barred by Pick n Pay's terms; Checkers blocks automated access | Don't do it (consistent with our earlier decision) |
| Retailer price feeds (as PriceCheck receives from merchants) | Yes, with agreement | Only with partnerships: this becomes **the main ask** |
| GS1 South Africa / PDC.za product catalogue (Shoprite, Pick n Pay and SPAR suppliers publish there) | Yes, with a licence | Product facts and barcodes, not live prices |
| **Users' own till slips** (scan your receipt) | Yes, with the user's consent; it is their data | Real prices paid, but patchy and delayed; SnapnSave already uses till slips for cashback |
| Retailer flyers and catalogues | Use needs checking (copyright) | Weekly specials only |

Recommendation:
- **Launch with product facts** (GS1/PDC.za or brand data) and **"your last price"** from scanned till slips.
- **Ask retailers for feeds.** Show live prices only where a feed or written permission exists.
- **Never present a price as current if it isn't.** Say "seen on your slip on 12 Oct".

---

## 5. How it could make money

These are rough year-one estimates from the research, not forecasts.

| Stream | Likelihood | Rough size, year 1 |
|---|---|---|
| **Sponsored recipes and collections from food brands** (e.g. Knorr, Robertsons, Rajah), clearly labelled #Sponsored | **Best bet**: brands already pay South African creators about R4,000–R7,000 a post | **R0.1m–R2m** (5–15 deals) |
| Affiliate fees from non-grocers (Faithful to Nature up to 15%, kitchenware) | Low | R0.1m–R0.3m |
| Grocer referral fees | Unlikely without a signed deal | R0 until negotiated; 1–2% of attributed baskets after |
| **Off-site inventory for Shoprite's Rainmaker Media** (sponsored recipes sold by Shoprite, revenue shared) | Possible: Shoprite's media business is heading past **R1bn a year** | Deal-dependent |
| Consumer subscription (premium: unlimited imports, household plans) | Possible, but South Africans pay little; Samsung Food charges R1,100 a year | Small at first |
| Selling data | **No**: POPIA risk and trust | R0 |

Rules that keep this honest:
- sponsored content is always labelled (ARB code, Consumer Protection Act s41);
- paid placement never changes a "cheapest" answer;
- no health claims that a food treats or prevents a disease (R146).

---

## 6. Risks

| Risk | What we found | Handling |
|---|---|---|
| Features are commodities | Retailer assistants and general AI already do photo-to-recipe and recipe-to-basket, for free | Compete on neutrality across shops, South African rituals, household planning and honesty, not on AI |
| Low retention | Food and drink apps keep about 3–4% of users after 30 days | Build around a weekly habit (the plan, the list, the Sunday reminder). Measure weekly active planners, not downloads |
| Retailers can refuse links or data | Pick n Pay's terms require consent even to link | Ask first; show only permitted links; product search as the fallback |
| Food AI errors | Photos give about half the ingredients wrong; one supermarket's bot once suggested a recipe that makes chlorine gas | Show "looks like"; recipes checked against an ingredient list; allergen warnings; never "allergen-safe" |
| Health data (POPIA) | Allergies, medical diets and pregnancy are special personal information | Optional, explicit consent, stored separately; strip photo location data; no training on user photos without opt-in |
| Copyright | Ingredient lists are facts; text, photos and video are protected; South Africa's fair-use reform isn't law yet | Import facts, rewrite steps, link to the source, private by default, takedown process |
| Revenue depends on companies that may also compete | Retailers run their own assistants and media | Make Trollie the *outside* channel they can't build themselves: households that plan before they shop |

---

## 7. What happens to what we've built

| Built | Role in the new model |
|---|---|
| Products and barcode matching (GTIN first) | **Core**: matching recipe ingredients and list items to real products |
| Preferences (locked / preferred / flexible) | **Core**: the household's brands and swaps |
| Optimiser across stores | **Core**: "this list is cheapest at X" wherever we have permitted prices |
| Quotes, approval with fingerprint or face, orders, ledger, refunds, wallet | **Later**: switched on when a retailer lets us check out for the user, or when wallet payments are allowed. Kept, tested, not deleted |
| Positioning (I-048) | **Needs updating.** "Nothing bought until you say yes" assumes Trollie buys. See decision 2 |
| ShopriteX proposal v4.0 | **Needs rewriting:** from "approved order route" to "deep links, basket hand-off, price feed, attribution and Rainmaker revenue share" |
| CLAUDE.md sprint scope | **Needs changing:** it currently rules out any language-model call and focuses on the payment engine. Photo-to-recipe and voice need one, kept *out of anything to do with money* |

---

## 8. A phased plan, if adopted

**Phase 1: plan and find (about 3 months, no retailer needed)**
- Household list and plan:
  - the "usual" list;
  - the Sunday plan;
  - South African recipe collections (braai, Sunday lunch, month-end, seasons).
- Recipe saving from links and photos, honestly labelled.
- Reminders: quiet by default, one weekly message.
- "Find it": product search links to each retailer, only where permitted.
- Till-slip scanning for "your last price".
- Test with 50–100 households. Measure weekly active planners, items found, and hand-off taps.

**Phase 2: partners (in parallel)**
- **Shoprite / ShopriteX ask:**
  1. written permission to link to product and search pages;
  2. a **basket hand-off link** that opens the user's Sixty60 basket pre-filled;
  3. a licensed product, price and availability feed;
  4. a partner ID and monthly attribution report;
  5. a free 90-day pilot, then either a fee per new customer, or **sponsored recipes sold through Rainmaker Media with a revenue share** (the most likely yes).
- The same ask to Pick n Pay, Woolworths and Walmart SA (non-exclusive).
- First brand sponsors for labelled recipe collections.

**Phase 3: buy inside Trollie (only when a retailer allows it)**
- Switch on the approval engine and, if permitted, the wallet: the user approves once, and the retailer's checkout runs on their own account.

---

## 9. Decisions for the founders

1. **Adopt the pivot?** Recommended: yes, as "plan and find first, buy later", keeping the engine for Phase 3.
2. **Supporting line.** "The whole shop, one honest total, nothing bought until you say yes" no longer fits Phases 1–2. Options:
   - *"Plan it, find it, buy it where you like."*
   - *"Your food, planned. Your shops, compared."*
   - Keep the slogan "Your list. Taken care of." either way.
3. **Rewrite the ShopriteX proposal** around the Phase 2 ask.
4. **Change the sprint scope in CLAUDE.md** to the Phase 1 build: consumer features and an AI layer kept outside the money path.

---

## Sources (main)

**Food lifestyle market**
- ReciMe: SmartCompany, 2023 and July 2024; ReciMe help centre on copyright.
- Samsung Food: Stuff SA, 2024–25.
- Yummly shutdown: The Spoon; Kitchen Stories sale: Horizont, October 2025.
- Cookpad results: Quartr, 2025–26; BuzzFeed going-concern warning: RNZ, 13 March 2026.
- Jow: TechCrunch, 2019 and 2021; Grocery Dive.
- Retention benchmarks: Upland/Localytics, UXCam, Adjust.
- South African demand: BusinessDay, 23 September 2025 (braai); Ncube et al., *Health SA Gesondheid*, 19 December 2024 (Tshwane meal planning).
- Food AI accuracy: arXiv 2511.08215 and 2409.18459; *Nutrients*, November 2025; *Proceedings of the Nutrition Society*, 2024; The Register, 11 August 2023 (Pak'nSave).

**Retailer assistants**
- Pixie: Cape Argus, 9 April 2026; Stuff, 13 August 2026.
- Penny: Business Report, 2 July 2026.
- My Woolies Chef: The Citizen, 13 July 2026.
- TechCentral, 12 August 2026.

**Hand-off and data**
- Direct checks of retailer link and robots files on 31 October 2026 (Pick n Pay, Woolworths, Walmart SA, Makro, Takealot, Clicks).
- Pick n Pay asap! terms and conditions; Instacart Developer Platform documentation; Amazon add-to-cart form; Kroger API.
- PriceCheck merchant support; Grocify: Daily Dispatch, 30 January 2026; GS1 South Africa / PDC.za: ITWeb.

**Money and rules**
- Shoprite media business: Moneyweb / The Citizen, 15 July 2026; Pick n Pay retail media: Osmos.
- SA influencer rates: Cape Argus, 26 November 2024.
- ARB social media code; IAB SA disclosure toolkit 2026; Consumer Protection Act s29 and s41.
- R146 labelling regulations; POPIA special personal information guidance note (28 June 2021).
- US Copyright Office Circular 33; Constitutional Court copyright ruling ([2026] ZACC 26).

Full source lists with URLs are in this session's two research briefs from 31 October 2026.
