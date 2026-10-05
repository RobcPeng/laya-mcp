"""The invented world every Ridgeback row is written in: people, homes, places, and surface variation.

Every name, household, street, town, email, and phone number here is made up. Emails use the reserved
example.com/.net/.org domains and phone numbers the 555-01xx range. Coordinates are random points in
open country, generated per row, and tied to nobody.
"""
import random

ADULTS = ["Nadia", "Marcus", "Priya", "Owen", "Ines", "Rafael", "Hana", "Silas", "Dev", "Lena", "Mateo",
          "Ruth", "Kofi", "Ada", "Felix", "Noor", "Wren", "Imani", "Bram", "Tomas", "Esme", "Jonah",
          "Mira", "Ezra", "Lucia", "Arlo", "Greta", "Idris", "Sunny", "Viktor"]
KIDS = ["Theo", "Juniper", "Milo", "Ivy", "Ollie", "Pip", "Remy", "Tess", "Kit", "Bea", "Nico", "Lark",
        "Rosa", "Finn", "Zuri", "Otto"]
SURNAMES = ["Okafor", "Lindqvist", "Varga", "Hollis", "Brennan", "Delgado", "Achterberg", "Moreau",
            "Castellano", "Ivanova", "Takeda", "Mbeki", "Sorensen", "Quill", "Ferreira"]
KIN = ["Mom", "Dad", "Grandma", "Grandpa", "Nana", "Papa", "Auntie Lu", "Uncle Ray", "my brother",
       "my sister", "my stepdad", "Granny Jo"]
HOMES = ["Hollis house", "the Varga home", "Maple Street", "the Okafor-Lindqvist house", "Brennan family",
         "the apartment", "Quill house", "Casa Delgado"]
OTHER_HOMES_OWN = ["the Cabin", "the lake house", "Grandma's house", "Dad's apartment", "the beach place"]
OTHER_HOUSEHOLDS = ["the Hendersons", "the Achterbergs next door", "the Moreau family", "my ex's new household",
                    "the neighbors", "the family across the street", "the Takedas", "the Sorensen house",
                    "the people in apartment 4B", "my coworker's family", "the Castellanos"]
TOWNS = ["Alder Creek", "Pinehollow", "Marrow Bay", "Westbrook Falls", "Cedar Hollow", "Fernvale", "Ashby",
         "Kettle Rock", "Silverlake Bend", "Oakmere"]
STREETS = ["Larkspur Lane", "Quarry Road", "Birchwood Ave", "Mill Street", "Heron Way", "Juniper Court",
           "Orchard Row", "Tanner Street", "Lantern Hill Rd", "Wicker Lane"]
STORES = ["Costco", "Trader Joe's", "the farmers market", "Target", "the corner store", "Aldi", "Whole Foods",
          "the co-op", "Safeway", "Home Depot"]
ROLES_ADULT = ["Creator", "Manager", "Member", "Member", "Member", "Guest", "Viewer"]
ROLES_KID = ["Member", "Member", "Guest", "Viewer"]

GROCERIES = ["milk", "eggs", "oat milk", "bananas", "bread", "coffee beans", "paper towels", "dish soap",
             "chicken thighs", "rice", "apples", "yogurt", "butter", "tortillas", "cereal", "spinach",
             "olive oil", "cat food", "diapers", "lemons", "frozen peas", "peanut butter", "toilet paper",
             "basil", "salmon", "cheddar", "AA batteries", "trash bags", "honey", "garlic"]
LISTS = ["packing list", "Costco list", "to-do list", "birthday wishlist", "hardware store list",
         "camping list", "chores list", "gift ideas", "school supplies", "Christmas list", "garden list",
         "books to read"]
EVENTS = ["dentist", "soccer practice", "parent-teacher conference", "piano lesson", "Grandma's birthday dinner",
          "vet appointment", "book club", "haircut", "date night", "swim meet", "school play", "car service",
          "flu shots", "game night", "orthodontist", "playdate with the Takedas"]
DAYS = ["tomorrow", "Friday", "next Tuesday", "Saturday morning", "on the 14th", "this Sunday", "Monday at 4",
        "Thursday at 6pm", "next week", "tonight at 7", "Wednesday at 3:30", "the 22nd at noon"]
RECIPES = ["lasagna", "Grandma's chili", "banana bread", "pad thai", "the lemon chicken", "overnight oats",
           "shakshuka", "mac and cheese", "vegetable curry", "fish tacos", "minestrone", "pancakes"]
TRIPS = ["the Fernvale camping trip", "Marrow Bay beach week", "the road trip to Kettle Rock",
         "spring break", "the ski weekend", "Grandma's for Thanksgiving", "the Oakmere reunion"]
PETS = [("Biscuit", "dog"), ("Pepper", "cat"), ("Mango", "parrot"), ("Waffles", "dog"), ("Nimbus", "rabbit"),
        ("Toast", "guinea pig"), ("Juno", "cat"), ("Rocket", "dog")]
MOVIES = ["Dune: Part Two", "Paddington 2", "the new Pixar one", "Spirited Away", "The Bear", "Severance",
          "Bluey", "The Princess Bride", "Arrival", "Shrinking", "Inside Out 2", "The Great British Bake Off",
          "Only Murders in the Building", "Wallace and Gromit", "Andor"]
PLACES = ["the library", "the aquarium", "the science museum", "Kettle Rock trailhead", "the climbing gym",
          "Rosie's Diner", "the botanical garden", "the ice rink", "Lantern Hill park", "the pumpkin patch",
          "Marrow Bay pier", "the zoo"]

EMAIL_DOMAINS = ["example.com", "example.net", "example.org"]


def pick(rng, xs):
    return xs[rng.randrange(len(xs))]


def fill(rng, template, slots):
    out = template
    for k, vals in slots.items():
        while "{" + k + "}" in out:
            out = out.replace("{" + k + "}", str(pick(rng, vals)), 1)
    return out


def email(rng, who=None):
    who = (who or pick(rng, ADULTS + SURNAMES)).lower().replace(" ", ".")
    return f"{who}{rng.randint(1, 99)}@{pick(rng, EMAIL_DOMAINS)}"


def phone(rng):
    return f"555-01{rng.randint(0, 99):02d}"


def coords(rng):
    # open country, random to four decimals; no town, no person
    lat = round(rng.uniform(43.0, 47.5), 4)
    lon = round(rng.uniform(-112.0, -100.5), 4)
    return lat, lon


def address(rng):
    return f"{rng.randint(10, 990)} {pick(rng, STREETS)}, {pick(rng, TOWNS)}"


def uuid(rng):
    h = "".join(pick(rng, "0123456789abcdef") for _ in range(32))
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


BASE_SLOTS = {
    "adult": ADULTS, "kid": KIDS, "kin": KIN, "item": GROCERIES, "list": LISTS, "event": EVENTS,
    "day": DAYS, "recipe": RECIPES, "trip": TRIPS, "town": TOWNS, "store": STORES, "street": STREETS,
    "place": PLACES, "movie": MOVIES, "home_other": OTHER_HOMES_OWN, "other_hh": OTHER_HOUSEHOLDS,
    "surname": SURNAMES, "pet": [p for p, _ in PETS], "n": ["2", "3", "4", "5", "6", "10", "12"],
}

# Surface variation. Household chat is short, lowercase, typo-ridden, and sometimes voice-dictated.
OPENERS = ["", "", "", "", "hey bobby ", "bobby, ", "Bobby can you ", "hey, ", "ok so ", "quick q: ",
           "um ", "yo bobby ", "hi! ", "@bobby "]
CLOSERS = ["", "", "", "", "?", " please", " thx", " thanks!", " pls", " 🙏", " lol", " asap", "!!", " :)"]


def typo(rng, text, p=0.18):
    """One or two keyboard slips in longer words, with probability p."""
    if rng.random() >= p:
        return text
    words = text.split(" ")
    for _ in range(rng.choice([1, 1, 2])):
        idx = [i for i, w in enumerate(words) if len(w) > 4 and w.isalpha()]
        if not idx:
            break
        i = rng.choice(idx)
        w = list(words[i])
        j = rng.randrange(1, len(w) - 1)
        op = rng.random()
        if op < 0.4:
            w[j], w[j + 1] = w[j + 1], w[j]
        elif op < 0.7:
            del w[j]
        else:
            w.insert(j, w[j])
        words[i] = "".join(w)
    return " ".join(words)


def vary(rng, text, openers=True):
    t = text
    if openers:
        o = pick(rng, OPENERS)
        if o and o.endswith("can you ") and not t.lower().startswith(("what", "how", "is", "are", "do")):
            t = o + t[:1].lower() + t[1:]
        elif o and not o.endswith("can you "):
            t = o + t
        t = t + pick(rng, CLOSERS)
    r = rng.random()
    if r < 0.2:
        t = t.lower()
    elif r < 0.25:
        t = t.upper() if len(t) < 40 else t
    return typo(rng, t)


def asker(rng, safe, role=None, name=None, homes=False):
    """The `asker` field: who is speaking, their seat, and whether safe mode is on."""
    if safe:
        name = name or pick(rng, KIDS)
        role = role or pick(rng, ROLES_KID)
        s = f"{name}, age {rng.randint(6, 15)}, {role} seat; safe mode is ON (a child)"
    else:
        name = name or pick(rng, ADULTS)
        role = role or pick(rng, ROLES_ADULT)
        age = pick(rng, ["adult", "adult", "adult", "age 16", "age 17", "adult (grandparent)"])
        s = f"{name}, {age}, {role} seat; safe mode is off"
    if homes:
        here = pick(rng, HOMES)
        extra = pick(rng, [[], [], [pick(rng, OTHER_HOMES_OWN)]])
        s += f"; member of {here} (this home)" + "".join(f" and {h}" for h in extra)
    return s


NO_CONTEXT = "(none)"


def context_line(rng, speaker, said, bobby):
    return f"Earlier in the thread. {speaker}: {said} / Bobby: {bobby}"
