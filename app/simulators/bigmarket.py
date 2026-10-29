# ruff: noqa: E501 - tabular fixture data reads better unwrapped
"""Catalogue-scale synthetic market for crowd simulations. SIMULATED — NOT REAL MONEY.

About 63 000 canonical products generated deterministically from a taxonomy (department →
product type → brand → variant → size), and five invented merchants:

| Merchant | Range | What it is for |
|---|---|---|
| Ubuntu Hypermarket | ~50 000 | big range, slow and flaky integration |
| Zest Express | ~20 000 | quick integration, couriers often late |
| Fairbasket Supermarkets | ~18 000 | an ordinary, well-behaved store |
| Kaya Living | ~2 500 furniture and appliances | new merchant, legitimate, slow multi-day delivery |
| BargainBox Direct | ~760 popular lines | new merchant that passed onboarding with forged documents: prices too good to be true, accepts every order, never hands anything over |

Every name is invented. Nothing was scraped or copied from any retailer (DECISIONS.md
I-036). Range sizes are of the order a large South African grocer carries; prices are
generated from hand-set reference levels, not market data.

Time is compressed for simulation runs (a 20-minute run is one shopping day): grocery
delivery windows are 5 minutes long and start 4-8 minutes out; "multi-day" furniture
delivery starts 20 minutes out.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.delivery.models import DeliverySlot
from app.merchants.models import Merchant, MerchantCapability, MerchantLocation, MerchantState
from app.offers.models import Promotion, PromotionKind
from app.products.models import Product
from app.seed import COURIER, _ensure, gtin13
from app.simulators.market import REGIONS
from app.simulators.models import SimMerchantLatency

NS = uuid.UUID("0b8f3d5e-6c1a-4e7b-9f2d-3a5c7e9b1d42")
ALL_ZONES = tuple(z for zones in REGIONS.values() for z in zones)


def u(*parts: object) -> float:
    """Deterministic pseudo-random number in [0, 1)."""
    digest = hashlib.sha256(":".join(map(str, parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def pid(code: str) -> uuid.UUID:
    return uuid.uuid5(NS, f"product:{code}")


# --- Taxonomy ------------------------------------------------------------------------

FLAV = ["original", "chocolate", "strawberry", "vanilla", "banana", "caramel", "mint", "lemon"]
SNACK = [
    "salted",
    "cheese",
    "chutney",
    "salt & vinegar",
    "barbecue",
    "sour cream",
    "chilli",
    "tomato",
]
SCENT = ["original", "lemon", "lavender", "fresh linen", "ocean", "rose", "unscented", "aloe"]
FRUIT = ["mango", "orange", "apple", "guava", "litchi", "tropical", "berry", "grape"]
SPICE = ["mild", "medium", "hot", "extra hot", "peri-peri"]
PLAIN = [""]

# (code, name, category, unit, sizes, ref cents for first size, variants, brands, ambient, zero-rated)
TYPES: list[tuple] = [
    (
        "maize",
        "Super maize meal",
        "staples",
        "g",
        [1000, 2500, 5000, 10000, 12500],
        2299,
        ["", "special", "roller"],
        30,
        True,
        True,
    ),
    ("samp", "Samp", "staples", "g", [1000, 2000, 5000], 1899, ["", "and beans"], 12, True, True),
    (
        "rice",
        "Long grain rice",
        "staples",
        "g",
        [1000, 2000, 5000, 10000],
        2499,
        ["", "parboiled", "basmati", "jasmine"],
        28,
        True,
        True,
    ),
    (
        "sugar",
        "White sugar",
        "staples",
        "g",
        [1000, 2500, 5000, 10000],
        2499,
        ["", "castor", "brown"],
        14,
        True,
        False,
    ),
    (
        "oil",
        "Sunflower oil",
        "staples",
        "ml",
        [750, 2000, 5000],
        2999,
        ["", "canola blend"],
        20,
        True,
        True,
    ),
    (
        "flour",
        "Cake flour",
        "staples",
        "g",
        [1000, 2500, 5000, 10000],
        1899,
        ["", "self-raising", "bread"],
        18,
        True,
        False,
    ),
    (
        "pasta",
        "Spaghetti",
        "staples",
        "g",
        [500, 1000, 3000],
        2199,
        ["", "whole wheat"],
        24,
        True,
        False,
    ),
    (
        "macaroni",
        "Macaroni",
        "staples",
        "g",
        [500, 1000, 3000],
        2199,
        ["", "elbow"],
        18,
        True,
        False,
    ),
    (
        "drybeans",
        "Sugar beans",
        "staples",
        "g",
        [500, 1000, 2000],
        3299,
        ["dried", "speckled"],
        14,
        True,
        True,
    ),
    ("lentils", "Lentils", "staples", "g", [500, 1000], 2999, ["brown", "red"], 10, True, True),
    (
        "oats",
        "Rolled oats",
        "breakfast",
        "g",
        [500, 1000, 2000],
        2599,
        ["", "instant", "jungle"],
        18,
        True,
        False,
    ),
    (
        "cornflakes",
        "Corn flakes",
        "breakfast",
        "g",
        [500, 750, 1000],
        4599,
        ["", "honey"],
        14,
        True,
        False,
    ),
    (
        "wheatbisc",
        "Wheat biscuits",
        "breakfast",
        "g",
        [450, 900],
        4999,
        ["", "bran"],
        10,
        True,
        False,
    ),
    (
        "muesli",
        "Muesli",
        "breakfast",
        "g",
        [500, 750, 1000],
        5499,
        ["fruit", "nut", "berry", "low sugar"],
        16,
        True,
        False,
    ),
    ("pronutro", "Wheat porridge", "breakfast", "g", [500, 1000], 3999, FLAV[:4], 10, True, False),
    (
        "bread",
        "Brown bread",
        "bakery",
        "g",
        [600, 700],
        1899,
        ["sliced", "seed loaf"],
        16,
        True,
        True,
    ),
    (
        "wbread",
        "White bread",
        "bakery",
        "g",
        [600, 700],
        2099,
        ["sliced", "toaster"],
        16,
        True,
        False,
    ),
    (
        "rolls",
        "Bread rolls",
        "bakery",
        "each",
        [6, 12],
        2499,
        ["hot dog", "hamburger"],
        12,
        True,
        False,
    ),
    (
        "rusks",
        "Rusks",
        "bakery",
        "g",
        [450, 750],
        5999,
        ["buttermilk", "muesli", "aniseed", "condensed milk"],
        14,
        True,
        False,
    ),
    (
        "uht",
        "UHT milk",
        "dairy",
        "ml",
        [1000],
        1899,
        ["full cream", "low fat", "fat free"],
        18,
        True,
        True,
    ),
    (
        "milk",
        "Fresh milk",
        "dairy",
        "ml",
        [1000, 2000, 3000],
        2199,
        ["full cream", "low fat", "fat free"],
        14,
        False,
        True,
    ),
    (
        "maas",
        "Fermented milk",
        "dairy",
        "ml",
        [1000, 2000],
        2799,
        ["plain", "flavoured"],
        8,
        False,
        True,
    ),
    (
        "eggs",
        "Large eggs",
        "dairy",
        "each",
        [6, 18, 30, 60],
        2799,
        ["", "free range"],
        12,
        True,
        True,
    ),
    ("butter", "Butter", "dairy", "g", [250, 500], 5499, ["salted", "unsalted"], 10, False, False),
    (
        "marg",
        "Margarine spread",
        "dairy",
        "g",
        [500, 1000],
        3499,
        ["original", "lite", "with olive oil"],
        12,
        False,
        False,
    ),
    (
        "cheddar",
        "Cheddar cheese",
        "dairy",
        "g",
        [400, 900],
        7999,
        ["mild", "mature", "sliced"],
        14,
        False,
        False,
    ),
    (
        "yoghurt",
        "Yoghurt",
        "dairy",
        "g",
        [175, 1000],
        1299,
        FLAV[:5] + ["plain", "double cream"],
        18,
        False,
        False,
    ),
    ("custard", "Custard", "dairy", "ml", [500, 1000], 2499, ["vanilla", "banana"], 8, True, False),
    (
        "chicken",
        "Frozen chicken portions",
        "meat",
        "g",
        [1000, 2000, 5000],
        6999,
        ["mixed", "thighs", "drumsticks", "wings"],
        14,
        False,
        False,
    ),
    ("mince", "Beef mince", "meat", "g", [500, 1000], 6999, ["lean", "regular"], 10, False, False),
    (
        "wors",
        "Boerewors",
        "meat",
        "g",
        [500, 1000],
        6999,
        ["traditional", "spicy", "garlic"],
        12,
        False,
        False,
    ),
    ("polony", "Polony", "meat", "g", [500, 1000, 3000], 2999, ["", "chicken"], 10, False, False),
    ("vienna", "Viennas", "meat", "g", [500, 1000], 4499, ["", "cheese"], 10, False, False),
    (
        "potatoes",
        "Potatoes",
        "produce",
        "g",
        [2000, 7000, 10000],
        3999,
        ["", "baby"],
        6,
        True,
        True,
    ),
    ("onions", "Onions", "produce", "g", [1000, 2000, 7000], 1899, ["brown", "red"], 6, True, True),
    ("tomatoes", "Tomatoes", "produce", "g", [500, 1000], 1999, ["", "cherry"], 6, True, True),
    ("apples", "Apples", "produce", "g", [1500, 3000], 3299, ["red", "green"], 8, True, True),
    ("bananas", "Bananas", "produce", "g", [1000], 2699, [""], 6, True, True),
    ("oranges", "Oranges", "produce", "g", [1500, 3000], 3299, [""], 6, True, True),
    ("cabbage", "Cabbage", "produce", "each", [1], 1999, ["green", "red"], 4, True, True),
    ("carrots", "Carrots", "produce", "g", [500, 1000], 1599, [""], 6, True, True),
    ("spinach", "Spinach", "produce", "g", [250, 500], 1999, ["", "baby"], 6, False, True),
    (
        "bakedbeans",
        "Baked beans",
        "tins",
        "g",
        [410, 3000],
        1799,
        ["in tomato sauce", "in chakalaka"],
        18,
        True,
        False,
    ),
    (
        "pilchards",
        "Pilchards",
        "tins",
        "g",
        [155, 400],
        2199,
        ["in tomato sauce", "in chilli sauce"],
        10,
        True,
        True,
    ),
    (
        "tuna",
        "Tuna chunks",
        "tins",
        "g",
        [170, 400],
        2999,
        ["in brine", "in oil", "in chilli"],
        14,
        True,
        False,
    ),
    ("chakalaka", "Chakalaka relish", "tins", "g", [410, 3000], 1799, SPICE, 14, True, False),
    (
        "cannedveg",
        "Mixed vegetables",
        "tins",
        "g",
        [410],
        1599,
        ["", "butter beans", "peas", "sweetcorn"],
        14,
        True,
        False,
    ),
    (
        "tomtin",
        "Chopped tomatoes",
        "tins",
        "g",
        [410],
        1499,
        ["", "and onion", "with basil"],
        14,
        True,
        False,
    ),
    (
        "fruittin",
        "Canned peaches",
        "tins",
        "g",
        [410, 825],
        2499,
        ["halves", "slices", "fruit cocktail"],
        10,
        True,
        False,
    ),
    (
        "peanut",
        "Peanut butter",
        "pantry",
        "g",
        [400, 800],
        4299,
        ["smooth", "crunchy"],
        14,
        True,
        False,
    ),
    (
        "jam",
        "Fruit jam",
        "pantry",
        "g",
        [450, 900],
        3999,
        ["apricot", "strawberry", "mixed fruit", "fig"],
        14,
        True,
        False,
    ),
    (
        "mayo",
        "Mayonnaise",
        "pantry",
        "g",
        [375, 750, 3000],
        3299,
        ["", "lite", "garlic"],
        12,
        True,
        False,
    ),
    (
        "tsauce",
        "Tomato sauce",
        "pantry",
        "ml",
        [350, 700, 2000],
        2499,
        ["", "no added sugar"],
        12,
        True,
        False,
    ),
    (
        "chutney",
        "Fruit chutney",
        "pantry",
        "ml",
        [470, 1000],
        3299,
        ["original", "hot"],
        8,
        True,
        False,
    ),
    (
        "soup",
        "Soup powder",
        "pantry",
        "g",
        [400, 1000],
        3499,
        ["brown onion", "oxtail", "minestrone", "chicken"],
        10,
        True,
        False,
    ),
    (
        "stock",
        "Stock cubes",
        "pantry",
        "each",
        [12, 24],
        2299,
        ["beef", "chicken", "vegetable"],
        10,
        True,
        False,
    ),
    ("atchar", "Mango atchar", "pantry", "g", [380, 1000], 2999, SPICE[:3], 10, True, False),
    ("curry", "Curry powder", "pantry", "g", [50, 100, 500], 1499, SPICE, 14, True, False),
    (
        "spice",
        "Braai spice",
        "pantry",
        "g",
        [100, 200, 500],
        2299,
        ["", "steak", "chicken", "lemon pepper"],
        16,
        True,
        False,
    ),
    (
        "salt",
        "Table salt",
        "pantry",
        "g",
        [500, 1000],
        1099,
        ["", "iodated", "coarse"],
        8,
        True,
        False,
    ),
    ("vinegar", "Vinegar", "pantry", "ml", [750], 1499, ["brown", "white"], 6, True, False),
    ("honey", "Honey", "pantry", "g", [375, 500], 6499, ["", "fynbos"], 8, True, False),
    (
        "rooibos",
        "Rooibos tea",
        "beverages",
        "each",
        [40, 80, 160],
        2799,
        ["", "honeybush", "vanilla"],
        16,
        True,
        False,
    ),
    (
        "blacktea",
        "Black tea",
        "beverages",
        "each",
        [100, 200],
        4999,
        ["", "decaf"],
        12,
        True,
        False,
    ),
    (
        "coffee",
        "Instant coffee",
        "beverages",
        "g",
        [100, 200, 750],
        7499,
        ["", "decaf", "chicory blend"],
        16,
        True,
        False,
    ),
    (
        "groundcoffee",
        "Ground coffee",
        "beverages",
        "g",
        [250, 500, 1000],
        8999,
        ["medium roast", "dark roast", "espresso"],
        20,
        True,
        False,
    ),
    (
        "creamer",
        "Coffee creamer",
        "beverages",
        "g",
        [400, 750, 1000],
        3999,
        ["", "lite"],
        8,
        True,
        False,
    ),
    ("cola", "Cola", "beverages", "ml", [330, 1500, 2000], 1099, ["", "no sugar"], 10, True, False),
    (
        "softdrink",
        "Soft drink",
        "beverages",
        "ml",
        [330, 1500, 2000],
        999,
        ["orange", "lemon-lime", "cream soda", "ginger beer", "granadilla"],
        16,
        True,
        False,
    ),
    ("juice", "Fruit juice", "beverages", "ml", [1000, 2000, 5000], 2999, FRUIT, 18, True, False),
    ("cordial", "Cordial", "beverages", "ml", [1000, 2000, 5000], 3499, FRUIT, 12, True, False),
    (
        "water",
        "Still water",
        "beverages",
        "ml",
        [500, 1500, 5000],
        999,
        ["", "sparkling"],
        12,
        True,
        False,
    ),
    (
        "energy",
        "Energy drink",
        "beverages",
        "ml",
        [250, 500],
        1499,
        ["original", "sugar free", "berry"],
        12,
        True,
        False,
    ),
    ("chips", "Potato chips", "snacks", "g", [36, 125, 200], 1499, SNACK, 18, True, False),
    (
        "maizesnack",
        "Maize snacks",
        "snacks",
        "g",
        [25, 135],
        899,
        ["cheese", "chutney", "spicy"],
        10,
        True,
        False,
    ),
    (
        "biscuits",
        "Tea biscuits",
        "snacks",
        "g",
        [200, 500],
        1999,
        ["", "coconut", "lemon cream", "chocolate"],
        18,
        True,
        False,
    ),
    (
        "choc",
        "Chocolate slab",
        "snacks",
        "g",
        [80, 150],
        2599,
        ["milk", "dark", "mint", "nut"],
        14,
        True,
        False,
    ),
    (
        "sweets",
        "Sweets",
        "snacks",
        "g",
        [125, 500],
        1999,
        ["jelly", "toffee", "sour", "mint"],
        16,
        True,
        False,
    ),
    (
        "nuts",
        "Roasted peanuts",
        "snacks",
        "g",
        [100, 400, 1000],
        2499,
        ["salted", "and raisins", "chilli"],
        12,
        True,
        False,
    ),
    (
        "frozenveg",
        "Frozen vegetables",
        "frozen",
        "g",
        [1000, 2500],
        3499,
        ["mixed", "peas", "stir fry"],
        10,
        False,
        False,
    ),
    ("icecream", "Ice cream", "frozen", "ml", [2000, 5000], 4999, FLAV[:6], 12, False, False),
    (
        "chips_frozen",
        "Frozen chips",
        "frozen",
        "g",
        [1000, 2500],
        3999,
        ["straight cut", "crinkle"],
        8,
        False,
        False,
    ),
    (
        "formula",
        "Infant formula",
        "baby",
        "g",
        [400, 900, 1800],
        15999,
        ["stage 1", "stage 2", "stage 3"],
        8,
        True,
        False,
    ),
    (
        "babycereal",
        "Infant cereal",
        "baby",
        "g",
        [250, 500],
        4999,
        ["rice", "wheat", "fruit"],
        8,
        True,
        False,
    ),
    (
        "nappies",
        "Nappies",
        "baby",
        "each",
        [24, 44, 64, 100],
        11999,
        ["size 1", "size 2", "size 3", "size 4", "size 5"],
        10,
        True,
        False,
    ),
    (
        "wipes",
        "Baby wipes",
        "baby",
        "each",
        [64, 80, 240],
        3999,
        ["", "sensitive"],
        10,
        True,
        False,
    ),
    (
        "dish",
        "Dishwashing liquid",
        "household",
        "ml",
        [400, 750, 1500, 5000],
        2299,
        SCENT[:5],
        18,
        True,
        False,
    ),
    (
        "washing",
        "Washing powder",
        "household",
        "g",
        [500, 1000, 2000, 5000],
        4499,
        ["hand wash", "auto", "sensitive"],
        16,
        True,
        False,
    ),
    (
        "liquiddet",
        "Laundry liquid",
        "household",
        "ml",
        [1500, 3000],
        8999,
        ["auto", "colour", "sensitive"],
        12,
        True,
        False,
    ),
    (
        "softener",
        "Fabric softener",
        "household",
        "ml",
        [500, 1000, 2000, 4000],
        2999,
        SCENT,
        14,
        True,
        False,
    ),
    (
        "bleach",
        "Bleach",
        "household",
        "ml",
        [750, 1500, 5000],
        2499,
        ["", "thick", "lemon"],
        10,
        True,
        False,
    ),
    (
        "surface",
        "Surface cleaner",
        "household",
        "ml",
        [500, 750, 1500],
        3999,
        SCENT[:4],
        14,
        True,
        False,
    ),
    (
        "tissue",
        "Toilet tissue",
        "household",
        "each",
        [4, 9, 18, 24],
        4499,
        ["1-ply", "2-ply", "3-ply"],
        14,
        True,
        False,
    ),
    ("towels", "Paper towels", "household", "each", [2, 4], 2999, ["", "jumbo"], 10, True, False),
    (
        "refuse",
        "Refuse bags",
        "household",
        "each",
        [10, 20, 50],
        2499,
        ["", "heavy duty"],
        10,
        True,
        False,
    ),
    (
        "foil",
        "Aluminium foil",
        "household",
        "each",
        [1],
        3499,
        ["5m", "10m", "30m"],
        8,
        True,
        False,
    ),
    ("matches", "Matches", "household", "each", [10], 1499, [""], 6, True, False),
    (
        "candles",
        "Candles",
        "household",
        "each",
        [6, 12, 24],
        2999,
        ["household", "long burn"],
        8,
        True,
        False,
    ),
    (
        "insect",
        "Insect spray",
        "household",
        "ml",
        [300, 600],
        4499,
        ["multi-insect", "mosquito", "cockroach"],
        8,
        True,
        False,
    ),
    ("soap", "Bath soap", "personal", "each", [1, 4, 6], 1299, SCENT, 18, True, False),
    ("bodywash", "Body wash", "personal", "ml", [400, 750], 4999, SCENT, 16, True, False),
    (
        "toothpaste",
        "Toothpaste",
        "personal",
        "ml",
        [75, 100, 150],
        2499,
        ["regular", "whitening", "sensitive", "herbal"],
        12,
        True,
        False,
    ),
    (
        "toothbrush",
        "Toothbrush",
        "personal",
        "each",
        [1, 2, 4],
        2499,
        ["soft", "medium"],
        10,
        True,
        False,
    ),
    (
        "deo",
        "Roll-on deodorant",
        "personal",
        "ml",
        [50, 150],
        2999,
        ["men", "women", "sensitive"],
        16,
        True,
        False,
    ),
    (
        "lotion",
        "Body lotion",
        "personal",
        "ml",
        [400, 750],
        5499,
        ["aloe", "cocoa butter", "shea", "unscented"],
        14,
        True,
        False,
    ),
    (
        "jelly",
        "Petroleum jelly",
        "personal",
        "ml",
        [100, 250, 500],
        2499,
        ["", "cocoa butter", "baby"],
        8,
        True,
        False,
    ),
    (
        "shampoo",
        "Shampoo",
        "personal",
        "ml",
        [400, 750],
        5499,
        ["everyday", "anti-dandruff", "curl care", "kids"],
        16,
        True,
        False,
    ),
    (
        "sanitary",
        "Sanitary pads",
        "personal",
        "each",
        [8, 16, 32],
        3499,
        ["regular", "maxi", "night"],
        10,
        True,
        False,
    ),
    (
        "razor",
        "Disposable razors",
        "personal",
        "each",
        [5, 10],
        4999,
        ["men", "women"],
        8,
        True,
        False,
    ),
    (
        "painkiller",
        "Pain tablets",
        "health",
        "each",
        [20, 48],
        4999,
        ["paracetamol", "ibuprofen"],
        8,
        True,
        False,
    ),
    (
        "vitamins",
        "Multivitamins",
        "health",
        "each",
        [30, 60],
        12999,
        ["adult", "kids", "50+"],
        10,
        True,
        False,
    ),
    (
        "dogfood",
        "Dry dog food",
        "pets",
        "g",
        [2000, 8000, 20000],
        9999,
        ["adult", "puppy", "senior"],
        12,
        True,
        False,
    ),
    (
        "catfood",
        "Dry cat food",
        "pets",
        "g",
        [1000, 4000],
        8999,
        ["adult", "kitten"],
        10,
        True,
        False,
    ),
    (
        "cattin",
        "Wet cat food",
        "pets",
        "g",
        [85, 400],
        1499,
        ["chicken", "fish", "beef"],
        10,
        True,
        False,
    ),
    # Hypermarket general merchandise and DIY
    (
        "batteries",
        "AA batteries",
        "hardware",
        "each",
        [4, 8, 16],
        5999,
        ["alkaline", "rechargeable"],
        8,
        True,
        False,
    ),
    (
        "ledbulb",
        "LED bulb",
        "hardware",
        "each",
        [1, 2, 4],
        3999,
        ["9W", "12W", "warm white"],
        10,
        True,
        False,
    ),
    (
        "lantern",
        "Rechargeable LED lantern",
        "hardware",
        "each",
        [1],
        14999,
        ["small", "large", "solar"],
        10,
        True,
        False,
    ),
    ("gas", "LP gas refill", "hardware", "g", [3000, 9000], 19999, ["exchange"], 6, True, False),
    (
        "powerstation",
        "Portable power station",
        "hardware",
        "each",
        [1],
        399999,
        ["300Wh", "600Wh", "1000Wh"],
        6,
        True,
        False,
    ),
    (
        "extension",
        "Extension cord",
        "hardware",
        "each",
        [1],
        12999,
        ["3m", "5m", "10m"],
        8,
        True,
        False,
    ),
    ("padlock", "Padlock", "hardware", "each", [1], 8999, ["40mm", "50mm", "60mm"], 8, True, False),
    (
        "cement",
        "Cement",
        "building",
        "g",
        [25000, 50000],
        6999,
        ["general purpose", "rapid set"],
        6,
        True,
        False,
    ),
    (
        "tileadh",
        "Tile adhesive",
        "building",
        "g",
        [5000, 20000],
        6999,
        ["", "flexible"],
        6,
        True,
        False,
    ),
    (
        "paint",
        "PVA paint",
        "building",
        "ml",
        [1000, 5000, 20000],
        12999,
        ["white", "magnolia", "grey", "sky blue"],
        10,
        True,
        False,
    ),
    ("roller", "Paint roller", "building", "each", [1], 3999, ["150mm", "225mm"], 8, True, False),
    (
        "brush",
        "Paint brush",
        "building",
        "each",
        [1, 3],
        2499,
        ["25mm", "50mm", "75mm"],
        8,
        True,
        False,
    ),
    (
        "screws",
        "Wood screws",
        "building",
        "each",
        [50, 100, 500],
        3999,
        ["4x30mm", "4x40mm", "5x50mm"],
        6,
        True,
        False,
    ),
    (
        "nails",
        "Wire nails",
        "building",
        "g",
        [500, 1000],
        3999,
        ["50mm", "75mm", "100mm"],
        6,
        True,
        False,
    ),
    (
        "silicone",
        "Silicone sealant",
        "building",
        "ml",
        [280],
        7999,
        ["clear", "white"],
        6,
        True,
        False,
    ),
    ("hose", "Garden hose", "garden", "each", [1], 24999, ["15m", "20m", "30m"], 8, True, False),
    ("wheelbarrow", "Wheelbarrow", "garden", "each", [1], 69999, ["65L", "85L"], 6, True, False),
    (
        "kettle",
        "Electric kettle",
        "appliances",
        "each",
        [1],
        29999,
        ["1.7L", "cordless", "stainless"],
        12,
        True,
        False,
    ),
    (
        "toaster",
        "Toaster",
        "appliances",
        "each",
        [1],
        34999,
        ["2-slice", "4-slice"],
        10,
        True,
        False,
    ),
    ("iron", "Steam iron", "appliances", "each", [1], 39999, [""], 8, True, False),
    (
        "phone",
        "Smartphone",
        "electronics",
        "each",
        [1],
        249999,
        ["64GB", "128GB", "256GB"],
        10,
        True,
        False,
    ),
    (
        "tv",
        "LED TV",
        "electronics",
        "each",
        [1],
        499999,
        ["32-inch", "43-inch", "55-inch", "65-inch"],
        8,
        True,
        False,
    ),
]

FURNITURE: list[tuple] = [
    (
        "sofa",
        "Sofa",
        "furniture",
        ["2-seater", "3-seater", "L-shape", "sleeper"],
        ["charcoal", "grey", "beige", "navy", "green"],
        649999,
    ),
    (
        "bed",
        "Bed set",
        "furniture",
        ["single", "three-quarter", "double", "queen", "king"],
        ["firm", "medium", "plush"],
        449999,
    ),
    (
        "mattress",
        "Mattress",
        "furniture",
        ["single", "double", "queen", "king"],
        ["foam", "pocket spring", "orthopaedic"],
        299999,
    ),
    (
        "bunk",
        "Bunk bed",
        "furniture",
        ["single over single", "single over double"],
        ["white", "pine", "black"],
        399999,
    ),
    (
        "wardrobe",
        "Wardrobe",
        "furniture",
        ["2-door", "3-door", "sliding"],
        ["white", "oak", "walnut"],
        349999,
    ),
    (
        "drawers",
        "Chest of drawers",
        "furniture",
        ["3-drawer", "5-drawer"],
        ["white", "oak", "walnut"],
        199999,
    ),
    (
        "dining",
        "Dining set",
        "furniture",
        ["4-seater", "6-seater", "8-seater"],
        ["oak", "walnut", "glass", "white"],
        599999,
    ),
    ("tvunit", "TV stand", "furniture", ["1.2m", "1.6m", "2m"], ["oak", "black", "white"], 249999),
    ("desk", "Desk", "furniture", ["1m", "1.2m", "1.5m"], ["oak", "white", "black"], 149999),
    (
        "officechair",
        "Office chair",
        "furniture",
        ["task", "executive", "mesh"],
        ["black", "grey"],
        129999,
    ),
    ("bookshelf", "Bookshelf", "furniture", ["3-tier", "5-tier"], ["oak", "white", "black"], 99999),
    (
        "coffeetable",
        "Coffee table",
        "furniture",
        ["round", "square", "rectangle"],
        ["oak", "glass", "marble-look"],
        149999,
    ),
    (
        "kitchenunit",
        "Kitchen unit",
        "furniture",
        ["base", "wall", "pantry"],
        ["white", "grey", "oak"],
        249999,
    ),
    (
        "fridge",
        "Fridge",
        "appliances",
        ["single door", "double door", "side-by-side"],
        ["silver", "white", "black"],
        799999,
    ),
    (
        "washer",
        "Washing machine",
        "appliances",
        ["7kg", "9kg", "12kg"],
        ["top loader", "front loader"],
        699999,
    ),
    (
        "stove",
        "Stove",
        "appliances",
        ["4-plate", "gas/electric", "5-burner gas"],
        ["white", "silver", "black"],
        599999,
    ),
    (
        "microwave",
        "Microwave",
        "appliances",
        ["20L", "28L", "34L"],
        ["silver", "white", "black"],
        179999,
    ),
    (
        "rug",
        "Rug",
        "decor",
        ["1.2x1.7m", "1.6x2.3m", "2x2.9m"],
        ["grey", "beige", "patterned"],
        89999,
    ),
    (
        "curtains",
        "Curtains",
        "decor",
        ["2.3m", "3.5m"],
        ["block-out", "sheer", "linen-look"],
        69999,
    ),
]

SYL_A = [
    "Sun",
    "Veld",
    "Karoo",
    "High",
    "Blue",
    "Golden",
    "Cape",
    "Umoya",
    "Ukhozi",
    "Protea",
    "Baobab",
    "Marula",
    "Kalahari",
    "Savanna",
    "Jacaranda",
    "Fynbos",
    "Kudu",
    "Impala",
    "Mopani",
    "Lekker",
    "Thaba",
    "Amber",
    "Coral",
    "River",
    "Silver",
    "Morning",
]
SYL_B = [
    "bird",
    " Valley",
    " Mills",
    " Kitchen",
    "crest",
    " Fields",
    " Farm",
    " Pride",
    " Choice",
    "gold",
    "star",
    " Harvest",
    " Home",
    " Fresh",
    "craft",
    " Peak",
    "dale",
    " Grove",
    " Works",
    " Pantry",
]
FURNITURE_BRANDS = [
    "Kaya Home",
    "Oakhaven",
    "Imbali Living",
    "Tafelberg Furnishers",
    "Sleepwell SA",
    "Nkosi Craft",
    "Urban Kraal",
    "Highveld Sleep",
    "Coastline Living",
    "Ironwood",
    "Masakhane Design",
    "Restful",
    "Kalahari Loft",
    "Ubuntu Interiors",
    "Westbrook",
    "Indaba Home",
]
BRANDS = [a + b for a in SYL_A for b in SYL_B]
BRAND_SCALE = 3  # each listed brand count is multiplied: real ranges carry many brands
MULTIPACK = {
    "beverages": (1, 6, 24),
    "snacks": (1, 6),
    "tins": (1, 6, 12),
    "personal": (1, 3),
    "household": (1, 2),
    "pets": (1, 4),
    "dairy": (1, 6),
    "pantry": (1, 2),
}
TIERS = {"premium": (1.25, 1.6), "standard": (0.95, 1.15), "value": (0.72, 0.9)}


def brand_tier(brand: str) -> str:
    r = u("tier", brand)
    return "premium" if r < 0.2 else ("value" if r > 0.7 else "standard")


@dataclass(frozen=True)
class GenProduct:
    code: str
    brand: str
    name: str
    variant: str
    measure: int
    unit: str
    category: str
    ambient: bool
    zero_rated: bool
    price: int  # reference shelf price before chain/branch indices
    tier: str
    popularity: float
    house: str | None = None
    pack: int = 1


def _sized(measure: int, unit: str) -> str:
    if unit == "g":
        return f"{measure // 1000}kg" if measure >= 1000 and measure % 1000 == 0 else f"{measure}g"
    if unit == "ml":
        return f"{measure / 1000:g}L" if measure >= 1000 else f"{measure}ml"
    return f"{measure}s" if measure > 1 else ""


def generate_universe() -> list[GenProduct]:
    """All canonical products, deterministic for a given taxonomy."""
    out: list[GenProduct] = []
    for code, name, cat, unit, sizes, ref, variants, n_brands, ambient, zero in TYPES:
        start = int(u("brands", code) * len(BRANDS))
        count = min(len(BRANDS) // 7, n_brands * BRAND_SCALE)
        brands = [BRANDS[(start + 7 * i) % len(BRANDS)] for i in range(count)]
        packs = MULTIPACK.get(cat, (1,))
        for brand in brands:
            tier = brand_tier(brand)
            lo, hi = TIERS[tier]
            mult = lo + (hi - lo) * u("bm", brand, code)
            for v in variants:
                for size_i, size in enumerate(sizes):
                    for pack in packs:
                        if pack > 1 and u("mp", brand, code, v, size, pack) < 0.5:
                            continue  # not every line comes in every multipack
                        c = f"{code}|{brand}|{v}|{size}|{pack}"
                        price = (
                            ref * (size / sizes[0]) ** 0.88 * mult * (0.95 + 0.1 * u("v", c))
                            * pack * (0.92 if pack > 1 else 1)
                        )  # fmt: skip
                        mid = 1 - abs(size_i - (len(sizes) - 1) / 2) / max(1, len(sizes))
                        pop = (
                            u("pop", c) * (1.3 if tier == "value" else 1.0) * (0.6 + 0.4 * mid)
                            * (1 if pack == 1 else 0.7)
                        )  # fmt: skip
                        out.append(
                            GenProduct(
                                c,
                                brand,
                                name,
                                v,
                                size,
                                unit,
                                cat,
                                ambient,
                                zero,
                                _round(price),
                                tier,
                                pop,
                                None,
                                pack,
                            )  # fmt: skip
                        )
        for house in HOUSE_BRANDS:
            for v in variants:
                for size in sizes:
                    c = f"{code}|{house}|{v}|{size}"
                    price = ref * (size / sizes[0]) ** 0.88 * 0.8
                    out.append(
                        GenProduct(
                            c,
                            house,
                            name,
                            v,
                            size,
                            unit,
                            cat,
                            ambient,
                            zero,
                            _round(price),
                            "house",
                            u("pop", c),
                            house,
                        )  # fmt: skip
                    )
    for code, name, cat, kinds, finishes, ref in FURNITURE:
        start = int(u("fbrands", code) * len(FURNITURE_BRANDS))
        n = 6 + int(u("fn", code) * 7)
        for i in range(n):
            brand = FURNITURE_BRANDS[(start + 3 * i) % len(FURNITURE_BRANDS)]
            mult = 0.7 + 0.8 * u("fm", brand, code)
            for ki, kind in enumerate(kinds):
                for finish in finishes:
                    for line in ("", "classic", "premium"):
                        c = f"{code}|{brand}|{kind}|{finish}|{line}"
                        variant = " ".join(x for x in (kind, finish, line) if x)
                        price = ref * (1 + 0.25 * ki) * mult * (1.4 if line == "premium" else 1)
                        out.append(
                            GenProduct(
                                c,
                                brand,
                                name,
                                variant,
                                1,
                                "each",
                                cat,
                                True,
                                False,
                                _round(price),
                                "furniture",
                                u("pop", c),
                            )  # fmt: skip
                        )
    return out


def _round(cents: float) -> int:
    return max(1, round(cents / 100)) * 100 - 1


# --- Merchants -----------------------------------------------------------------------

HOUSE_BRANDS = ["Ubuntu Value", "Zest Select", "Fairbasket Essentials"]


@dataclass(frozen=True)
class Branch:
    code: str
    name: str
    zones: tuple[str, ...]


@dataclass(frozen=True)
class Latency:
    mean_ms: int
    jitter_ms: int
    slow_permille: int
    slow_ms: int
    timeout_ms: int = 6000


@dataclass(frozen=True)
class Chain:
    code: str
    name: str
    story: str
    range_size: int
    branches: tuple[Branch, ...]
    coverage: float
    price_index: float
    minimum_order_minor: int
    fee_minor: int
    pick_minutes: int
    first_slot_minutes: int
    slot_minutes: int
    slot_capacity: int
    latency: Latency
    risk_tier: str = "standard"
    onboarded_days_ago: int = 900
    house: str | None = None
    furniture: bool = False
    tier_bias: dict[str, float] = field(default_factory=dict)
    free_over_minor: int | None = None


GP = tuple(z for z in ALL_ZONES if z.startswith("gp-"))
WC = tuple(z for z in ALL_ZONES if z.startswith("wc-"))
KZN_EC = tuple(z for z in ALL_ZONES if z.startswith(("kzn-", "ec-")))

CHAINS = [
    Chain(
        "ubuntu",
        "Ubuntu Hypermarket (Fictional)",
        "~50 000 lines; the integration is slow and sometimes times out",
        50_000,
        (
            Branch("ubh-soweto", "Ubuntu Hyper Soweto", ("gp-soweto",)),
            Branch(
                "ubh-midrand", "Ubuntu Hyper Midrand", ("gp-midrand", "gp-sandton", "gp-tembisa")
            ),
            Branch("ubh-menlyn", "Ubuntu Hyper Menlyn", ("gp-pretoria-east",)),
            Branch("ubh-bellville", "Ubuntu Hyper Bellville", WC),
            Branch("ubh-pinetown", "Ubuntu Hyper Pinetown", ("kzn-umhlanga", "kzn-umlazi")),
            Branch("ubh-gqeberha", "Ubuntu Hyper Gqeberha", ("ec-gqeberha",)),
        ),
        0.96,
        0.97,
        0,
        4500,
        5,
        8,
        5,
        10,
        Latency(mean_ms=2500, jitter_ms=1500, slow_permille=150, slow_ms=9000),
        house="Ubuntu Value",
        free_over_minor=70000,
    ),
    Chain(
        "zest",
        "Zest Express (Fictional)",
        "~20 000 lines; answers instantly, but its couriers are often late",
        20_000,
        (
            Branch("zx-sandton", "Zest Express Sandton", ("gp-sandton",)),
            Branch("zx-soweto", "Zest Express Soweto", ("gp-soweto",)),
            Branch("zx-menlyn", "Zest Express Pretoria East", ("gp-pretoria-east",)),
            Branch("zx-midrand", "Zest Express Midrand", ("gp-midrand", "gp-tembisa")),
            Branch("zx-citybowl", "Zest Express City Bowl", ("wc-city-bowl",)),
            Branch("zx-bellville", "Zest Express Bellville", ("wc-bellville", "wc-khayelitsha")),
            Branch("zx-umhlanga", "Zest Express Umhlanga", ("kzn-umhlanga",)),
        ),
        0.94,
        1.07,
        0,
        3500,
        2,
        4,
        5,
        8,
        Latency(mean_ms=60, jitter_ms=40, slow_permille=0, slow_ms=0),
        house="Zest Select",
        tier_bias={"premium": 1.4, "value": 0.8},
        free_over_minor=45000,
    ),
    Chain(
        "fairbasket",
        "Fairbasket Supermarkets (Fictional)",
        "~18 000 lines; an ordinary, well-behaved store",
        18_000,
        (
            Branch("fb-rosebank", "Fairbasket Rosebank", ("gp-sandton", "gp-midrand")),
            Branch("fb-jabulani", "Fairbasket Jabulani", ("gp-soweto",)),
            Branch("fb-hatfield", "Fairbasket Hatfield", ("gp-pretoria-east",)),
            Branch("fb-tembisa", "Fairbasket Tembisa", ("gp-tembisa",)),
            Branch("fb-claremont", "Fairbasket Claremont", ("wc-city-bowl", "wc-bellville")),
            Branch("fb-gateway", "Fairbasket Gateway", ("kzn-umhlanga", "kzn-umlazi")),
            Branch("fb-walmer", "Fairbasket Walmer", ("ec-gqeberha",)),
        ),
        0.95,
        1.0,
        0,
        5000,
        4,
        6,
        5,
        8,
        Latency(mean_ms=300, jitter_ms=200, slow_permille=30, slow_ms=4000),
        house="Fairbasket Essentials",
        free_over_minor=60000,
    ),
    Chain(
        "kaya",
        "Kaya Living (Fictional)",
        "furniture and appliances; new to the platform, legitimate, multi-day delivery",
        2_600,
        (
            Branch("kaya-gp", "Kaya Living Gauteng DC", GP),
            Branch("kaya-wc", "Kaya Living Cape DC", WC),
            Branch("kaya-kzn", "Kaya Living Durban DC", KZN_EC),
        ),
        0.97,
        1.0,
        50000,
        35000,
        15,
        20,
        10,
        3,
        Latency(mean_ms=400, jitter_ms=200, slow_permille=0, slow_ms=0),
        risk_tier="probation",
        onboarded_days_ago=6,
        furniture=True,
        free_over_minor=1000000,
    ),
    Chain(
        "bargainbox",
        "BargainBox Direct (Fictional)",
        "SCAM: onboarded with forged company documents; prices too good to be true; "
        "accepts every order and never hands anything to a courier",
        760,
        (Branch("bbx-national", "BargainBox National Warehouse", ALL_ZONES),),
        1.0,
        0.74,
        0,
        2500,
        2,
        4,
        5,
        50,
        Latency(mean_ms=40, jitter_ms=20, slow_permille=0, slow_ms=0),
        risk_tier="probation",
        onboarded_days_ago=3,
    ),
]
SCAM_CHAINS = {"bargainbox"}


def ranges(universe: list[GenProduct]) -> dict[str, list[GenProduct]]:
    """Which canonical products each chain carries."""
    national = [p for p in universe if p.house is None and p.tier != "furniture"]
    out: dict[str, list[GenProduct]] = {}
    for chain in CHAINS:
        if chain.furniture:
            out[chain.code] = [p for p in universe if p.tier == "furniture"][: chain.range_size]
            continue
        if chain.code in SCAM_CHAINS:
            # The most popular national lines plus big-ticket items people resell.
            top = sorted(national, key=lambda p: -p.popularity)
            big = [
                p
                for p in universe
                if p.category in ("electronics", "appliances") and p.house is None
            ]
            big += [p for p in universe if p.tier == "furniture" and u("bbx", p.code) < 0.02]
            picks = top[:700] + sorted(big, key=lambda p: -p.popularity)[:60]
            out[chain.code] = list({p.code: p for p in picks}.values())
            continue
        house = [p for p in universe if p.house == chain.house]
        bias = chain.tier_bias
        ranked = sorted(
            national,
            key=lambda p: (
                -(p.popularity * bias.get(p.tier, 1.0) * (0.85 + 0.3 * u(chain.code, p.code)))
            ),
        )
        out[chain.code] = house + ranked[: chain.range_size - len(house)]
    return out


def chain_price(chain: Chain, branch: Branch, p: GenProduct) -> int:
    noise = 0.95 + 0.1 * u("bp", branch.code, p.code)
    return _round(p.price * chain.price_index * noise)


def chain_stock(chain: Chain, branch: Branch, p: GenProduct) -> int:
    r = u("st", branch.code, p.code)
    if chain.furniture:
        return 0 if r < 0.05 else 1 + int(r * 8)
    if chain.code in SCAM_CHAINS:
        return 999  # "always in stock"
    if p.price > 100000:
        return 0 if r < 0.1 else 1 + int(r * 6)
    return 0 if r < 0.04 else (2 if r < 0.12 else 6 + int(r * 100))


# --- Seeding -------------------------------------------------------------------------


def seed_bigmarket(session: Session, *, now: datetime) -> dict[str, object]:
    """Create the universe, merchants and offers once; refresh slots on every call."""
    universe = generate_universe()
    first = universe[0]
    created = session.get(Product, pid(first.code)) is None
    by_chain = ranges(universe)
    if created:
        _copy_products(session, universe)
    for chain in CHAINS:
        mid = uuid.uuid5(NS, f"merchant:{chain.code}")
        _ensure(
            session,
            Merchant,
            mid,
            id=mid,
            code=chain.code,
            display_name=chain.name,
            legal_name=f"{chain.name} (synthetic entity)",
            state=MerchantState.PAYMENT_ENABLED,
            payout_destination_version=f"sim-payout-{chain.code}-v1",
            risk_tier=chain.risk_tier,
            onboarded_at=now - timedelta(days=chain.onboarded_days_ago),
        )
        for branch in chain.branches:
            lid = uuid.uuid5(NS, f"location:{branch.code}")
            loc_new = session.get(MerchantLocation, lid) is None
            _ensure(
                session,
                MerchantLocation,
                lid,
                id=lid,
                merchant_id=mid,
                code=branch.code,
                name=f"{branch.name} (Fictional)",
                service_zones=list(branch.zones),
                minimum_order_minor=chain.minimum_order_minor,
                pick_minutes=chain.pick_minutes,
            )
            if loc_new:
                session.add(
                    MerchantCapability(
                        location_id=lid, version=1, can_reserve=True, can_commit=True,
                        can_cancel=True, can_lookup_by_reference=True,
                        reservation_ttl_seconds=1800,
                        evidence="synthetic merchant simulator; not evidence of any real merchant",
                    )
                )  # fmt: skip
                session.add(SimMerchantLatency(location_id=lid, **vars(chain.latency)))
                session.flush()
        if created:
            _copy_offers(session, chain, mid, by_chain[chain.code], now)
    session.flush()
    for chain in CHAINS:
        for branch in chain.branches:
            _slots(session, chain, branch, now)
    if created:
        _promotions(session, by_chain, now)
    session.flush()
    return {
        "products": len(universe),
        "ranges": {c: len(v) for c, v in by_chain.items()},
        "created": created,
    }


def _copy(session: Session, table: str, columns: list[str], rows) -> None:
    conn = session.connection().connection.driver_connection
    with conn.cursor() as cur, cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as cp:
        for row in rows:
            cp.write_row(row)


def _copy_products(session: Session, universe: list[GenProduct]) -> None:
    def rows():
        for i, p in enumerate(universe):
            yield (
                pid(p.code), gtin13(f"22{i:010d}"), p.brand, p.name,
                " ".join(
                    x
                    for x in (p.variant, _sized(p.measure, p.unit), f"{p.pack}-pack" if p.pack > 1 else "")
                    if x
                ),
                p.measure, p.unit, p.pack, p.category, p.ambient, False,
            )  # fmt: skip

    session.flush()
    _copy(
        session,
        "products",
        ["id", "gtin", "brand", "name", "variant", "unit_measure", "unit", "pack_count",
         "category", "ambient", "regulated"],
        rows(),
    )  # fmt: skip


def _copy_offers(session, chain: Chain, merchant_id, products: list[GenProduct], now) -> None:
    def mappings():
        for p in products:
            yield (uuid.uuid4(), merchant_id, _sku(chain, p), pid(p.code), 1,
                   "gtin_verified", "synthetic GTIN match", True)  # fmt: skip

    _copy(
        session,
        "product_mappings",
        ["id", "merchant_id", "merchant_sku", "product_id", "revision", "match_level",
         "evidence", "active"],
        mappings(),
    )  # fmt: skip

    def offers():
        for branch in chain.branches:
            lid = uuid.uuid5(NS, f"location:{branch.code}")
            for p in products:
                if u("cov", branch.code, p.code) >= chain.coverage:
                    continue
                stock = chain_stock(chain, branch, p)
                yield (
                    uuid.uuid4(), lid, pid(p.code), _sku(chain, p), chain_price(chain, branch, p),
                    "zero_rated" if p.zero_rated else "standard", stock,
                    "observed" if stock > 2 else "low", now - timedelta(minutes=5),
                    now + timedelta(days=2), f"{p.brand} {p.name} (synthetic listing)",
                )  # fmt: skip

    _copy(
        session,
        "offer_versions",
        ["id", "location_id", "product_id", "merchant_sku", "price_minor", "tax_code",
         "stock_quantity", "stock_confidence", "observed_at", "valid_until", "description"],
        offers(),
    )  # fmt: skip


def _sku(chain: Chain, p: GenProduct) -> str:
    return f"{chain.code.upper()}-{hashlib.sha1(p.code.encode()).hexdigest()[:12]}"


def _slots(session: Session, chain: Chain, branch: Branch, now: datetime) -> None:
    lid = uuid.uuid5(NS, f"location:{branch.code}")
    for zone in branch.zones:
        spare = session.scalar(
            select(func.coalesce(func.sum(DeliverySlot.capacity - DeliverySlot.booked), 0)).where(
                DeliverySlot.location_id == lid,
                DeliverySlot.zone == zone,
                DeliverySlot.starts_at > now + timedelta(minutes=chain.pick_minutes + 5),
            )
        )
        if spare >= chain.slot_capacity * 4:
            continue
        surcharge = 0 if zone == branch.zones[0] else 1000
        for i in range(16):
            start = now + timedelta(minutes=chain.first_slot_minutes + chain.slot_minutes * i)
            session.add(
                DeliverySlot(
                    location_id=lid, courier_code=COURIER, zone=zone, starts_at=start,
                    ends_at=start + timedelta(minutes=chain.slot_minutes),
                    fee_minor=chain.fee_minor + surcharge, capacity=chain.slot_capacity,
                )
            )  # fmt: skip


def _promotions(session: Session, by_chain: dict[str, list[GenProduct]], now: datetime) -> None:
    window = {"valid_from": now - timedelta(days=1), "valid_until": now + timedelta(days=7)}
    for chain in CHAINS:
        popular = sorted(by_chain[chain.code], key=lambda p: -p.popularity)[:40]
        for branch in chain.branches:
            lid = uuid.uuid5(NS, f"location:{branch.code}")
            if chain.free_over_minor:
                session.add(
                    Promotion(location_id=lid, kind=PromotionKind.DELIVERY_THRESHOLD,
                              min_spend_minor=chain.free_over_minor, **window)
                )  # fmt: skip
            for i, p in enumerate(popular[:12]):
                kind = i % 2
                if kind == 0:
                    session.add(
                        Promotion(location_id=lid, kind=PromotionKind.PERCENT_LINE,
                                  product_ids=[pid(p.code)], percent_bp=1000 + 500 * (i % 3), **window)
                    )  # fmt: skip
                else:
                    price = chain_price(chain, branch, p)
                    session.add(
                        Promotion(location_id=lid, kind=PromotionKind.MULTIBUY,
                                  product_ids=[pid(p.code)], min_quantity=3,
                                  bundle_price_minor=_round(price * 3 * 0.85), **window)
                    )  # fmt: skip


def location_id(branch_code: str) -> uuid.UUID:
    return uuid.uuid5(NS, f"location:{branch_code}")


def merchant_id(chain_code: str) -> uuid.UUID:
    return uuid.uuid5(NS, f"merchant:{chain_code}")
