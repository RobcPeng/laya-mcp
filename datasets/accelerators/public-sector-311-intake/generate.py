"""Generate the public-sector-311-intake accelerator set (deterministic, stdlib only).

Each phrasing family is a hand-written core description of one kind of 311 request, with slots for
location, detail, duration, and caller voice. Families carry their own gold labels (service, emergency,
priority); the location slot decides location_present. Channel wrappers (web form, phone transcript,
app, email, text, social DM) and a noise pass add realistic mess. TEST holds out whole families.

    python datasets/accelerators/public-sector-311-intake/generate.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import _common as C  # noqa: E402

NAME = "public-sector-311-intake"
PREFIX = "311"
PER_FAMILY = 18
SEED = 311

LANDMARKS = ["Lincoln Elementary", "the public library on Main", "Riverside Park", "the rec center on Oak",
             "Washington Middle School", "the bus stop outside City Hall", "Memorial Hospital's east entrance",
             "the light rail station on 2nd", "Cottonwood Trailhead", "the senior center on Birch",
             "the community garden on Mill St", "Fire Station 4", "the county courthouse",
             "the dog park at Juniper and 4th", "Centennial High School", "the Safeway lot on Ridge Rd"]
VAGUE = ["near my house", "on my street", "in my neighborhood", "by where I live", "around the corner from me",
         "somewhere downtown", "on the road I take to work", "out front", "down the block from me",
         "near the school", "by the park", "on the main road", "at the usual spot", "here"]


def loc_concrete(rng):
    r = rng.random()
    if r < 0.35:
        return f"at {C.address(rng)}"
    if r < 0.65:
        return f"at {C.intersection(rng)}"
    if r < 0.85:
        return f"{C.pick(rng, ['near', 'in front of', 'across from', 'behind', 'next to'])} {C.pick(rng, LANDMARKS)}"
    return f"on the {rng.randrange(1, 49) * 100} block of {C.pick(rng, C.STREETS)}"


SLOTS = {
    "dur": ["for two weeks", "since last Tuesday", "for about a month", "since the storm", "for days now",
            "for 3 weeks", "since Monday", "all week", "for a while", "since before Thanksgiving",
            "for over a month", "again"],
    "please": ["Please fix.", "Can someone come out?", "Please send someone.", "Thanks.", "Thank you!",
               "Hoping this gets taken care of soon.", "Appreciate it.", "", "", "pls fix", "thx"],
    "again": ["", "", "This is my second report.", "I already called about this once.",
              "Third time reporting this!!", "Ticket from last month was closed but nothing happened."],
    "time": ["every night", "last night", "right now", "since 11pm", "most weekends", "every morning at 5am",
             "until 2am on weeknights", "all afternoon"],
}

# Each family: (service, family id, emergency, priority, [templates]). {loc} is the location slot.
FAMILIES = [
    # ---------------------------------------------------------------- pothole
    ("pothole", "pothole/basic", False, 1, [
        "There is a pothole {loc} {dur}. {please}",
        "Big pothole {loc}. {again} {please}",
        "Reporting a pothole in the right lane {loc}. It's about a foot across. {please}",
    ]),
    ("pothole", "pothole/damage", False, 2, [
        "The pothole {loc} blew out my tire this morning, and I watched two other cars hit it. Someone is going to get hurt. {please}",
        "Huge hole in the road {loc}, cyclists are swerving into traffic to avoid it. {again}",
        "Deep pothole {loc} filled with water so you can't see it. My rim is bent. {please}",
    ]),
    ("pothole", "pothole/pavement", False, 1, [
        "Pavement is crumbling and sunken {loc} {dur}. {please}",
        "The asphalt patch {loc} has sunk again and there's a dip that jolts every car. {please}",
        "Road surface is cracked and breaking apart {loc}. Getting worse after every freeze. {please}",
    ]),
    ("pothole", "pothole/minor", False, 0, [
        "Small crack in the road {loc}, not urgent, just wanted it on the list. {please}",
        "Minor surface cracking {loc}. Not a hazard yet but figured I'd report it before winter.",
    ]),
    ("pothole", "pothole/sinkhole-emergency", True, 3, [
        "A sinkhole just opened {loc} and a car fell partly in, the driver is still inside! Send help!",
        "The road just collapsed {loc}, there's a huge hole and a woman fell in and is hurt. Please hurry.",
    ]),
    # ---------------------------------------------------------------- streetlight
    ("streetlight", "streetlight/out", False, 1, [
        "Streetlight {loc} is out {dur}. {please}",
        "The light pole {loc} doesn't come on at night. {again} {please}",
        "Street lamp out {loc}. It's really dark walking home. {please}",
    ]),
    ("streetlight", "streetlight/flicker", False, 0, [
        "The streetlight {loc} flickers on and off all night. {please}",
        "Light {loc} keeps cycling on and off, kind of annoying but not a big deal. {please}",
        "Streetlight {loc} is on during the day and stays on. Wasting power. {please}",
    ]),
    ("streetlight", "streetlight/dark-crossing", False, 2, [
        "Every streetlight {loc} is out and kids cross there to get to school in the dark. Please prioritize.",
        "Whole block is dark {loc}, three lights out in a row. People have almost been hit in the crosswalk. {again}",
    ]),
    ("streetlight", "streetlight/pole-damage", False, 2, [
        "A light pole {loc} is leaning badly after someone hit it, looks like it could fall on the sidewalk. {please}",
        "The access panel on the base of the streetlight {loc} is open and you can see wires. {please}",
    ]),
    ("streetlight", "streetlight/live-wire-emergency", True, 3, [
        "A light pole got knocked over {loc} and the wires are sparking on the sidewalk right now, people are walking by!",
        "Streetlight {loc} fell into the road and there's fire coming from the base, sparks everywhere.",
    ]),
    # ---------------------------------------------------------------- trash
    ("trash", "trash/missed", False, 1, [
        "Our trash wasn't picked up this week {loc}. {please}",
        "Recycling truck skipped us again {loc}. {again} {please}",
        "Missed garbage pickup {loc}, the whole street got skipped. {please}",
    ]),
    ("trash", "trash/bulk", False, 0, [
        "I need to schedule a bulk pickup for an old couch and a mattress {loc}. What do I do?",
        "How do I get rid of a broken fridge? Want a bulk item pickup {loc}.",
    ]),
    ("trash", "trash/dumping", False, 1, [
        "Someone dumped a pile of furniture and bags of trash {loc}. {dur}. {please}",
        "Illegal dumping {loc}, tires and construction debris in the alley. {please}",
        "People keep dumping trash bags {loc} and now there are rats. {again}",
    ]),
    ("trash", "trash/hazardous-dump", False, 2, [
        "Somebody dumped buckets of what smells like paint thinner and old car batteries {loc}, leaking into the gutter. {please}",
        "There are used needles scattered in a pile of dumped trash {loc}, right where kids walk. {please}",
    ]),
    ("trash", "trash/overflowing", False, 1, [
        "The public trash can {loc} is overflowing and garbage is blowing everywhere. {please}",
        "City bins {loc} haven't been emptied {dur}, trash all over the sidewalk. {please}",
    ]),
    ("trash", "trash/dumpster-fire-emergency", True, 3, [
        "The dumpster {loc} is on fire right now and it's spreading toward the building!!",
        "Trash cans {loc} are burning, big flames and black smoke, it's next to parked cars.",
    ]),
    # ---------------------------------------------------------------- noise
    ("noise", "noise/party", False, 0, [
        "Loud party {loc} {time}, music is shaking our windows. {please}",
        "Neighbors {loc} blast music {time}. {again} Can someone do something?",
        "Bass from the house {loc} {time}. We have a newborn. {please}",
    ]),
    ("noise", "noise/construction", False, 1, [
        "Construction crew {loc} starts jackhammering {time}, way before allowed hours. {please}",
        "Contractor {loc} is running generators {time}, is that even allowed? {again}",
    ]),
    ("noise", "noise/barking", False, 0, [
        "Dog {loc} barks nonstop {time}. Owners are never home. {please}",
        "The dogs {loc} bark {time} and nobody can sleep. {again}",
    ]),
    ("noise", "noise/business", False, 1, [
        "The bar {loc} has live music outside {time} past the permit. {please}",
        "Delivery trucks idle and unload {loc} {time}, beeping the whole time. {please}",
    ]),
    ("noise", "noise/violence-emergency", True, 3, [
        "I hear screaming and what sounds like someone being beaten in the apartment {loc} right now. Please send someone!",
        "There are gunshots {loc} right now, I just heard like five of them.",
    ]),
    # ---------------------------------------------------------------- graffiti
    ("graffiti", "graffiti/wall", False, 0, [
        "Graffiti on the wall {loc}. {please}",
        "Someone tagged the side of the building {loc} {dur}. {please}",
        "Spray paint tags all over the fence {loc}. {again}",
    ]),
    ("graffiti", "graffiti/public-property", False, 1, [
        "The stop sign {loc} is spray painted over and you can't read it. {please}",
        "Graffiti covering the bus shelter and the utility boxes {loc}. {please}",
        "The underpass mural {loc} got tagged over. {please}",
    ]),
    ("graffiti", "graffiti/offensive", False, 2, [
        "Someone painted hateful symbols and slurs on the playground wall {loc}. Kids are seeing this. Please remove ASAP.",
        "Offensive graffiti with threats toward a family was painted on the sidewalk {loc}. {please}",
    ]),
    ("graffiti", "graffiti/in-progress-emergency", True, 3, [
        "Group of guys spray painting cars {loc} right now and they just smashed a window with a bat.",
        "People are breaking into the store {loc} right now, they spray painted the cameras first.",
    ]),
    # ---------------------------------------------------------------- water
    ("water", "water/leak", False, 1, [
        "Water is bubbling up from the ground {loc} {dur}. {please}",
        "There's a leak coming from the water meter {loc}, sidewalk is always wet. {please}",
        "Clean water running down the gutter {loc} {dur}, no rain. Probably a leak. {please}",
    ]),
    ("water", "water/main-break", False, 2, [
        "Water main break {loc}, the street is flooding and water is heading into garages. {please}",
        "Major water gushing out of the road {loc}, it's like a river. {please}",
    ]),
    ("water", "water/pressure", False, 1, [
        "Almost no water pressure in our house {loc} since this morning. Neighbors too. {please}",
        "Tap water is brown and smells weird {loc}. Is it safe? {please}",
    ]),
    ("water", "water/hydrant", False, 1, [
        "Fire hydrant {loc} is leaking steadily. {please}",
        "Someone opened the fire hydrant {loc} and it's just running. {please}",
        "The hydrant {loc} got hit by a car and is tilted, not leaking though. {please}",
    ]),
    ("water", "water/sewer", False, 2, [
        "Sewer is backing up into our basement {loc}, smells awful. {please}",
        "Storm drain {loc} is clogged and the intersection floods every time it rains. {again}",
    ]),
    # ---------------------------------------------------------------- animal
    ("animal", "animal/dead", False, 1, [
        "Dead deer in the road {loc}. {please}",
        "There's a dead raccoon {loc} {dur}, it smells. {please}",
        "Dead cat on the side of the road {loc}. {please}",
    ]),
    ("animal", "animal/stray", False, 1, [
        "Stray dog wandering {loc}, no collar, seems friendly. {please}",
        "Loose cats keep getting into our yard {loc}. {again}",
    ]),
    ("animal", "animal/aggressive", False, 2, [
        "A big dog is running loose {loc} and lunging at people walking by. Kids are about to walk home from school.",
        "Coyote hanging around {loc} during the day, it doesn't run from people and got close to a stroller. {please}",
    ]),
    ("animal", "animal/wildlife", False, 0, [
        "Raccoons living under our deck {loc}, can the city relocate them?",
        "There's a bird's nest in the traffic light {loc}. Just curious if someone checks these. {please}",
        "Bees swarming in a tree {loc}. {please}",
    ]),
    ("animal", "animal/attack-emergency", True, 3, [
        "A dog is attacking a child {loc} right now, the kid is bleeding, please send help!",
        "Pit bull just bit my neighbor {loc} and he's bleeding badly, dog is still loose.",
    ]),
    # ---------------------------------------------------------------- parking
    ("parking", "parking/abandoned", False, 0, [
        "Abandoned car parked {loc} {dur}, flat tires, no plates. {please}",
        "There's a van {loc} that hasn't moved {dur}. {again}",
        "Junk car with expired tags sitting {loc}. {please}",
    ]),
    ("parking", "parking/blocking", False, 1, [
        "Someone is parked across my driveway {loc} and I can't get out for work. {please}",
        "Car parked in the bike lane {loc} every day. {again}",
        "Truck blocking the alley {loc}, garbage truck can't get through. {please}",
    ]),
    ("parking", "parking/safety", False, 2, [
        "Cars keep parking in front of the fire hydrant and in the fire lane {loc}. An ambulance couldn't get through yesterday.",
        "SUV parked on the corner {loc} blocking the view of the crosswalk, kids crossing can't be seen. {please}",
    ]),
    ("parking", "parking/crash-emergency", True, 3, [
        "A car just crashed into the parked cars {loc} and the driver isn't moving. Hurry!",
        "Someone parked car rolled into the intersection {loc} and hit a pedestrian, she's on the ground.",
    ]),
    # ---------------------------------------------------------------- other
    ("other", "other/tree", False, 2, [
        "Large tree branch fell and is blocking the road {loc}. {please}",
        "Tree limb hanging over the sidewalk {loc} looks like it will fall any time. {please}",
    ]),
    ("other", "other/sidewalk-sign", False, 1, [
        "Sidewalk is heaved up {loc}, my mother tripped. {please}",
        "The stop sign {loc} is knocked down. {please}",
        "Traffic signal {loc} is stuck on red in every direction. {please}",
    ]),
    ("other", "other/info", False, 0, [
        "What are the hours for the recycling drop-off center? Also is it open on holidays?",
        "How do I sign up for the city's alert texts? I live {loc}.",
        "Can I get a permit for a block party {loc} next month?",
    ]),
    ("other", "other/snow-weeds", False, 1, [
        "The sidewalk {loc} hasn't been shoveled {dur} and it's solid ice. {please}",
        "Weeds are waist high on the vacant lot {loc}. {again}",
        "Snow plow left a wall of snow blocking the bus stop {loc}. {please}",
    ]),
    ("other", "other/gas-emergency", True, 3, [
        "Strong smell of gas {loc}, I can hear hissing from the meter. Evacuating now.",
        "It smells like natural gas all over the block {loc}, getting stronger. Neighbor is dizzy.",
    ]),
    ("other", "other/fire-emergency", True, 3, [
        "House {loc} is on fire, smoke coming out of the roof, I don't know if anyone is inside!",
        "Brush fire started {loc} next to the homes, wind is pushing it!",
    ]),
]

# Near-miss families: emergency vocabulary, but not an emergency (hard negatives for `emergency`).
NEAR_MISS = [
    ("water", "nearmiss/hydrant-word", False, 1, [
        "The fire hydrant {loc} is painted a weird color and leaking a little. Not an emergency. {please}",
        "Fire hydrant cap {loc} is missing. {please}",
    ]),
    ("other", "nearmiss/after-fire", False, 1, [
        "There was a house fire {loc} last month and the burned debris is still piled up by the curb. {please}",
        "After the fire department put out the fire {loc} last week, the sidewalk was left damaged. {please}",
    ]),
    ("streetlight", "nearmiss/gas-station", False, 1, [
        "Streetlight out by the gas station {loc}. {please}",
        "Light at the gas station entrance {loc} is out, the city pole not the station's. {please}",
    ]),
    ("pothole", "nearmiss/could-hurt", False, 2, [
        "Nobody's hurt yet but this pothole {loc} is going to cause an accident someday. {please}",
        "Pothole {loc} is so deep someone could break an ankle. {again}",
    ]),
    ("noise", "nearmiss/fireworks", False, 0, [
        "Neighbors {loc} set off fireworks {time}. Nobody's hurt, just loud. {please}",
        "People shooting off fireworks {loc} every night this week, dog is terrified. {please}",
    ]),
    ("animal", "nearmiss/past-bite", False, 1, [
        "The dog {loc} that bit my son last year is out loose again. Nobody is hurt, but can animal control check the owners? {please}",
        "Want to report a dog that got loose {loc} yesterday. It's back home now. {please}",
    ]),
]

OPENERS = ["", "", "", "Hi, ", "Hello, ", "Hi there. ", "Good morning. ", "I'd like to report something. ",
           "Not sure if this is the right place but ", "To whom it may concern: ", "Quick report: ",
           "Hey, ", "Resident here. ", "FYI - "]
FILLERS = ["", "", "", "", " I walk this way every day.", " I've lived here 20 years.", " Photo attached.",
           " See attached pic.", " Not sure who handles this.", " My neighbor asked me to report it too.",
           " I pay my taxes for this.", " Let me know if you need anything else.", " Ref: my earlier email."]

# Held-out phrasing families (never seen in train/val): one per service plus unseen emergency and
# near-miss phrasings, so test measures generalization to new wording rather than memorized templates.
TEST_FAMILIES = ["pothole/damage", "streetlight/out", "trash/dumping", "noise/barking", "graffiti/wall",
                 "water/main-break", "animal/aggressive", "parking/abandoned", "other/sidewalk-sign",
                 "pothole/sinkhole-emergency", "animal/attack-emergency", "other/gas-emergency",
                 "nearmiss/hydrant-word"]

CHANNELS = ["web form", "phone call transcript", "mobile app", "email", "text message", "social media DM"]


def wrap_channel(rng, channel, text):
    name = C.person(rng)
    if channel == "phone call transcript":
        intro = C.pick(rng, ["Caller states:", "Caller reports", "Resident on the line says", "Agent notes - caller:"])
        return f"{intro} {text}{C.maybe(rng, 0.4, ' Callback ' + C.phone(rng) + '.')}"
    if channel == "email":
        subj = C.pick(rng, ["Service request", "Complaint", "Please help", "Issue on my street", "311"])
        sig = C.pick(rng, ["", f"\n\n{name}", f"\n\nThanks,\n{C.first_name(rng)}", "\n\nSent from my iPhone"])
        return f"Subject: {subj}\n\n{text}{sig}"
    if channel == "text message":
        return text.replace(". ", " ").rstrip(".")
    if channel == "social media DM":
        return C.pick(rng, ["@CityServices ", "hey city ", "", "Hi! "]) + text
    if channel == "mobile app":
        cat = C.pick(rng, ["General", "Street issue", "Other", "Report a problem"])
        return f"[category: {cat}] {text}"
    return text


def build(rng):
    examples = []
    for service, fam, emergency, priority, templates in FAMILIES + NEAR_MISS:
        for i in range(PER_FAMILY):
            tpl = templates[i % len(templates)]
            # info requests often have no location; others: 72% concrete, 28% vague or none
            if "{loc}" in tpl:
                concrete = rng.random() < 0.72
                loc = loc_concrete(rng) if concrete else C.pick(rng, VAGUE + [""])
            else:
                concrete, loc = False, ""
            text = C.fill(rng, tpl.replace("{loc}", "\x00"), SLOTS).replace("\x00", loc)
            opener = C.pick(rng, OPENERS)
            if opener and text[:1].isupper() and not text.startswith("I "):
                text = text[0].lower() + text[1:] if opener.endswith("but ") else text
            text = opener + text + C.pick(rng, FILLERS)
            text = C.messy(rng, text, typo_rate=0.04, p_typo=0.4)
            channel = C.pick(rng, CHANNELS)
            text = wrap_channel(rng, channel, text)
            examples.append({
                "family": fam, "group": service,
                "state": {"channel": channel, "request": text},
                "gold": {"service": service, "emergency": emergency, "location_present": concrete,
                         "priority": priority},
            })
    return examples


def main():
    rng = C.rng_for(NAME, SEED)
    splits = C.write_dataset(NAME, build(rng), HERE, PREFIX, seed=SEED, test_families=TEST_FAMILIES)
    C.summary(NAME, splits)
    return splits


if __name__ == "__main__":
    main()
