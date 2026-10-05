"""ridgeback-route: which tool group, then which tool, a household request needs.

Hierarchical: `group` picks one of 15 groups; a row also carries gold for the one `tool_<group>`
question that applies, plus `needs_tool` and `changes`. The other tool questions have no gold in that
row and are simply not scored for it (evaluate.py skips a qid a row's gold does not name).

One REQUESTS table drives this and the gate set: a template per tool, with the group, whether it writes,
and whether it is irreversible. Phrasings are natural household chat with variation. `chat` and `undo`
have no tool question (one or zero tools), so a row for them carries only `group`.
"""
from .world import BASE_SLOTS, fill, pick, vary
from laya_mcp.ridgeback_packs import TOOL_GROUP, format_context

SLOTS = dict(BASE_SLOTS)

# tool -> (writes, irreversible, [templates]). Group comes from TOOL_GROUP. Reads don't change anything;
# writes do; the three comms sends are irreversible.
TOOLS = {
    # grocery
    "grocery_add": (True, False, ["add {item} to the shopping list", "we need {item}", "put {item} on groceries",
                                  "grab {item} next shop", "{item} and {item} for the store"]),
    "grocery_list": (False, False, ["what's on the grocery list", "read me the shopping list",
                                    "what do we need from the store", "how long is the grocery list"]),
    "grocery_mark_bought": (True, False, ["I got the {item}", "mark {item} as bought", "tick off {item}, got it",
                                          "bought the {item} already"]),
    "grocery_remove": (True, False, ["take {item} off the list, we have it", "remove {item} from groceries",
                                     "drop {item} from the shopping list"]),
    "grocery_clear": (True, False, ["clear the grocery list, we shopped", "wipe the shopping list",
                                    "empty the grocery list after today's run"]),
    "plan_grocery_run": (False, False, ["plan a shop with stores near me", "where should I shop for this list",
                                        "plan the grocery run", "which {store} is closest for the list"]),
    # lists
    "list_add": (True, False, ["add {item} to the {list}", "put sunscreen on the {list}",
                               "add 'call the plumber' to the {list}", "stick {item} on the {list}"]),
    "list_create": (True, False, ["start a {list}", "make a new list called {list}", "create a {list} for us",
                                  "new list: {list}"]),
    "list_show": (False, False, ["what's on the {list}", "show me the {list}", "read the {list}",
                                 "how many things on the {list}"]),
    "list_check": (True, False, ["check off the tent on the {list}", "tick the first thing on the {list}",
                                 "mark 'book hotel' done on the {list}"]),
    "list_remove": (True, False, ["remove the tent from the {list}", "take sunscreen off the {list}",
                                  "delete 'call plumber' from the {list}"]),
    "lists_overview": (False, False, ["what lists do we have", "show all our lists", "how many open items across lists",
                                      "list of lists please"]),
    "inventory_list": (False, False, ["what's in the pantry", "what do we have in stock", "check the inventory",
                                      "what's in the freezer"]),
    # reminders
    "reminder_add": (True, False, ["remind me to {event} {day}", "set a reminder for {event} {day}",
                                   "remind the family about {event} {day}", "nudge me {day} about {event}"]),
    "reminders_list": (False, False, ["what reminders do I have", "what am I being reminded of",
                                      "any reminders coming up", "my reminders this week"]),
    "reminder_cancel": (True, False, ["cancel the reminder about {event}", "drop the {event} reminder",
                                      "stop reminding me about {event}"]),
    # calendar
    "calendar_add": (True, False, ["add {event} {day}", "put {event} on the calendar {day}",
                                   "schedule {event} for {day}", "new event: {event} {day}"]),
    "calendar_upcoming": (False, False, ["what's on the calendar {day}", "what do we have this week",
                                         "what's coming up", "anything on {day}"]),
    "calendar_update_event": (True, False, ["move the {event} to {day}", "change {event} to {day}",
                                            "reschedule {event} for {day}"]),
    "calendar_delete_event": (True, False, ["cancel {event}", "delete the {event} from the calendar",
                                            "take {event} off the calendar"]),
    # comms (irreversible for the three sends)
    "email_send": (True, True, ["email {adult} the notes from today", "send an email to {adult} about {event}",
                                "shoot {adult} a quick email", "email the coach we'll be late"]),
    "email_search": (False, False, ["search my email for the flight confirmation", "find the email from the school",
                                    "look up the receipt email from {store}"]),
    "email_read": (False, False, ["read me the latest email from {adult}", "open the email about {event}",
                                  "what did the school email say"]),
    "email_event": (True, True, ["email everyone the invite for {event}", "send the {event} invitation to the family",
                                 "email an invite for {event} {day}"]),
    "send_sms": (True, True, ["text {adult} that we're on our way", "send a text to {kin} about {event}",
                              "text the sitter we'll be home {day}"]),
    "set_phone": (True, False, ["save {adult}'s number as 555-0133", "set my phone number for texts",
                                "add a phone number for {kin}"]),
    # receipts
    "receipt_add": (True, False, ["record a receipt from {store} for 42 dollars", "log a purchase at {store}",
                                  "add today's {store} receipt"]),
    "receipt_get": (False, False, ["show me the {store} receipt", "pull up the last receipt from {store}",
                                   "find the receipt from {store} {day}"]),
    "receipt_totals": (False, False, ["how much did we spend at {store} this month", "total our spending last month",
                                      "what did we spend on groceries this year"]),
    "receipts_list": (False, False, ["show recent receipts", "list our receipts", "what have we logged lately"]),
    # food
    "recipe_add": (True, False, ["save the {recipe} recipe", "keep this recipe for {recipe}",
                                 "add {recipe} to our recipes"]),
    "recipe_get": (False, False, ["show me the {recipe} recipe", "how do I make {recipe}",
                                  "pull up our {recipe}"]),
    "recipe_search": (False, False, ["which recipes use {item}", "find our recipes with chicken",
                                     "search recipes for {recipe}"]),
    "what_can_i_make": (False, False, ["what can I make with what we have", "dinner from the pantry?",
                                       "what can I cook tonight without shopping"]),
    # outings
    "log_outing": (True, False, ["log that we went to {place}, 4 stars", "record our trip to {place}",
                                 "we visited {place} today, loved it"]),
    "recall_outings": (False, False, ["where have we been lately", "what outings have we logged",
                                      "did we ever go to {place}"]),
    # trips
    "plan_trip": (True, False, ["start planning {trip}", "set up a trip for {trip} next month",
                                "new trip: {trip}"]),
    "add_trip_participant": (True, False, ["add {adult} to {trip}", "put {kin} on the {trip}"]),
    "add_itinerary_item": (True, False, ["add kayaking to day 2 of {trip}", "put dinner on the {trip} itinerary"]),
    "recall_trip": (False, False, ["show me the {trip} plan", "what's planned for {trip}"]),
    "add_trip_stop": (True, False, ["add {town} as a stop on {trip}", "put {place} on the {trip} route"]),
    "reorder_trip_stops": (True, False, ["reorder the stops on {trip}", "change the route order for {trip}"]),
    "add_stay": (True, False, ["we're staying at {place} two nights on {trip}", "book night of lodging for {trip}"]),
    "add_pet": (True, False, ["add our {pet} the dog", "record {pet} as our cat"]),
    "recall_pets": (False, False, ["list our pets", "what pets do we have"]),
    "set_trip_notes": (True, False, ["add trip notes for {trip}", "write the heads-up for {trip}"]),
    "attach_trip_list": (True, False, ["attach the {list} to {trip}", "put the packing list on {trip}"]),
    # people
    "whoami": (False, False, ["who am I", "what's my role here", "am I the creator"]),
    "list_household": (False, False, ["who lives here", "who's in the household", "list everyone at home"]),
    "people_roster": (False, False, ["who has a login", "who's signed in", "who has an account here"]),
    "add_person": (True, False, ["add {kin} as someone we know", "record our neighbour {adult}",
                                 "add {adult} to the people Bobby knows"]),
    "add_relationship": (True, False, ["{adult} is {kin}'s daughter", "record that {adult} is my sister"]),
    "get_relationships": (False, False, ["how is {adult} related to {kin}", "who is {adult} to us"]),
    "graph_neighbors": (False, False, ["who's close to {adult} in the family", "who's connected to {kin}"]),
    "recall_person": (False, False, ["what do you know about {kin}", "tell me everything about {adult}"]),
    "recall_facts": (False, False, ["what did I tell you to remember about {kin}", "search what you remember about the car"]),
    "remember_person": (True, False, ["remember {kin} is allergic to shellfish", "note that {adult} prefers tea"]),
    "record_fact": (True, False, ["remember the spare key is under the mat", "remember the wifi password is in the drawer"]),
    "where_is": (False, False, ["where is {adult}", "is {kin} home yet", "where's {adult} right now"]),
    # places
    "set_address": (True, False, ["save our home address", "set the house address to {street}"]),
    "get_address": (False, False, ["what's our address on file", "what address do you have for home"]),
    "get_weather": (False, False, ["what's the weather", "is it going to rain {day}", "weather today"]),
    "search_nearby": (False, False, ["find a {place} near me", "any good parks nearby", "coffee shops close by"]),
    "request_current_location": (False, False, ["use my current location", "I'll share where I am"]),
    "geocode": (False, False, ["where is {place} exactly", "look up {town}"]),
    "distance": (False, False, ["how far is {town} from {town}", "distance between {place} and {place}"]),
    "member_distance": (False, False, ["how far is {adult} from home", "how far away is {kin}"]),
    "distance_from_home": (False, False, ["how far is {place} from home", "distance from home to {town}"]),
    # files + web
    "read_file": (False, False, ["read the file I uploaded", "what does the PDF I attached say",
                                 "summarise the CSV I just shared"]),
    "web_search": (False, False, ["search the web for {place} hours", "look up when {movie} comes out",
                                  "google the best {item} brands"]),
    # media (planned)
    "media_add": (True, False, ["add {movie} to our watch list", "put {movie} on the movies list",
                                "we should watch {movie}, add it"]),
    "media_check": (False, False, ["where can I stream {movie} now", "check again where {movie} is streaming"]),
}

# chat (no tool) and undo (one verb) rows
CHAT = ["tell me a joke", "how are you", "what's a good board game for 4 people", "explain how a rainbow forms",
        "what's the capital of Peru", "give me a pep talk", "what rhymes with orange", "thanks bobby",
        "what should I name the new goldfish", "how many cups in a quart", "what's 15% of 80",
        "who won the world cup in 1998", "say something nice about mondays"]
UNDO = ["undo that", "take that back", "oops undo", "never mind, undo the last thing", "revert that please",
        "scratch that", "undo"]


# --- multi-turn: the right tool depends on earlier turns ------------------------------------------
#
# Each entry: (target tool, [context-turn templates as (speaker_slot, text)], [follow-up requests]).
# The follow-ups are deliberately anaphoric ("add that", "cancel it", "and the weekend?"), and several
# appear under more than one target, so only the earlier turns can tell them apart. Speaker "P" is a
# household member (filled with a name), "B" is Bobby.
CTX = [
    ("grocery_add", [("P", "we're out of {item} again"), ("B", "Want me to put {item} on the shopping list?")],
     ["yes add it", "add that", "yep, put it on", "please do"]),
    ("grocery_add", [("P", "what goes in the {recipe}?"), ("B", "You'll need {item} and {item}.")],
     ["add those to the list", "put them on groceries", "add that stuff"]),
    ("list_add", [("P", "show me the {list}"), ("B", "The {list} has 4 things on it.")],
     ["add {item} to it", "add that to it too", "put sunscreen on there"]),
    ("list_add", [("P", "we need to plan the camping trip"), ("B", "Your camping list has a tent and a stove.")],
     ["add that to the list", "add a lantern", "put bug spray on it"]),
    ("calendar_upcoming", [("P", "what's on the calendar {day}?"), ("B", "Just the {event}.")],
     ["and the weekend?", "what about Saturday?", "and next week?"]),
    ("get_weather", [("P", "what's the weather today?"), ("B", "Sunny, high of 72.")],
     ["and the weekend?", "what about tomorrow?", "and Saturday?"]),
    ("reminders_list", [("P", "what reminders do I have today?"), ("B", "One: call the vet.")],
     ["and tomorrow?", "what about the weekend?"]),
    ("calendar_update_event", [("P", "when's the {event}?"), ("B", "The {event} is {day}.")],
     ["move it to Friday", "push it back an hour", "can we make it Saturday instead"]),
    ("calendar_delete_event", [("P", "when's the {event}?"), ("B", "The {event} is {day}.")],
     ["cancel it", "take it off", "we're not going anymore, remove it"]),
    ("reminder_cancel", [("P", "what reminders are set?"), ("B", "A reminder to {event} {day}.")],
     ["cancel it", "drop that one", "stop that reminder"]),
    ("where_is", [("P", "where's {adult}?"), ("B", "{adult} is at home.")],
     ["and {kin}?", "what about {kid}?", "where's everyone else?"]),
    ("member_distance", [("P", "how far is {adult} from home?"), ("B", "About 3 miles.")],
     ["and {kin}?", "what about {kid}?"]),
    ("recall_person", [("P", "what do you know about {kin}?"), ("B", "{kin} likes tea and gardening.")],
     ["and {adult}?", "what about {kid}?"]),
    ("email_send", [("P", "draft an email to the coach about Saturday"), ("B", "Here's a draft: we'll be late.")],
     ["looks good, send it", "yes send that", "ok go ahead and send"]),
    ("send_sms", [("P", "write a text to {adult} saying we're on our way"), ("B", "Draft: on our way!")],
     ["send it", "yep send that", "ok text it"]),
    ("distance_from_home", [("P", "find a park nearby"), ("B", "{place} looks good.")],
     ["how far is that from home?", "how far is it from the house?"]),
    ("recipe_add", [("P", "how do you make {recipe}?"), ("B", "Here's a simple version with 5 steps.")],
     ["save that recipe", "keep that one", "add it to our recipes"]),
    ("media_add", [("P", "have you heard of {movie}?"), ("B", "Yes, it's well reviewed.")],
     ["add it to our watch list", "put that on the movies list", "we should watch it, add it"]),
    ("undo", [("P", "add {item} to the list"), ("B", "Added {item} to the shopping list.")],
     ["undo that", "oops, take that back", "never mind, undo it"]),
]
# Hard negatives: tool-heavy earlier turns, but the new request needs no tool (or a different one,
# self-contained). Context present, routing still follows the request.
CTX_NEG = [
    ("chat", [("P", "add {item} to the list"), ("B", "Added {item} to the shopping list.")],
     ["thanks!", "perfect, thank you", "you're the best", "cool"]),
    ("chat", [("P", "what's on the calendar {day}?"), ("B", "Just the {event}.")],
     ["tell me a joke", "how are you today", "what rhymes with orange"]),
    ("grocery_add", [("P", "what's on the calendar {day}?"), ("B", "Just the {event}.")],
     ["add {item} to the shopping list", "we need {item}"]),
    ("calendar_add", [("P", "we're out of {item}"), ("B", "Added {item} to the shopping list.")],
     ["add {event} {day}", "put {event} on the calendar {day}"]),
    ("get_weather", [("P", "where's {adult}?"), ("B", "{adult} is at home.")],
     ["what's the weather today", "is it going to rain {day}"]),
]
WRITES_TOOL = {t for t, (w, _, _) in TOOLS.items() if w} | {"undo", "media_add"}


def _turns(rng, templates):
    out = []
    for who, text in templates:
        speaker = "Bobby" if who == "B" else pick(rng, BASE_SLOTS["adult"] + BASE_SLOTS["kid"])
        out.append((speaker, fill(rng, text, SLOTS)))
    # sometimes an older, unrelated exchange sits in front of the relevant one
    if rng.random() < 0.35:
        older = [(pick(rng, BASE_SLOTS["adult"]), fill(rng, pick(rng, ["good morning", "who's home?",
                  "remind me to water the plants later", "what's for dinner?"]), SLOTS)),
                 ("Bobby", pick(rng, ["Morning!", "Everyone's home.", "Done.", "Tacos are planned."]))]
        out = older + out
    return out


def _gold(tool):
    if tool == "chat":
        return {"group": "chat", "needs_tool": False, "changes": False}
    g = TOOL_GROUP[tool]
    gold = {"group": g, "needs_tool": True, "changes": tool in WRITES_TOOL}
    if g not in ("undo", "chat"):
        gold[f"tool_{g}"] = tool
    return gold


def rows(rng, reps=8):
    out = []
    for tool, (writes, irrev, templates) in TOOLS.items():
        g = TOOL_GROUP[tool]
        for ti, tmpl in enumerate(templates):
            for _ in range(reps):
                req = vary(rng, fill(rng, tmpl, SLOTS))
                gold = {"group": g, f"tool_{g}": tool, "needs_tool": True, "changes": writes}
                out.append((f"rt/{g}/{tool}/{ti}", f"rt:{g}:{tool}",
                            {"context": _bg_ctx(rng), "request": req}, gold))
    for ci, c in enumerate(CHAT):
        for _ in range(reps):
            out.append((f"rt/chat/{ci}", "rt:chat",
                        {"context": _bg_ctx(rng), "request": vary(rng, fill(rng, c, SLOTS))},
                        {"group": "chat", "needs_tool": False, "changes": False}))
    for ui, u in enumerate(UNDO):
        for _ in range(reps):
            out.append((f"rt/undo/{ui}", "rt:undo",
                        {"context": _bg_ctx(rng), "request": vary(rng, u, openers=(rng.random() < 0.5))},
                        {"group": "undo", "needs_tool": True, "changes": True}))
    # multi-turn: one family per (pattern, follow-up phrasing), so test holds out whole phrasings
    for kind, table in (("ctx", CTX), ("ctxneg", CTX_NEG)):
        for pi, (tool, turns, follow) in enumerate(table):
            for fi, f in enumerate(follow):
                for _ in range(reps + 2):
                    ctx = format_context(_turns(rng, turns))
                    req = vary(rng, fill(rng, f, SLOTS), openers=(rng.random() < 0.3))
                    out.append((f"rt/{kind}/{tool}/{pi}/{fi}", f"rt:{kind}:{tool}",
                                {"context": ctx, "request": req}, _gold(tool)))
    return out


def _bg_ctx(rng):
    """Most single-turn rows have no history; some carry an unrelated recent exchange, so the model
    learns that context only matters when the request leans on it."""
    if rng.random() < 0.6:
        return "(none)"
    pairs = [("what's for dinner?", "Tacos are planned."), ("who's home?", "Everyone's home."),
             ("good morning", "Morning!"), ("is it cold out?", "It's 45 and windy.")]
    said, reply = pick(rng, pairs)
    return format_context([(pick(rng, BASE_SLOTS["adult"]), said), ("Bobby", reply)])
