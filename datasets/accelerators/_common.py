"""Shared, stdlib-only helpers for the accelerator generators.

Every generate.py builds a list of *examples* and hands them to `write_dataset`:

    {"family": "pothole/t3",      # phrasing family; TEST holds out whole families
     "group":  "pothole",         # stratification key (usually the main choice label)
     "state":  {field: text},
     "gold":   {qid: label}}

`write_dataset` dedupes on state text, splits by family (held-out families -> test; the rest shuffled
into train/val), stamps ids, attaches the pack's exact questions, and writes train/val/test.jsonl.
"""
import hashlib
import json
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def load_pack(name):
    """The pack's questions straight from laya_mcp/accelerator_packs.py (the single source of wording).
    Imported by file path so generators do not need the rest of laya_mcp importable."""
    import importlib.util
    pkg_dir = os.path.join(REPO_ROOT, "laya_mcp")
    if "laya_mcp" not in sys.modules:
        # minimal package shell: client.py (stdlib) + accelerator_packs.py
        spec = importlib.util.spec_from_file_location("laya_mcp", os.path.join(pkg_dir, "__init__.py"),
                                                      submodule_search_locations=[pkg_dir])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["laya_mcp"] = mod
    from laya_mcp import accelerator_packs  # noqa: E402
    return accelerator_packs.PACKS[name]


# ------------------------------------------------------------------ randomness and text noise

def rng_for(name, seed=1234):
    h = int(hashlib.sha256(f"{name}:{seed}".encode()).hexdigest()[:12], 16)
    return random.Random(h)


def pick(rng, seq):
    return seq[rng.randrange(len(seq))]


def fill(rng, template, slots):
    """Replace {slot} with a random choice from slots[slot] (a list or a callable(rng))."""
    def rep(m):
        key = m.group(1)
        v = slots[key]
        return v(rng) if callable(v) else pick(rng, v)
    out = template
    for _ in range(3):                      # allow one level of nested slots
        new = re.sub(r"\{([a-z_0-9]+)\}", rep, out)
        if new == out:
            break
        out = new
    return out


_KEYBOARD_NEIGHBORS = {
    "a": "qs", "b": "vn", "c": "xv", "d": "sf", "e": "wr", "f": "dg", "g": "fh", "h": "gj", "i": "uo",
    "j": "hk", "k": "jl", "l": "k", "m": "n", "n": "bm", "o": "ip", "p": "o", "r": "et", "s": "ad",
    "t": "ry", "u": "yi", "w": "qe", "y": "tu",
}


def typo(rng, text, rate=0.03):
    """Introduce keyboard-style typos into roughly `rate` of words longer than 3 letters."""
    words = text.split(" ")
    out = []
    for w in words:
        if len(w) > 3 and w.isalpha() and rng.random() < rate:
            i = rng.randrange(1, len(w) - 1)
            kind = rng.randrange(4)
            if kind == 0:                                   # swap
                w = w[:i] + w[i + 1] + w[i] + w[i + 2:]
            elif kind == 1:                                 # drop
                w = w[:i] + w[i + 1:]
            elif kind == 2:                                 # double
                w = w[:i] + w[i] + w[i:]
            else:                                           # neighbor key
                c = w[i].lower()
                if c in _KEYBOARD_NEIGHBORS:
                    w = w[:i] + pick(rng, _KEYBOARD_NEIGHBORS[c]) + w[i + 1:]
        out.append(w)
    return " ".join(out)


def casing(rng, text):
    """Occasionally all-lowercase (phone/chat style) or sentence-start lowercase."""
    r = rng.random()
    if r < 0.12:
        return text.lower()
    if r < 0.16:
        return re.sub(r"(^|[.!?]\s+)([A-Z])", lambda m: m.group(1) + m.group(2).lower(), text)
    return text


def messy(rng, text, typo_rate=0.03, p_typo=0.45):
    """Default realism pass: some rows get typos, some get chat casing, whitespace tidy."""
    if rng.random() < p_typo:
        text = typo(rng, text, typo_rate)
    text = casing(rng, text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +([,.!?])", r"\1", text)
    return text.strip()


def maybe(rng, p, text, other=""):
    return text if rng.random() < p else other


# ------------------------------------------------------------------ synthetic identities (obviously fake)

FIRST = ["Alex", "Jordan", "Sam", "Taylor", "Casey", "Riley", "Morgan", "Jamie", "Avery", "Quinn",
         "Drew", "Reese", "Rowan", "Parker", "Skyler", "Dana", "Robin", "Kai", "Emerson", "Hayden",
         "Priya", "Wei", "Luis", "Fatima", "Kenji", "Amara", "Mateo", "Ingrid", "Tariq", "Nadia"]
LAST = ["Doe", "Roe", "Sample", "Example", "Placeholder", "Testwell", "Mockford", "Fakeley", "Nullman",
        "Dummyson", "Specimen", "Demo", "Pseudo", "Stubbs", "Templeton", "Fixture", "Lorem", "Ipsum"]


def person(rng):
    return f"{pick(rng, FIRST)} {pick(rng, LAST)}"


def first_name(rng):
    return pick(rng, FIRST)


def phone(rng):
    """North American fictional range 555-0100..0199."""
    return f"({rng.randrange(200, 990)}) 555-01{rng.randrange(0, 100):02d}"


def email(rng, name=None, domain=None):
    name = name or person(rng)
    local = re.sub(r"[^a-z.]", "", name.lower().replace(" ", pick(rng, [".", "_", ""])))
    return f"{local}@{domain or pick(rng, ['example.com', 'example.org', 'example.net'])}"


def fake_ssn(rng):
    """Always invalid: area number 000 is never issued."""
    return f"000-{rng.randrange(10, 99)}-{rng.randrange(1000, 9999)}"


def dob(rng):
    return f"{rng.randrange(1, 13):02d}/{rng.randrange(1, 29):02d}/{rng.randrange(1940, 2006)}"


STREETS = ["Maple St", "Oak Ave", "Cedar Ln", "Elm St", "Pine Rd", "Birch Way", "Willow Dr", "Aspen Ct",
           "Main St", "1st Ave", "2nd St", "3rd Ave", "4th St", "Park Blvd", "Lakeview Dr", "Ridge Rd",
           "Mill St", "River Rd", "Hillcrest Ave", "Sunset Blvd", "Juniper St", "Spruce St", "Walnut Ave",
           "Chestnut St", "Prairie Ln", "Mesa Dr", "Canyon Rd", "Foothill Pkwy", "Columbine Ct",
           "Blue Spruce Dr", "Elk Run Rd", "Railroad Ave"]


def address(rng):
    return f"{rng.randrange(100, 9900)} {pick(rng, STREETS)}"


def intersection(rng):
    a, b = rng.sample(STREETS, 2)
    return f"{a} {pick(rng, ['&', 'and', '/', 'at'])} {b}"


# ------------------------------------------------------------------ split + write

def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def split_by_family(examples, rng, test_family_frac=0.2, val_frac=0.12, test_families=None):
    """Hold out whole phrasing families for test (per group, so every group shows up in test when it has
    >= 2 families); shuffle the rest into train/val. `test_families` pins the held-out list instead."""
    groups = {}
    for ex in examples:
        groups.setdefault(ex["group"], set()).add(ex["family"])
    test_fams = set(test_families or [])
    known = {ex["family"] for ex in examples}
    if test_fams - known:
        raise ValueError(f"unknown test families: {sorted(test_fams - known)}")
    for g in ([] if test_families else sorted(groups)):
        fams = sorted(groups[g])
        rng.shuffle(fams)
        k = max(1, int(round(len(fams) * test_family_frac))) if len(fams) >= 2 else 0
        test_fams.update(fams[:k])
    # Coverage: every gold label that occurs in >= 3 families must also occur in test, so each
    # question is measured on all of its labels (e.g. held-out emergency phrasings, not just routine).
    fam_labels = {}
    for ex in examples:
        for q, v in ex["gold"].items():
            fam_labels.setdefault((q, json.dumps(v)), set()).add(ex["family"])
    for key in sorted(fam_labels):
        fams = sorted(fam_labels[key])
        if len(fams) >= 3 and not (set(fams) & test_fams):
            test_fams.add(fams[rng.randrange(len(fams))])
    test = [e for e in examples if e["family"] in test_fams]
    rest = [e for e in examples if e["family"] not in test_fams]
    rng.shuffle(rest)
    n_val = int(round(len(rest) * val_frac))
    return {"train": rest[n_val:], "val": rest[:n_val], "test": test}


def write_dataset(name, examples, out_dir, prefix, seed=1234, test_family_frac=0.2, val_frac=0.12,
                  test_families=None):
    """Dedupe, split, stamp ids and questions, write JSONL. Returns {split: rows}."""
    pack = load_pack(name)
    questions = pack["questions"]
    seen, uniq = set(), []
    for ex in examples:
        key = json.dumps(ex["state"], sort_keys=True).lower()
        if key in seen:
            continue
        seen.add(key)
        missing = [q for q in questions if q not in ex["gold"]]
        if missing:
            raise ValueError(f"{name}: example missing gold for {missing}: {ex['state']}")
        uniq.append(ex)
    rng = rng_for(name + ":split", seed)
    splits = split_by_family(uniq, rng, test_family_frac, val_frac, test_families)
    out = {}
    os.makedirs(out_dir, exist_ok=True)
    for split, exs in splits.items():
        rows = []
        for i, ex in enumerate(exs):
            rows.append({
                "id": f"{prefix}-{split}-{_slug(ex['family'])}-{i:05d}",
                "state": ex["state"],
                "questions": questions,
                "gold": {q: ex["gold"][q] for q in questions},
                "family": ex["family"],     # optional in the fine-tune format; evaluate.py reports by family
            })
        with open(os.path.join(out_dir, f"{split}.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        out[split] = rows
    return out


def label_balance(rows, questions):
    """{qid: {label: count}} for README cards."""
    bal = {}
    for q, spec in questions.items():
        c = {}
        for r in rows:
            v = r["gold"].get(q)
            if spec["type"] == "score" and isinstance(v, int):
                v = f"{v}"
            c[str(v).lower() if isinstance(v, bool) else str(v)] = c.get(
                str(v).lower() if isinstance(v, bool) else str(v), 0) + 1
        bal[q] = dict(sorted(c.items()))
    return bal


def summary(name, splits):
    pack = load_pack(name)
    allrows = [r for s in splits.values() for r in s]
    print(f"{name}: " + ", ".join(f"{s}={len(v)}" for s, v in splits.items()) + f", total={len(allrows)}")
    for q, c in label_balance(allrows, pack["questions"]).items():
        print(f"  {q}: {c}")
