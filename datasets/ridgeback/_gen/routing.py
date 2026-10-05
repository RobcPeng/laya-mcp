"""ridgeback-route: which tool group, then which tool, a household request needs.

Hierarchical: `group` picks one of 15 groups; a row also carries gold for the one `tool_<group>`
question that applies, plus `needs_tool` and `changes`. The other tool questions have no gold in that
row and are simply not scored for it (evaluate.py skips a qid a row's gold does not name).

One REQUESTS table drives this and the gate set: a template per tool, with the group, whether it writes,
and whether it is irreversible. Phrasings are natural household chat with variation. `chat` and `undo`
have no tool question (one or zero tools), so a row for them carries only `group`.
"""
from .world import BASE_SLOTS, asker, context_line, fill, pick, vary
from laya_mcp.ridgeback_packs import TOOL_GROUP

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


def rows(rng, reps=8):
    out = []
    for tool, (writes, irrev, templates) in TOOLS.items():
        g = TOOL_GROUP[tool]
        for ti, tmpl in enumerate(templates):
            for _ in range(reps):
                safe = rng.random() < 0.4
                req = vary(rng, fill(rng, tmpl, SLOTS))
                gold = {"group": g, f"tool_{g}": tool, "needs_tool": True, "changes": writes}
                out.append((f"rt/{g}/{tool}/{ti}", f"rt:{g}:{tool}",
                            {"context": _ctx(rng), "request": req}, gold))
    for ci, c in enumerate(CHAT):
        for _ in range(reps):
            out.append((f"rt/chat/{ci}", "rt:chat",
                        {"context": _ctx(rng), "request": vary(rng, fill(rng, c, SLOTS))},
                        {"group": "chat", "needs_tool": False, "changes": False}))
    for ui, u in enumerate(UNDO):
        for _ in range(reps):
            out.append((f"rt/undo/{ui}", "rt:undo",
                        {"context": _ctx(rng), "request": vary(rng, u, openers=(rng.random() < 0.5))},
                        {"group": "undo", "needs_tool": True, "changes": True}))
    return out


def _ctx(rng):
    if rng.random() < 0.25:
        sp = pick(rng, BASE_SLOTS["adult"])
        return context_line(rng, sp, fill(rng, pick(rng, ["add {item}", "what's for dinner?",
                            "what's on {day}?"]), SLOTS), "Done.")
    return "(none)"
