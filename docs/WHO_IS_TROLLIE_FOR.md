# Who is Trollie for, and why would they use it?

*Plain-language customer research · 29 October 2026 · Two Two Six Investments (Pty) Ltd*

Our other documents explain how Trollie works. This one asks the questions a shopper would ask: **what is it for me, and why should I use it instead of what I already do?**

It started with a voice note from a co-founder's partner, a mother who does the household shopping. We then checked their ideas against what South African shoppers actually do and against what the big retailers launched this year.

> **Read with:** [`reviews/CUSTOMER_VALUE_AND_PRODUCT_STRATEGY_REVIEW_2026-10-29.md`](reviews/CUSTOMER_VALUE_AND_PRODUCT_STRATEGY_REVIEW_2026-10-29.md), a separate review of the same question from the same day. Where the two differ, section 11 below sets out the differences and the decision each one needs.

---

## 1. The short answer

> **Trollie is your household's own shopping helper. It knows what your family buys, checks the specials at the shops near you, puts together the cheapest complete order, and only buys when you say yes.**

Three words carry the promise:

- **Your own.** Trollie works for the household, not for a shop. A Checkers or Pick n Pay assistant will always send you to Checkers or Pick n Pay.
- **Cheapest complete.** It's not about the cheapest single item. It's about the whole list arriving, at the lowest total, including delivery.
- **You say yes.** Nothing is bought until you approve the total, and the price you approve is the price you pay.

We don't lead with "AI". Most South Africans aren't familiar with the term (section 4), and the people who are already have Pixie and Penny.

---

## 1a. What we heard: the founder's summary of the voice note

After listening again, the founder summarised it like this:

1. **I can buy everything I need** in one app.
2. **It learns about me:** "You bought this 30 days ago, do you want it again?"
3. **Diet changes:** "I'm going on a diet." It finds substitutes, such as different creams and milks.
4. **Regular meals:** I cook certain meals on Sundays. It learns that, makes suggestions, gets the ingredients and reminds me what to do (for example, "marinate the lamb tonight").
5. **Save a meal and cook it one day:** scan a meal, get the recipe and the ingredients. "If you're feeling down and want a healthy soup, it can do it for you." The reference is **ReciMe** (recime.app), which the partner pays for every year. It saves recipes from TikTok, Instagram, Facebook, Pinterest, YouTube and photos of handwritten recipes, plans meals and builds aisle-sorted lists. It has over 15 million users; the free version allows 5 imports a week.
6. **Saves for me:** rewards, savings, and clear costs.
7. **Specials for the month and the week:** did Walmart, Shoprite or Pick n Pay run one? It works out **which shops in my area** have something special for me. *Example: Fourways Mall has several retailers under one roof.*
8. **Bundled weekly and monthly buys.** It hunts for sales and helps me save.
9. **Seasonal:** sales and suggestions that change with the seasons.
10. **No pop-ups, no annoying notifications.**

**The founders' conclusion:** make it a **fun app** where people can buy, plan and connect it to the AI agents they already use. In effect, **a personal agent for food and seasonal living.**

---

## 1b. The product: your personal food agent

One sentence: **"Trollie knows what your family eats, plans it with you, finds the best deals at the shops near you, and buys only when you say yes."**

| Pillar | What the customer sees | From the list above | Already built? |
|---|---|---|---|
| **Knows you** | Your usual order, your brands, "you usually run out of rice around now", favourites ("that wine you liked"), diet goals | 1, 2, 3 | Partly. The preference rules (locked / preferred / flexible brands) are built. Learning from purchase history is not |
| **Plans with you** | Sunday menu, saved recipes from TikTok/Instagram/photos, "cook this one day", a healthy soup on a bad day, Saturday reminders | 4, 5 | No. New module (ReciMe-style recipe saving plus a meal planner) |
| **Saves for you** | Specials this week and month at the shops near you, the cheapest complete order, mall bundles (several shops, one trip or delivery), seasonal deals, "you saved R__ this month" | 6, 7, 8, 9 | Partly. The engine that finds the cheapest complete basket across up to two shops (including promotions and delivery cost) is built. Area and mall discovery, a specials feed and a savings tracker are not |
| **Asks before buying** | One total, delivery included. Approve with a tap or fingerprint. Nothing changes without asking | (trust) | Yes. Quotes, approval and refusing double charges are built and tested |
| **Quiet by default** | Only "ready to approve", "on its way" and at most one helpful nudge a week | 10 | Design rule, not yet built |
| **Works with your agents** | Connect ChatGPT, Claude, Grok or Muse; they can plan and propose, but you approve | (founders) | Partly. The agent can propose but can never approve, and that is already enforced |

**What makes it "fun", not just useful:**
- a monthly savings card ("You saved R312 in October"), shareable;
- seasonal collections (winter soups, braai season, back-to-school, festive season);
- a family Sunday menu everyone can add to;
- streaks for "no wasted food this week";
- favourites and "tried it, loved it" ratings.

Keep it light: no games that push people to spend.

**Honest constraint:** the "specials at Walmart vs Shoprite vs Pick n Pay near me" pillar needs **price and specials data from each retailer**. Without agreements, the only lawful sources are each retailer's public catalogues and flyers, entered or partnered for. We should not scrape retailer apps (see `LAUNCH_STRUCTURE_INVESTIGATION.md`). Getting this data is the first business task, before it becomes an engineering one.

---

## 2. What the partner asked for, and who already does it

The partner's voice note (7 min 52 s) listed what would make them use the app. In 2026 the three big grocers each launched their own AI assistant:

- Checkers' **Pixie** (April, upgraded in August);
- Pick n Pay's **Penny** (July);
- Woolworths' **W.CHEF / My Woolies Chef**: announced in July, in a limited beta for selected loyalty members since about October, with a wider rollout planned for early 2027.

So we checked each idea against what already exists.

| What they asked for | In their words | Who already does it | What only Trollie can add |
|---|---|---|---|
| Everything in one app | "I can buy everything I need on this app" | Each retailer, for its own shelves only. OneCart lets you shop several stores but leaves the comparing to you | One list across more than one shop |
| Reminders when things run out | "You bought this about 30 days ago, it should be done. Shall I order it again?" | Pixie (restock suggestions), Penny (reload previous baskets) | Remembers across shops, not inside one loyalty card |
| Lifestyle and diet changes | "I'm going on a diet… you always buy full cream milk, we can start buying fat-free milk" | Penny (dietary preferences in meal plans) | Suggests swaps, but **never swaps without asking** |
| Meal plans and recipes | "This Sunday I want to cook lamb… remind me on Saturday to marinate" | Penny (meal plans within a budget), W.CHEF (beta), Pixie (Jamie Oliver recipes) | The meal plan uses whichever shop has the ingredients cheapest |
| Save a meal you saw | "Scan a meal… I want to cook this one day" | Pixie (photo of a handwritten recipe), Penny (photos) | Same feature, plus stores compared |
| Savings and rewards | "As a mom and a wife, we always want to save somewhere somehow" | Xtra Savings, Smart Shopper, WRewards, each for its own store only | **Shows how much you saved compared with one shop**, honestly, on every order |
| Specials across stores | "Woolies had the rice at R68 and Checkers still had R78" | Nobody does this and buys for you. Grocify compares prices but doesn't order | This is the core of Trollie |
| Bundle so you don't pay delivery on one item | "I'm not going to pay delivery on one item" | Partly: R35 per mall at OneCart | Puts the order together across at most two shops, and adds a second shop only when it saves more than it costs |
| Seasonal ideas | "Winter soups… summer ice, cooler boxes" | Retailer promotions | Low priority; easy to add later |
| Don't nag me | "I muted Shein and Temu… one item going out of stock won't make me buy 40 items" | Most apps get this wrong | Few messages, only useful ones (section 7) |
| Remember what I liked | "That wine I bought, I really liked it… show me similar ones" | Retailer purchase history | Favourites that work across shops |

**What this tells us:**

- Most of the single-shop ideas (reminders, recipes, meal plans, photo lists) **were launched by Shoprite, Pick n Pay and Woolworths this year.** On their own they won't make anyone switch.
- What **no one** does is the partner's rice example: *check the specials at the shops near me, put my usual order together where it's cheapest, and don't make me drive around.*

**Walmart.** The partner mentioned Walmart and Woolies being in one mall at Fourways. Walmart opened its first South African stores in **Clearwater Mall (November 2025)** and **Fourways Mall (28 November 2025)**, and a third in Boksburg in **March 2026**. Massmart plans 21 more. Walmart sells on "Every Day Low Prices" and runs its own app with 60-minute delivery. Price comparisons find it cheapest on most staples, *except when Checkers or Pick n Pay run a special.* That exception is exactly the gap Trollie fills.

---

## 3. What South African shoppers actually do

These figures come from published research; sources are in section 10.

**They already shop around, by hand.**
- The average household now splits its big monthly shop across **about four stores, up from one or two in 2022** (Roots, 25,000 adults).
- 69% check printed flyers for specials, and 95% of shoppers look for deals.
- **52% say the main thing they want AI to do is find the lowest price across retailers. Only 8% want automatic reordering** (iqbusiness, April 2026).

That last finding matters. The partner's "remind me to reorder" idea is nice to have, but **"find me the cheapest across shops" is what people actually ask for.**

**Food takes a large part of the money.**
- Poor households spend about **R41 of every R100 on food** (Competition Commission, September 2026).
- 42% of grocery shoppers live in households earning under R5,000 a month.
- The household food basket cost **R5,530** in July 2026.

**Getting to the shops costs money and time.**
- Taxi fares rose about 13% this year.
- Low-income Gauteng residents spend about 29% of their income on transport.
- 40% of people who use delivery apps say they do it partly to save on transport or to avoid impulse buying in the store.

**The planning falls on mothers.**
- Mothers carry about **71–73% of the household "mental load"**: remembering what's run out, planning meals, writing the list (Bath/Melbourne 2024; UCLA 2024).
- We found no South African study on this, but nothing suggests it is different here.

**Loyalty cards are everywhere.**
- Shoppers belong to about five loyalty programmes and use about four.
- Xtra Savings returned R18.3bn to shoppers in the year to June 2026.
- Losing points is a real objection to any app that buys for you.

---

## 4. What shoppers think about AI buying for them

- **Most people aren't "AI people".** In a broad 2025 study, more than 70% of South Africans had little or no familiarity with the term "AI". Among grocery shoppers, **only 1 in 5 hope to use AI for groceries next year, and only 10% of people who don't already use AI** (Trade Intelligence, April 2026).
- **People want AI to find deals and ask before paying.** 41% want help staying within a budget, and 58% are comfortable with AI comparing prices. Only 6–9% would let AI buy without checking first. Trust drops sharply at the moment of payment.
- **Their fears:** buying the wrong item (42%), overspending (40%), fraud (52%), and a feeling that shopping assistants are built to make you spend more (36%).
- **The controls they ask for:** a spending limit, an instant off switch, easy cancellation, and approval before buying.

**What this means:** Trollie's "you approve every order" design is exactly what people say they want. The message should be **"it finds the deal, you say yes"**, not "an AI agent shops for you".

---

## 5. The selling point, person by person

The same app, described the way each person would hear it.

### The mother who does the monthly shop on payday (Soweto, Tembisa, Mamelodi)
- **Her month:** checks the Checkers, Shoprite and Pick n Pay flyers, takes two taxis to two shops on payday weekend, and carries the bags home. Food is close to half the budget.
- **The promise:** *"Send a voice note of your list, in your language. Trollie checks the specials at the shops near you and shows one total, delivery included. Say yes, and it comes to your door. No taxi, no queue, no carrying."*
- **What would make her say no:** a fee bigger than the taxi fare she saves, or anything that looks like a hidden markup.

### The busy working mother (Midrand, Centurion, Durban North)
- **Her week:** already uses Sixty60 or asap!, but is still the one who remembers that the rice is finished, plans Sunday lunch and writes the list.
- **The promise:** *"Stop being the family's memory. Trollie keeps the household list, reminds you before things run out, plans Sunday's lamb and adds the ingredients, and checks two shops' specials for you. You approve once a week."*
- **What would make her say no:** notifications. She will mute us the way she muted Shein and Temu.

### The father
- **His situation:** often handed the list, doesn't know which brands the family uses, and gets it "wrong".
- **The promise:** *"The family's usual order, already set up with the right brands. Add what you need, approve, done. No phone call from the shop to ask which cheese."*
- **Also for him:** a monthly grocery budget he can see and stick to.

### The person who doesn't know or trust AI (older shoppers, many low-income households)
- **Never say "AI".** Say: *"Send a voice note, get a price, say yes."*
- The approval step is the trust: *"Nothing is bought until you say yes, and the price you see is the price you pay."*
- **For a gogo or grandfather on SASSA:** a family member can add money with a limit, so the pensioner doesn't have to queue on grant day.

### The AI enthusiast ("geek")
- **His or her world:** already uses ChatGPT, Claude or Grok, and has probably tried Pixie or Penny.
- **The promise:** *"An agent that works for you, not for one shop. It compares more than one retailer, follows your rules (these brands always, those never), never goes over your budget, and has a spending limit you can switch off instantly. Connect your own AI to it."*
- **What would make them say no:** if Trollie is just another "AI builds a basket" inside one store. Pixie already does that.

### The grocery stokvel (later)
- **The promise:** *"Everyone sees the quote before anything is bought, and each member's share is delivered to their own door."*
- This comes later, but it is the clearest trust story we have.

---

## 6. The "Knorr soup" question, and why "you pay a premium" is the wrong answer

The partner asked: *"You say you buy from different shops, so what happens if I want Knorr soup?"* The answer given was *"you'll be charged a premium."* That answer would lose the customer, for three reasons:

1. In South Africa, **shop prices plus one visible fee is the norm.** Sixty60, asap!, Mr D and OneCart all advertise "in-store prices" with a flat R35–R45 delivery fee.
2. Instacart in the US marked up item prices and showed different shoppers different prices. It paid **$60 million to settle with the US regulator (FTC)** in December 2025 and stopped its price tests in January 2026.
3. A premium wipes out the saving, and the saving is the reason to use Trollie in the first place.

**The right answer:**

> *"If you always want Knorr, tell Trollie once and it will always get Knorr. It goes to whichever shop has it cheapest. If that means a second shop, it tells you what the extra delivery costs, and you choose. It never swaps your brand without asking. You pay the shop's price, plus one clear Trollie fee shown before you say yes."*

This is already how the engine works: the customer can lock a brand as a must-have, and a second shop is added only when it saves more than it costs. The **business model** must match it: no markup on items; a fee or subscription that is always shown, and always smaller than the saving we found.

**Rule for every order:** if the saving we found is smaller than our fee, say so before the customer approves.

---

## 7. Promises we can make, and things we never do

**We promise:**
1. **One list, the cheapest complete order across the shops near you, delivery included.**
2. **You see the full total before anything is bought. Nothing is bought until you say yes.**
3. **Your brands stay your brands**, whichever shop has them.
4. **The specials from two shops without driving to both.**
5. **We tell you straight if we can't get everything.** No surprise swaps at the door.
6. **Your saving shown honestly on every order**, compared with buying it all at one shop.
7. **Shop prices, one clear fee, the same price for everyone.**
8. **A monthly grocery budget your helper can't go over, with an off switch.**

**We never:**
- mark up shop prices or charge different people different prices;
- swap a brand, add items or upgrade without asking;
- send marketing notifications by default;
- use "money saved" figures we can't show the working for.

**Notifications.** Retail apps send about 27–34 pushes per user per month, and "too many" and "not relevant" are the top two reasons people switch them off. Trollie should send only:
- "your order is ready to approve";
- "it's arriving";
- at most one "you usually run out of rice around now" nudge a week, which the customer can switch off.

---

## 8. Hard questions a shopper will ask

| They ask | We answer |
|---|---|
| "Why pay you when Sixty60 delivers in an hour for R35?" | "Use Sixty60 for a quick top-up. Use Trollie for the big shop, where checking two shops' specials saves more than our fee. If it doesn't, we tell you." |
| "Pick n Pay's Penny already plans meals on a budget." | "Penny's budget stops at Pick n Pay. Ours checks two shops." |
| "Two deliveries means double the hassle." | "We only add a second shop when it saves you more than the extra delivery, and you see that before you say yes." |
| "What if you buy the wrong thing or spend more?" | "You approve the exact list and total. Any change means a new approval. Refunds come back to you." |
| "Do you mark up prices?" | "No. Shop price plus one fee you can see." |
| "Will I lose my Xtra Savings or Smart Shopper points?" | **Open question.** We need to link loyalty cards where retailers allow it, and show loyalty prices honestly. |
| "OneCart already does more than one shop." | "OneCart makes you do the comparing. Trollie does it for you, remembers your family's preferences and asks before buying." (OneCart has only about 280 App Store ratings after years, so "many shops in one app" alone doesn't win.) |
| "Is it safe to let an AI pay?" | "The AI never pays. You approve, with a spending limit you set and can switch off." |

---

## 9. What this means for what we build, and for the Shoprite pitch

**What the research says the customer wants most:**

1. **Compare across shops and buy the cheapest complete order.** This is the thing nobody else does, and it is what 52% say they want AI for.
2. **Approve before buying, with one fixed total.** Already built.
3. **A household list that remembers our brands and our usual order.** Partly built (the preference rules).
4. **An honest "you saved" figure on every order.** To build.
5. **Voice notes in home languages.** Planned; no retailer assistant does South African languages well yet.
6. **Meal plans, recipes (ReciMe-style saving), reminders, favourites and seasons.** These make Trollie a *personal food agent*, not just a checkout, and they are what makes the app fun to open every week. Retailers offer them inside their own stores. Ours connect to cross-shop savings: *"this week's Sunday lamb is cheapest at Walmart, the veg at Checkers, both in Fourways Mall."* Build them on top of 1–5, not instead of them.
7. **Few, useful notifications.** Design rule from day one.

**The difficult part, which the founders need to decide.** The partner's best idea (Woolies rice against Checkers rice) only works if Trollie can buy from **more than one retail group**. The ShopriteX pilot is **Shoprite Group only**, and Shoprite already has Pixie. So in the pilot, the consumer story is thinner:

- **Within the Shoprite Group we can still offer:**
  - home-language voice;
  - a household that approves every order;
  - comparing Checkers, Shoprite and Usave prices;
  - Xtra Savings specials;
  - budgets and Money Market funding;
  - a door for outside AI agents.
- **We cannot offer** "cheaper than going to Pick n Pay or Walmart". A Shoprite partner will not want that either.

There are two honest ways forward. They can run at the same time, but they shouldn't be mixed up in the same pitch:

| | A. The household's own shopper | B. Shoprite's voice-and-agent channel |
|---|---|---|
| Who it's for | Households that want the best deal across shops | Shoprite customers who would rather speak (in isiZulu or Setswana) or use their own AI than tap through an app |
| Selling point to a mother | "The cheapest complete order across shops, without driving around" | "Send a voice note in your language, approve, done" |
| Needs | More than one retail group (Shoprite, Pick n Pay, Walmart, Woolworths) | Shoprite's agreement |
| Risk | No retailer agreements yet; Walmart and Pick n Pay are rivals of the pilot partner | Thin difference from Pixie unless voice, languages and outside agents are really better |
| Fits the ShopriteX proposal? | No. Keep it out of that pitch | Yes. This is what the proposal already offers |

**Our recommendation:** pitch **B** to ShopriteX, because that is what the proposal already says. Keep **A** as Trollie's long-term consumer promise, and test it with real households before we spend more on the engine:

- run 10–15 short interviews using the personas in section 5;
- do 5 "paper prototype" price-comparison orders;
- ask the partner to do one month's shop through a WhatsApp mock-up.

The question to answer: **would they pay a fee for the saving, and how much?**

---

## 10. Sources

**Retailer AI assistants and competitors**
- Pixie: Bizcommunity, April 2026 and 13 August 2026; Sowetan, 14 July 2026.
- Penny: IOL Business Report, 2 July 2026; BusinessDay, 3 July 2026.
- W.CHEF / My Woolies Chef: eNCA, 13 July 2026; Bizcommunity, "Woolworths brings AI food assistant W.Chef into live customer testing"; Woolworths Holdings, 8 October 2026.
- Walmart South Africa:
  - BusinessTech, 27 February 2026 (businesstech.co.za/news/business/852487);
  - Massmart newsroom, November 2025 and March 2026;
  - Daily Investor price comparison (dailyinvestor.com/retail/115979);
  - BusinessDay, 20 November 2025, "Walmart starts the clock in delivery war with Shoprite".
- OneCart: TechCentral, 19 September 2023; App Store listing.
- Grocify: Daily Dispatch, 30 January 2026.
- Instacart:
  - Groundwork Collaborative / Consumer Reports, December 2025;
  - Supermarket News, FTC $60m settlement, December 2025;
  - Instacart newsroom, February 2026.
- Ocado Price Promise: ocado.com; Picnic: picnic.app.

**Shopper behaviour**
- Roots 2025 survey: Bizcommunity, 7 January 2026.
- Trade Intelligence, SA Grocery Shopper Report: 15 and 21 April 2026.
- iqbusiness AfricanPulse: Bizcommunity, 8 April 2026.
- Competition Commission Cost of Living Report, September 2026 (via AllAfrica).
- PMBEJD Household Affordability Index, July 2026 (via Business Report).
- Stats SA General Household Survey 2025 (via IOL, 26 May 2026).
- Shoprite Group results and newsroom, FY2025 and FY2026.
- Pick n Pay Smart Shopper year in review: Business Report, December 2025.
- Township CX Report 2025: Bizcommunity, 17 September 2025.
- NASASA stokvel figures: EWN, 14 August 2025.
- Eighty20/MAPS on language and grocery shopping: TimesLIVE, 2 October 2024.

**Mental load**
- Univ. of Bath / Melbourne, *Journal of Marriage & Family*, December 2024.
- Saxbe & Aviv, *Archives of Women's Mental Health*, July 2024.

**AI trust and agent shopping**
- Beyond the Hype (HSRC-linked), 2025.
- KPMG / University of Melbourne SA snapshot, May 2025.
- Google/Ipsos via TechCentral, 30 January 2026.
- Klaviyo, October 2025.
- Visa consumer survey.
- Checkout.com, June 2026.
- Accenture 2026.
- Riskified Q1 2026.
- Global Payments 2026.

**Notifications**
- Airship 2025 Push Notification Benchmarks.
- CleverTap, January 2025.

*Not verified, or no South African data found:* a South African mental-load study; how many grocery stokvels there are; Sixty60's total user count; ReciMe's South African user numbers and price (the partner pays yearly; recime.app lists only the free limit of 5 imports a week); how often people want notifications in South Africa.

---

## 11. Reconciling with the separate review (29 October 2026)

The separate review reaches the same conclusion as this document: the product is explained from the builder's side, not the household's. Most single-shop features already exist at Checkers, Pick n Pay and Woolworths. A Shoprite-only pilot cannot prove buying across retail groups. Wallets and connected agents stay in the product, but behind the ordinary shopping journey.

**Where the review is stronger, and we adopt it:**

1. **Lead promise.** The review leads with *"less work getting the household shop done, with an honest delivered total"*, and treats savings as something we show when they are real. This document led with "cheapest complete". The review's worked example shows why its version is safer: a R100 saving on the goods becomes R5 once the second delivery and our fee are added. **Proposed:** lead with less work and the honest total; show the saving on every order, including when there is none. *Founder decision.*
2. **The pilot can't prove the meal promise.** The partner's stories (lamb, milk, cheese, Sunday meals) need fresh food. The pilot starts with packaged shelf goods (pantry items). Either describe the pilot honestly as *pantry restocking*, or plan a later mixed-basket trial with fresh food. Don't use a dry-goods order as proof of the meal promise.
3. **Liking an item is not permission to buy it.** Keep four steps separate: *I like this* → *suggest it next shop* → *include it every fortnight (as a draft)* → *buy it within these limits (a separately approved standing instruction)*. This maps directly onto the existing rule that a purchase needs either your approval of the quote or a mandate you signed with your passkey.
4. **Reminders should say how sure they are.** Use "you confirmed you have it", "you may be running low" and "we don't know". Start with a rhythm the customer sets, not a guess.
5. **A percentage fee works against a savings promise.** Test a fixed fee per order, a capped percentage and an optional subscription. Never count an existing Xtra Savings Plus subscription as a saving.
6. **Diet and food-safety limits.** Make swaps only for a reason the customer states (for example, lower salt), backed by product data. No medical claims. Preparation reminders must use checked food-safety guidance.
7. **A bigger, mixed test group.** About 24 interviews across household organisers, fitness and meal-plan shoppers, convenience shoppers and agent users. Include people who are happy with one retailer and people who dislike the idea.

**What this document adds that the review doesn't have:**
- Walmart's South African entry.
- Roots' "about four stores per monthly shop".
- iqbusiness: 52% want AI to find the lowest price across retailers, and only 8% want automatic reordering.
- Instacart's $60m FTC settlement as the case against markups.
- The founders' ReciMe reference and the mall-bundle idea.

**Correction made after the review:** Woolworths' assistant is in **limited beta**, not generally available. Section 2 has been updated.

**Customer requirements CV-01 to CV-16** (review section 16) are proposed for founder sign-off. Once agreed, they belong in `DECISIONS.md`, next to the engineering decisions. Until then they are proposals; they don't change the build.
