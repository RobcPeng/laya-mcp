"""Regenerate and validate every accelerator set.

    python datasets/accelerators/build_all.py                 # regenerate all, validate, refresh catalog
    python datasets/accelerators/build_all.py --no-generate   # validate the JSONL already on disk
    python datasets/accelerators/build_all.py --determinism   # also regenerate twice and compare hashes
    python datasets/accelerators/build_all.py support-ticket-triage rag-relevance-filter

Checks per set: the pack exists; every row has id/state/questions/gold; `questions` equals the pack's
questions exactly (the literal instruction strings a fine-tune learns); the state carries exactly the
pack's state fields as non-empty strings; gold labels are valid for their question type (noul bool,
choice a listed label, score an int level); ids are unique across splits; no state appears in both
test and train/val; split sizes are sane; every question sees at least two labels in test; every choice
label appears in train. Writes catalog.json and the catalog table in README.md. Stdlib only.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _common as C  # noqa: E402

SPLITS = ("train", "val", "test")
MIN_SIZES = {"train": 200, "val": 20, "test": 50}
MAX_STATE_CHARS = 1600          # ~400 tokens; longer states get truncated behind the question header
CAT_START, CAT_END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def set_names():
    return sorted(d for d in os.listdir(HERE)
                  if os.path.isfile(os.path.join(HERE, d, "generate.py")))


def generate(name):
    r = subprocess.run([sys.executable, os.path.join(HERE, name, "generate.py")], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{name}: generate.py failed\n{r.stderr}")
    return r.stdout


def digest(name):
    h = hashlib.sha256()
    for s in SPLITS:
        with open(os.path.join(HERE, name, f"{s}.jsonl"), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def gold_ok(q, v):
    t = q["type"]
    if t == "noul":
        return isinstance(v, bool) or (isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1)
    if t == "choice":
        return isinstance(v, str) and v in q["criteria"]
    if t == "score":
        return isinstance(v, int) and not isinstance(v, bool) and 0 <= v < len(q["criteria"])
    return False


def validate(name):
    """Returns (errors, warnings, info)."""
    errors, warnings = [], []
    try:
        pack = C.load_pack(name)
    except KeyError:
        return [f"no pack named {name!r} in laya_mcp/accelerator_packs.py"], [], {}
    pq, fields = pack["questions"], set(pack["state_fields"])
    rows = {}
    for s in SPLITS:
        path = os.path.join(HERE, name, f"{s}.jsonl")
        if not os.path.exists(path):
            errors.append(f"missing {s}.jsonl")
            rows[s] = []
            continue
        rows[s] = []
        for ln, line in enumerate(open(path), 1):
            if not line.strip():
                continue
            try:
                rows[s].append(json.loads(line))
            except ValueError as e:
                errors.append(f"{s}:{ln} bad JSON: {e}")
    ids, states = set(), {}
    long_states = 0
    for s in SPLITS:
        for i, r in enumerate(rows[s]):
            where = f"{s}:{i + 1}"
            miss = {"id", "state", "questions", "gold"} - set(r)
            if miss:
                errors.append(f"{where} missing keys {sorted(miss)}")
                continue
            if r["id"] in ids:
                errors.append(f"{where} duplicate id {r['id']}")
            ids.add(r["id"])
            if r["questions"] != pq:
                diff = [q for q in set(pq) | set(r["questions"]) if r["questions"].get(q) != pq.get(q)]
                errors.append(f"{where} questions differ from the pack: {sorted(diff)}")
            st = r["state"]
            if not isinstance(st, dict) or set(st) != fields:
                errors.append(f"{where} state fields {sorted(st) if isinstance(st, dict) else type(st)} != {sorted(fields)}")
            elif not all(isinstance(v, str) and v.strip() for v in st.values()):
                errors.append(f"{where} state has an empty or non-string field")
            else:
                if len(json.dumps(st, ensure_ascii=False)) > MAX_STATE_CHARS:
                    long_states += 1
                states.setdefault(json.dumps(st, sort_keys=True).lower(), set()).add(s)
            for q, v in r["gold"].items():
                if q not in pq:
                    errors.append(f"{where} gold for unknown question {q}")
                elif not gold_ok(pq[q], v):
                    errors.append(f"{where} invalid gold {q}={v!r} for type {pq[q]['type']}")
            if set(r["gold"]) != set(pq):
                warnings.append(f"{where} partial gold ({len(r['gold'])}/{len(pq)} questions)")
    leaks = sum(1 for sp in states.values() if "test" in sp and len(sp) > 1)
    if leaks:
        errors.append(f"{leaks} state(s) appear in test and in train/val")
    for s, n in MIN_SIZES.items():
        if len(rows[s]) < n:
            errors.append(f"{s} has {len(rows[s])} rows (< {n})")
    total = sum(len(v) for v in rows.values())
    if not 400 <= total <= 1500:
        warnings.append(f"{total} rows total (target 400-1000)")
    if long_states:
        warnings.append(f"{long_states} state(s) longer than {MAX_STATE_CHARS} chars (may truncate)")
    for q, spec in pq.items():
        test_labels = {json.dumps(r["gold"].get(q)) for r in rows["test"] if q in r["gold"]}
        if len(test_labels) < 2:
            errors.append(f"test split has a single label for {q}: {test_labels}")
        if spec["type"] == "choice":
            seen = {r["gold"].get(q) for r in rows["train"]}
            missing = [k for k in spec["criteria"] if k not in seen]
            if missing:
                warnings.append(f"choice {q}: labels never in train: {missing}")
    allrows = [r for s in SPLITS for r in rows[s]]
    info = {"splits": {s: len(rows[s]) for s in SPLITS}, "total": total,
            "balance": C.label_balance(allrows, pq), "state_fields": pack["state_fields"],
            "questions": {q: v["type"] for q, v in pq.items()}, "description": pack["description"]}
    return errors, warnings, info


def zero_shot(name):
    p = os.path.join(HERE, name, "zero_shot.json")
    return json.load(open(p)) if os.path.exists(p) else None


GROUPS = [("General and public sector", lambda n: not n.startswith("he-")),
          ("Higher education", lambda n: n.startswith("he-"))]


def _table(catalog, names):
    lines = ["| set | fields | questions | rows | train / val / test | zero-shot mean acc (test) |",
             "|---|---|---|---|---|---|"]
    for name in names:
        c = catalog[name]
        zs = c.get("zero_shot")
        z = f"{zs['mean_accuracy']:.2f}" if zs else "not run"
        qs = ", ".join(f"{q} ({t})" for q, t in c["questions"].items())
        sp = c["splits"]
        lines.append(f"| [{name}]({name}/README.md) | {', '.join(c['state_fields'])} | {qs} | {c['total']} | "
                     f"{sp['train']} / {sp['val']} / {sp['test']} | {z} |")
    return lines


def catalog_markdown(catalog):
    lines = []
    for title, keep in GROUPS:
        names = [n for n in catalog if keep(n)]
        if not names:
            continue
        lines += [f"### {title}", ""] + _table(catalog, names) + [""]
    total = sum(c["total"] for c in catalog.values())
    lines += [f"{len(catalog)} sets, {total} rows.", "", "### Per-question zero-shot accuracy", "",
              "Test split, base checkpoint. Majority = always answering the most common test label.", "",
              "| set | question | accuracy | majority baseline |", "|---|---|---|---|"]
    for name, c in catalog.items():
        zs = c.get("zero_shot")
        if not zs:
            continue
        for q, d in zs["questions"].items():
            lines.append(f"| {name} | {q} | {d['accuracy']:.2f} | {d['majority_baseline']:.2f} |")
    return "\n".join(lines)


def update_catalog_readme(catalog):
    path = os.path.join(HERE, "README.md")
    if not os.path.exists(path):
        return
    text = open(path).read()
    if CAT_START not in text or CAT_END not in text:
        return
    head, rest = text.split(CAT_START, 1)
    _, tail = rest.split(CAT_END, 1)
    open(path, "w").write(head + CAT_START + "\n" + catalog_markdown(catalog) + "\n" + CAT_END + tail)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sets", nargs="*")
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--determinism", action="store_true")
    a = ap.parse_args(argv)
    names = a.sets or set_names()
    failed = False
    catalog = {}
    for n in names:
        if not a.no_generate:
            generate(n)
            if a.determinism:
                h1 = digest(n)
                generate(n)
                if digest(n) != h1:
                    print(f"[FAIL] {n}: generate.py is not deterministic")
                    failed = True
        errors, warnings, info = validate(n)
        status = "FAIL" if errors else "ok"
        failed |= bool(errors)
        sp = info.get("splits", {})
        print(f"[{status}] {n}: total={info.get('total')} " + " ".join(f"{k}={v}" for k, v in sp.items()))
        for e in errors[:20]:
            print(f"    error: {e}")
        if len(errors) > 20:
            print(f"    ... {len(errors) - 20} more errors")
        for w in sorted(set(w.split(':', 1)[0] if 'partial gold' in w else w for w in warnings))[:10]:
            print(f"    warn: {w}")
        if info:
            zs = zero_shot(n)
            if zs:
                test_sha = hashlib.sha256(open(os.path.join(HERE, n, "test.jsonl"), "rb").read()).hexdigest()
                if zs.get("test_sha256") != test_sha:
                    print("    warn: zero_shot.json is stale (test split changed); rerun eval_zero_shot.py")
            info["zero_shot"] = zs
            catalog[n] = info
    if not a.sets:
        with open(os.path.join(HERE, "catalog.json"), "w") as f:
            json.dump(catalog, f, indent=2)
            f.write("\n")
        update_catalog_readme(catalog)
    print("FAILED" if failed else f"all {len(names)} set(s) valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
