"""Synthetic shopper personas. Every name and household is fictional.

Archetype counts are drawn at random for each run (within bounds), so no two runs have the
same crowd. The random source is seeded from OS entropy and the seed is printed, so an
interesting run can be replayed with `--seed` (timing still varies between replays).
"""

import random
from dataclasses import dataclass, field

from app.simulators.market import MARKET_ZONES

FIRST = [
    "Thandi", "Sipho", "Lerato", "Pieter", "Ayesha", "Bongani", "Nomsa", "Johan", "Zanele",
    "Kagiso", "Fatima", "Themba", "Annelie", "Lwazi", "Naledi", "Ruan", "Precious", "Mandla",
    "Keabetswe", "Yusuf", "Lindiwe", "Charlene", "Tshepo", "Busisiwe", "Mpho", "Riaan",
    "Nandi", "Sibusiso", "Refilwe", "Ashwin", "Zodwa", "Kgomotso", "Andile", "Megan", "Vusi",
    "Palesa", "Hendrik", "Nokuthula", "Imran", "Dineo",
]  # fmt: skip
LAST = [
    "Dlamini", "Nkosi", "van Wyk", "Naidoo", "Mokoena", "Botha", "Khumalo", "Pillay",
    "Mahlangu", "Petersen", "Ndlovu", "Smit", "Mthembu", "Govender", "Molefe", "Jacobs",
]  # fmt: skip

# How people actually ask for things, mapped to what the fictional catalogue calls them.
# None means the catalogue has nothing like it (an honest coverage gap, not a typo).
COLLOQUIAL: dict[str, str | None] = {
    "mielie meal": "maize meal", "pap": "maize meal", "mealie meal 10kg": "maize meal",
    "iMpuphu": "maize meal", "samp": "Samp", "umngqusho": "Samp", "rice": "rice",
    "sugar": "sugar", "suiker": "sugar", "oil": "Sunflower oil", "cooking oil": "Sunflower oil",
    "flour": "Cake flour", "meel": "Cake flour", "bread": "bread", "brood": "bread",
    "isinkwa": "bread", "milk": "milk", "melk": "milk", "amasi": None, "eggs": "eggs",
    "amaqanda": "eggs", "butter": "Butter", "Rama": "Margarine", "cheese": "Cheddar",
    "chicken": "chicken", "inkukhu": "chicken", "mince": "mince", "wors": "Boerewors",
    "boerie": "Boerewors", "polony": "Polony", "potatoes": "Potatoes", "amazambane": "Potatoes",
    "onions": "Onions", "tomatoes": "Tomatoes", "apples": "Apples", "bananas": "Bananas",
    "cabbage": "Cabbage", "carrots": "Carrots", "Koo beans": "Baked beans",
    "baked beans": "Baked beans", "pilchards": "Pilchards", "tinned fish": "Pilchards",
    "tuna": "Tuna", "chakalaka": "Chakalaka", "peanut butter": "Peanut butter",
    "jam": "jam", "mayo": "Mayonnaise", "All Gold": "Tomato sauce",
    "tomato sauce": "Tomato sauce", "Royco": "Soup powder", "Knorrox": "Stock cubes",
    "atchar": "atchar", "curry": "Curry", "rooibos": "Rooibos", "Five Roses": "Black tea",
    "tea": "tea", "Ricoffy": "Instant coffee", "coffee": "coffee", "Cremora": "creamer",
    "coke": "Cola", "cooldrink": "Cola", "juice": "juice", "water": "water",
    "Nik Naks": "Maize snacks", "Simba": None, "biscuits": "biscuits",
    "Marie biscuits": "Tea biscuits", "formula": "formula", "Nan": "formula",
    "Huggies": "Nappies", "nappies": "Nappies", "wipes": "wipes",
    "Sunlight liquid": "Dishwashing", "dish soap": "Dishwashing", "Omo": "Washing powder",
    "washing powder": "Washing powder", "Sta-soft": "softener", "Jik": "Bleach",
    "bleach": "Bleach", "toilet paper": "Toilet tissue", "loo roll": "Toilet tissue",
    "black bags": "Refuse bags", "soap": "soap", "Lifebuoy": "soap",
    "Colgate": "Toothpaste", "toothpaste": "Toothpaste", "Vaseline": "jelly",
    "matches": "Matches", "candles": "Candles", "dog food": "dog food",
    "batteries": "batteries", "AA batteries": "batteries", "globes": "LED bulb",
    "light bulbs": "LED bulb", "lamp for loadshedding": "lantern", "gas": "gas",
    "gas refill": "gas", "inverter": None, "power station": "power station",
    "cement": "Cement", "PPC cement": "Cement", "tile glue": "Tile adhesive",
    "paint": "paint", "Dulux": "PVA paint", "roller": "roller", "brush": "brush",
    "screws": "screws", "nails": "nails", "silicone": "Silicone", "extension cord": "Extension",
    "lead": "Extension", "padlock": "Padlock", "hosepipe": "hose", "wheelbarrow": "Wheelbarrow",
    "airtime": None, "electricity": None, "prepaid electricity": None, "data bundle": None,
    "PS5": None, "Lotto ticket": None, "braai wood": None, "ice": None, "paraffin": None,
    "cigarettes": None, "beer": None, "medication": None, "school shoes": None,
    # Furniture, appliances and electronics (catalogue-scale market only)
    "couch": "Sofa", "sofa": "Sofa", "lounge suite": "Sofa", "bed": "Bed set",
    "mattress": "Mattress", "bunk bed": "Bunk bed", "wardrobe": "Wardrobe",
    "drawers": "Chest of drawers", "dining set": "Dining set", "TV stand": "TV stand",
    "desk": "Desk", "office chair": "Office chair", "fridge": "Fridge",
    "washing machine": "Washing machine", "stove": "Stove", "microwave": "Microwave",
    "rug": "Rug", "curtains": "Curtains", "TV": "LED TV", "smartphone": "Smartphone",
    "kettle": "Electric kettle", "toaster": "Toaster",
}  # fmt: skip

GROCERY_WORDS = [w for w, v in COLLOQUIAL.items() if v and w not in {
    "cement", "PPC cement", "tile glue", "paint", "Dulux", "roller", "brush", "screws",
    "nails", "silicone", "extension cord", "lead", "padlock", "hosepipe", "wheelbarrow",
    "power station", "gas", "gas refill", "lamp for loadshedding", "globes", "light bulbs",
    "batteries", "AA batteries",
}]  # fmt: skip
HARDWARE_WORDS = [
    "cement", "PPC cement", "tile glue", "paint", "Dulux", "roller", "brush", "screws",
    "nails", "silicone", "extension cord", "padlock", "hosepipe", "wheelbarrow",
]  # fmt: skip
LOADSHEDDING_WORDS = ["candles", "gas refill", "lamp for loadshedding", "AA batteries",
                      "power station", "matches", "inverter", "globes"]  # fmt: skip
GAP_WORDS = [w for w, v in COLLOQUIAL.items() if v is None]
FURNITURE_WORDS = [
    "couch", "sofa", "lounge suite", "bed", "mattress", "bunk bed", "wardrobe", "drawers",
    "dining set", "TV stand", "desk", "office chair", "fridge", "washing machine", "stove",
    "microwave", "rug", "curtains",
]  # fmt: skip
RESELLABLE_WORDS = ["TV", "smartphone", "fridge", "washing machine", "power station", "microwave"]
_NOT_GROCERY = set(FURNITURE_WORDS + RESELLABLE_WORDS + ["kettle", "toaster"])
GROCERY_WORDS = [w for w in GROCERY_WORDS if w not in _NOT_GROCERY]

GREETINGS = {
    "en": ["Hi", "Hello", "Morning", "Hey there", ""],
    "zu": ["Sawubona", "Yebo", "Heita", "Sanibonani"],
    "af": ["Hallo", "Goeie môre", "Howzit"],
    "sms": ["hi", "hey", "yo", ""],
}
ASKS = {
    "en": ["I need {x}", "Please get me {x}", "Can you find {x}?", "Add {x}", "We're out of {x}"],
    "zu": ["Ngicela {x}", "Ngidinga {x}", "Ngifuna {x} please", "Sicela {x} bandla"],
    "af": ["Ek soek {x}", "Kan jy vir my {x} kry?", "Ons het {x} nodig"],
    "sms": ["{x} pls", "need {x} asap", "{x}??", "get {x} cheap"],
}


@dataclass
class Archetype:
    key: str
    label: str
    mean_think_s: float  # mean pause between actions
    card_success: float  # chance the bank step succeeds when they try to pay
    list_size: tuple[int, int]
    word_pools: list[list[str]]
    budget_rands: tuple[int, int]
    traits: set[str] = field(default_factory=set)


ARCHETYPES = {
    "careful": Archetype(
        "careful",
        "Absolutely legit, careful shopper",
        9,
        0.97,
        (5, 12),
        [GROCERY_WORDS],
        (800, 2500),
        {"reads_quote", "prefers_complete"},
    ),
    "household": Archetype(
        "household",
        "Regular household",
        7,
        0.9,
        (4, 10),
        [GROCERY_WORDS, LOADSHEDDING_WORDS],
        (500, 2000),
        {"wallet_sometimes"},
    ),
    "broke": Archetype(
        "broke",
        "Broke, tries anyway",
        6,
        0.15,
        (3, 9),
        [GROCERY_WORDS, ["formula", "Huggies", "power station", "chicken", "wors"]],
        (30, 250),
        {"retries_payment", "low_budget", "small_topups", "overreaches"},
    ),
    "impulsive": Archetype(
        "impulsive",
        "Impulsive, changes mind",
        4,
        0.85,
        (1, 6),
        [GROCERY_WORDS, GAP_WORDS, LOADSHEDDING_WORDS],
        (200, 1500),
        {"abandons", "cancels", "double_clicks"},
    ),
    "confused": Archetype(
        "confused",
        "Low-tech, confused",
        12,
        0.8,
        (1, 5),
        [GROCERY_WORDS, GAP_WORDS],
        (200, 800),
        {"typos", "wrong_inputs", "slow"},
    ),
    "builder": Archetype(
        "builder",
        "DIY / small builder",
        8,
        0.9,
        (3, 8),
        [HARDWARE_WORDS, GROCERY_WORDS],
        (1500, 12000),
        {"bulk"},
    ),
    "stokvel": Archetype(
        "stokvel",
        "Stokvel bulk buyer",
        10,
        0.85,
        (4, 8),
        [GROCERY_WORDS],
        (3000, 15000),
        {"bulk", "wallet", "agent"},
    ),
    "delegator": Archetype(
        "delegator",
        "Busy parent using an agent",
        9,
        0.95,
        (4, 10),
        [GROCERY_WORDS],
        (800, 3000),
        {"wallet", "agent"},
    ),
    "malicious": Archetype(
        "malicious",
        "Malicious",
        3,
        0.5,
        (1, 4),
        [GROCERY_WORDS],
        (50, 500),
        {"attacker"},
    ),
    "furniture": Archetype(
        "furniture", "Furnishing a home", 10, 0.9, (1, 3), [FURNITURE_WORDS],
        (4000, 40000), {"big_ticket"},
    ),
    "fraudster": Archetype(
        "fraudster", "Loads stolen money into the wallet", 4, 0.3, (1, 3),
        [RESELLABLE_WORDS], (8000, 25000), {"stolen_funds"},
    ),
    "hijacker": Archetype(
        "hijacker", "Has stolen someone's shopping agent", 3, 0.3, (2, 6),
        [RESELLABLE_WORDS, GROCERY_WORDS], (0, 0), {"hijacks_agents"},
    ),
}  # fmt: skip


@dataclass
class Persona:
    name: str
    archetype: Archetype
    zone: str
    language: str
    budget_rands: int
    rng: random.Random
    brain: str = "stochastic"
    model: str | None = None

    @property
    def is_attacker(self) -> bool:
        return "attacker" in self.archetype.traits

    def utterance(self, word: str) -> str:
        greet = self.rng.choice(GREETINGS[self.language])
        ask = self.rng.choice(ASKS[self.language]).format(x=word)
        text = f"{greet} {ask}".strip()
        if "typos" in self.archetype.traits and self.rng.random() < 0.5:
            text = _typo(text, self.rng)
        return text


def _typo(text: str, rng: random.Random) -> str:
    chars = list(text)
    for _ in range(rng.randint(1, 3)):
        i = rng.randrange(len(chars))
        chars[i] = rng.choice("aeiouxzq ")
    return "".join(chars)


def draw_crowd(n: int, rng: random.Random, *, large: bool = False) -> list[Persona]:
    """A random crowd: a few attackers, a few model citizens, a few broke, the rest mixed."""
    counts = {
        "malicious": rng.randint(max(1, n // 20), max(2, n // 8)),
        "careful": rng.randint(max(1, n // 15), max(2, n // 7)),
        "broke": rng.randint(max(1, n // 15), max(2, n // 6)),
    }
    if large:
        counts |= {
            "fraudster": rng.randint(1, max(1, n // 20)),
            "hijacker": rng.randint(1, max(1, n // 30)),
            "delegator": rng.randint(max(2, n // 12), max(3, n // 6)),  # someone to hijack
            "furniture": rng.randint(max(2, n // 15), max(3, n // 8)),
        }
    rest = n - sum(counts.values())
    others = ["household", "impulsive", "confused", "stokvel", "delegator"]
    others += ["furniture"] if large else ["builder"]
    weights = [rng.uniform(0.5, 3) for _ in others]
    for _ in range(rest):
        k = rng.choices(others, weights)[0]
        counts[k] = counts.get(k, 0) + 1
    people = []
    names = set()
    for key, count in counts.items():
        arch = ARCHETYPES[key]
        for _ in range(count):
            while True:
                name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                if name not in names:
                    names.add(name)
                    break
            people.append(
                Persona(
                    name=name,
                    archetype=arch,
                    zone=rng.choice(MARKET_ZONES),
                    language=rng.choices(["en", "zu", "af", "sms"], [4, 3, 2, 2])[0],
                    budget_rands=rng.randint(*arch.budget_rands) if arch.budget_rands[1] else 0,
                    rng=random.Random(rng.getrandbits(64)),
                )
            )
    rng.shuffle(people)
    return people
