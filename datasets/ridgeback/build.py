#!/usr/bin/env python3
"""Build the five Ridgeback guard sets as seeded train/val/test JSONL.

    python datasets/ridgeback/build.py            # all five
    python datasets/ridgeback/build.py route      # one

Same row format and split policy as datasets/make_sets.py: whole phrasing FAMILIES are held out for
test (never seen in train/val), so test accuracy measures generalization to new phrasings; val is a
random slice of the training families, used for calibration and threshold fitting.

Every row: {"id", "family", "state", "questions" (the pack's, verbatim), "gold"}. State is built with
laya_mcp.packs.build_state, so non-string values (a tool_call dict) are JSON-encoded exactly as at
inference. All names, homes, addresses and numbers are invented (see _gen/world.py).
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.dirname(HERE))

from laya_mcp import packs, ridgeback_packs  # noqa: E402
from _gen import input_safety, output, routing, tool_gate, tool_result  # noqa: E402
from laya_mcp.ridgeback_packs import ADAPTERS, PACK_ADAPTER  # noqa: E402

SEED = 20261005

# one dataset per pack (per stage); the adapter it belongs to is PACK_ADAPTER.
SETS = {
    "input-safety": ("ridgeback-input-safety", input_safety.rows),
    "route": ("ridgeback-route", routing.rows),
    "tool-gate": ("ridgeback-tool-gate", tool_gate.rows),
    "tool-result": ("ridgeback-tool-result", tool_result.injection_rows),
    "result-safety": ("ridgeback-result-safety", tool_result.safety_rows),
    "output": ("ridgeback-output", output.rows),
}
# which per-stage sets make up each adapter's training set
ADAPTER_SETS = {a: [name for name, (pack, _) in SETS.items() if pack in packs_]
                for a, packs_ in ADAPTERS.items()}


def split_rows(rng, rows, test_frac=0.25, val_frac=0.12):
    """Hold out whole families per class for TEST; random VAL slice of the rest. (make_sets.py's policy.)"""
    by_class = {}
    for fam, cls, *_ in rows:
        by_class.setdefault(cls, set()).add(fam)
    test_fams = set()
    for cls, fams in sorted(by_class.items()):
        fams = sorted(fams)
        if len(fams) >= 2:
            k = max(1, round(len(fams) * test_frac))
            test_fams.update(rng.sample(fams, k))
    out = {"train": [], "val": [], "test": []}
    single = {c for c, f in by_class.items() if len(f) < 2}
    for r in rows:
        fam, cls = r[0], r[1]
        if fam in test_fams or (cls in single and rng.random() < test_frac):
            out["test"].append(r)
        elif rng.random() < val_frac:
            out["val"].append(r)
        else:
            out["train"].append(r)
    return out


def build(name, out_dir=HERE):
    pack_name, gen = SETS[name]
    pack = packs.get_pack(pack_name)
    rng = random.Random(f"{SEED}:{name}")
    rows = gen(rng)
    seen, uniq = set(), []
    for r in rows:
        key = json.dumps(r[2], sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    splits = split_rows(rng, uniq)
    counts = {}
    for split, rs in splits.items():
        rng.shuffle(rs)
        path = os.path.join(out_dir, name, f"{split}.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            for i, (fam, cls, fields, gold) in enumerate(rs):
                row = {"id": f"ridgeback-{name}-{split}-{i:04d}", "family": fam,
                       "state": packs.build_state(pack, **fields),
                       "questions": pack["questions"], "gold": gold}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts[split] = len(rs)
    return counts


def combine(adapter, set_names, out_dir=HERE):
    """Concatenate an adapter's per-stage sets into datasets/ridgeback/<adapter>/{split}.jsonl. Each row
    keeps its own pack `questions` (ids are unique across packs), so one adapter learns all its stages.
    Shuffled with a fixed seed. Scored by finetune.eval_ridgeback, not the pipeline's per-pack evaluate."""
    rng = random.Random(f"{SEED}:{adapter}")
    counts = {}
    for split in ("train", "val", "test"):
        rows = []
        for name in set_names:
            p = os.path.join(out_dir, name, f"{split}.jsonl")
            if os.path.exists(p):
                for line in open(p):
                    r = json.loads(line)
                    r["set"] = name
                    rows.append(r)
        rng.shuffle(rows)
        path = os.path.join(out_dir, adapter, f"{split}.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            for i, r in enumerate(rows):
                r["id"] = f"ridgeback-{adapter}-{split}-{i:04d}"
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        counts[split] = len(rows)
    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sets", nargs="*", help="set names (default: all)")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    total = {}
    names = a.sets or list(SETS)
    for name in names:
        c = build(name, a.out)
        total[name] = c
        print(f"{name}: {c}")
    if set(names) == set(SETS):
        for adapter in ADAPTERS:
            total[adapter] = combine(adapter, ADAPTER_SETS[adapter], a.out)
            print(f"{adapter}: {total[adapter]}")
    # also refresh the vendored pack JSON for the backend wrapper
    exp = os.path.join(os.path.dirname(os.path.dirname(HERE)), "laya_mcp", "ridgeback_packs.py")
    print(f"pack fingerprint: {ridgeback_packs.fingerprint()}")
    print(json.dumps(total))


if __name__ == "__main__":
    main()
