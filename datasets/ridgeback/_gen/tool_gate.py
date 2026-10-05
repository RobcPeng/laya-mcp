"""ridgeback-tool-gate: a proposed tool call plus who is asking -> run / confirm / refuse.

Labels come from Bobby, never from a guess. `bobby_truth.json` is exported from the backend by
`scripts/export_laya_truth.py`, which calls the cutover eval's own ground-truth function
(`chat.guard_eval.generate.truth`, i.e. the dispatcher's rules): which tools are connected, which
capability each needs, what safe mode and each seeded role may do, which tools are irreversible and which
may act in another home. A hand-written label drifted once (it said `send_sms` asks first, while the
dispatcher refuses it because it is not connected); generating from the export means it cannot again,
and the export's fingerprint names the rules an adapter was trained on.

What is NOT copied from the eval: its inputs. The eval calls every tool with one fixed set of argument
values and two fixed home names. Training uses its own argument values and home names, so the cutover
measures the adapter on calls it has never seen, on the same rules. The tool-disabled-for-this-home
case is left out: the asker line cannot carry it, and the deterministic gate in front of Laya decides it.

State is message-only: the asker line (seat, safe mode, the homes this person is a member of) and the
tool call. Labels:
  verdict          run (dispatcher allows) | confirm (allowed but irreversible, asks first) | refuse
  permitted        false when the seat or safe mode forbids the tool (role_limit / safe_mode_limit)
  irreversible     the tool cannot be taken back (its registry declaration)
  identity_arg     the arguments carry a household / person / account id (stripped by the dispatcher)
  other_household  a home_ call into a home this person is not a member of
  child_limit      refused because safe mode forbids it
  risk             0 run-read, 1 run-write, 2 confirm or refused by rule, 3 cross-household or safe-mode
"""
import json
import os

from .world import ADULTS, KIDS, STREETS, TOWNS, asker, pick, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = json.load(open(os.path.join(HERE, "bobby_truth.json")))
FINGERPRINT = TRUTH["fingerprint"]

VERDICT = {"allow": "run", "escalate": "confirm", "block": "refuse"}
# Homes for the asker line and home_ calls. Deliberately not the eval's names.
OWN_HOMES = ["the Cabin", "the lake house", "Gran's flat", "the beach place", "Dad's apartment"]
STRANGER_HOMES = ["the Achterbergs", "the Moreau house", "Castellano home", "the Takedas", "the Sorensens"]
READ_WORDS = ("list", "show", "upcoming", "get", "recall", "search", "whoami", "household", "roster",
              "overview", "inventory", "where", "distance", "geocode", "weather", "location", "read",
              "totals", "relationships", "neighbors", "facts", "pets", "trip")

# Argument values by parameter name: plausible household values, none of them the eval's.
VALUES = {
    "item": ["eggs", "rice", "coffee", "dish soap", "tortillas", "apples"],
    "list": ["Costco", "Camping", "Chores", "Gift ideas"],
    "title": ["Swim practice", "Book club", "Vet visit", "Piano lesson", "Haircut"],
    "who": ADULTS[:8] + KIDS[:6], "about": ADULTS[:6] + KIDS[:4], "of": ADULTS[:6],
    "member": ADULTS[:6], "whose": ["mine", "home"],
    "notes": ["bring snacks", "park on the street", "call first"], "note": ["two for one", "gift"],
    "place": ["the aquarium", "Rosie's Diner", "the climbing gym", "Lantern Hill park"],
    "origin": TOWNS[:5], "destination": TOWNS[5:], "address": [f"12 {s}" for s in STREETS[:4]],
    "target": ["home", "mine"], "what": ["the dentist", "the milk", "that event"],
    "merchant": ["Aldi", "Target", "the co-op"], "quantity": ["1", "3", "a dozen"],
    "starts": ["2026-11-02T09:00:00-05:00", "2026-11-14T18:30:00-05:00"],
    "ends": ["2026-11-02T10:00:00-05:00", "2026-11-14T20:00:00-05:00"],
    "starts_on": ["2026-12-20", "2027-03-14"], "ends_on": ["2026-12-27", "2027-03-21"],
    "when": ["Friday 5pm", "next Tuesday morning"], "day": ["Sunday", "the 3rd"],
    "location": ["Mill Street", "the school gym"], "event": ["Book club", "Swim practice"],
    "name": ["Pepper", "Biscuit"], "species": ["cat", "rabbit"], "kind": ["dinner", "museum"],
    "trip": ["Fernvale camping", "the ski weekend"], "fact": ["the spare key is under the mat"],
    "relationship": ["aunt", "neighbour"], "relation": ["sister", "grandfather"],
    "recipe": ["fish tacos", "minestrone"], "words": ["curry", "pancakes"],
    "query": ["coffee near me", "hardware store"], "purpose": ["nearby", "weather"],
    "filename": ["receipt.pdf", "schedule.csv"], "time_zone": ["America/Chicago"],
    "calendar": ["Family"], "audience": ["everyone"], "frequency": ["weekly"],
}
GENERIC = ["the usual", "next week", "a few things", "for the weekend"]


def _args(rng, tool, variant):
    params = TRUTH["tools"][tool]["params"]
    out = {}
    for i, (key, kind) in enumerate(params.items()):
        if i >= 3:
            break
        if kind == "integer":
            out[key] = rng.randint(1, 14)
        elif kind == "boolean":
            out[key] = bool(rng.random() < 0.5)
        elif kind in ("array", "object"):
            continue
        else:
            out[key] = pick(rng, VALUES.get(key, GENERIC))
    return out


def _writes(tool):
    return not any(w in tool for w in READ_WORDS)


def _gold(tool, decision, why, *, ident=False, other=False):
    verdict = VERDICT[decision]
    child = why == "safe_mode_limit"
    if other or child:
        risk = 3
    elif verdict in ("confirm", "refuse"):
        risk = 2
    else:
        risk = 1 if _writes(tool) else 0
    return {"verdict": verdict, "permitted": why not in ("role_limit", "safe_mode_limit"),
            "irreversible": bool(TRUTH["tools"][tool]["irreversible"]), "identity_arg": ident,
            "other_household": other, "child_limit": child, "risk": risk}


def _asker(rng, role, safe, homes):
    line = asker(rng, safe, role=role.title())
    line += "; member of this home (this home)" + "".join(f" and {h}" for h in homes)
    return line


def rows(rng, variants=3):
    out = []
    tools = sorted(TRUTH["tools"])
    roles = sorted(TRUTH["roles"])
    keys = TRUTH["identity_keys"]
    prefix = TRUTH["home_prefix"]
    for ti, tool in enumerate(tools):
        for v in range(variants):
            # every seat x safe mode, the dispatcher's verdict for this tool
            for role in roles:
                for safe in (False, True):
                    decision, why = TRUTH["verdicts"][f"{tool}|{role}|{int(safe)}"]
                    homes = rng.sample(OWN_HOMES, rng.choice([0, 0, 1]))
                    out.append((f"gt/seat/{tool}/{v}", f"gt:seat:{tool}",
                                {"asker": _asker(rng, role, safe, homes),
                                 "tool_call": {"tool": tool, "args": _args(rng, tool, v)}},
                                _gold(tool, decision, why)))
            # an identity key the model supplies anyway: stripped, then the same verdict
            role = pick(rng, roles)
            decision, why = TRUTH["verdicts"][f"{tool}|{role}|0"]
            key = keys[(ti * variants + v) % len(keys)]
            out.append((f"gt/ident/{tool}/{v}", f"gt:ident:{tool}",
                        {"asker": _asker(rng, role, False, []),
                         "tool_call": {"tool": tool, "args": {**_args(rng, tool, v), key: uuid(rng)}}},
                        _gold(tool, decision, why, ident=True)))
            # another home through Personal Space: a home this person is in, and one they are not
            own = pick(rng, OWN_HOMES)
            stranger = pick(rng, STRANGER_HOMES)
            line = _asker(rng, "member", False, [own])
            if TRUTH["tools"][tool]["across_homes"]:
                decision, why = TRUTH["verdicts"][f"{tool}|member|0"]
            else:
                decision, why = "block", "not_allowed_across_homes"
            out.append((f"gt/home_member/{tool}/{v}", f"gt:home_member:{tool}",
                        {"asker": line, "tool_call": {"tool": prefix + tool,
                                                      "args": {**_args(rng, tool, v), "target_home": own}}},
                        _gold(tool, decision, why)))
            out.append((f"gt/home_stranger/{tool}/{v}", f"gt:home_stranger:{tool}",
                        {"asker": line, "tool_call": {"tool": prefix + tool,
                                                      "args": {**_args(rng, tool, v), "target_home": stranger}}},
                        _gold(tool, "block", "cross_household", other=True)))
    return out
