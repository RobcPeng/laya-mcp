#!/usr/bin/env python3
"""Fit per-question serving thresholds for the Ridgeback guard, on the VAL split only.

The Ridgeback wrapper (`bobby_hearth.chat.laya_guard`) reads a JSON of {qid: {"low", "high"}}: a risk
signal at or above `high` blocks, at or above `low` escalates, below `low` allows. Ridgeback's swap gate
counts an escalation on a clean case as a false block, so the priority here is the CLEAN false-block
rate, then recall:

  low   the smallest cut whose val false-positive rate is <= --fp-budget (default 1%), i.e. the most
        recall the clean budget allows
  high  the smallest cut whose val false-positive rate is <= --block-fp (default 0.5%), never below low

A signal is the probability that something is wrong: P(true) for a "bad" question, 1 - P(true) for a
safe-when-true one (matches_request, permitted). The test split is never read.

    python -m finetune.fit_ridgeback_thresholds --url http://127.0.0.1:7493 \\
        --out finetune/recipes/ridgeback-guard.thresholds.json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from finetune.eval_ridgeback import SETS, _LocalAgent, _rows, _ServerAgent, _simplify  # noqa: E402
from laya_mcp import ridgeback_packs as R  # noqa: E402

# The risk questions each stage's decision reads (laya_guard.py uses exactly these).
RISK = {
    "input-safety": ["decline", "injection", "cross_household", "impersonation", "self_harm"],
    "tool-gate": ["permitted", "other_household", "child_limit", "irreversible"],
    "tool-result": ["injected", "quarantine", "wants_action"],
    "result-safety": ["result_unsuitable"],
    "output": ["leaks_prompt", "member_private", "safe_records", "coordinates", "other_home_data",
               "reply_unsuitable", "withhold"],
}
GRID = [x / 1000 for x in range(5, 1000, 5)]

# Per-signal false-positive budgets where the default is the wrong trade. result_unsuitable is the kid-safety
# screen on web results: a miss shows adult-only content to a child, a false positive hides an adult-only
# result from an adult (who can ask again). Its val set is small (about 30 negatives), so four adult rows (14%)
# scoring high on content v2 already exceed any small budget, and "budget wins" would then turn the screen off entirely.
FP_BUDGET_FOR = {"result_unsuitable": 0.15}


def _signal(qid, p):
    return 1.0 - p if qid in R.POSITIVE else p


def _bad(qid, gold):
    g = bool(gold)
    return (not g) if qid in R.POSITIVE else g


def _cut(fpr, rec, fp_budget, recall_target, n_neg=None):
    """Where to cut one signal, from its val distribution.

    Val shares phrasing families with train, so a fine-tuned model usually separates it cleanly, and the
    lowest cut that meets the false-positive budget then sits at the very bottom of the scale (0.005):
    any non-zero signal would trip it on new phrasings. So the cut goes in the MIDDLE of a band:

      - the band of cuts that keep false positives within budget AND recall at or above target; or, when
        no cut does both,
      - the band of cuts within budget that reach the best recall available (its plateau), so a weak
        signal is not pushed to the edge of the scale either way.

    On a small val set a rate budget can mean "zero false positives", which forces the cut to the top of
    the scale and recall to nothing; the budget is floored at one negative row (1 / n_neg) for that.
    """
    if n_neg:
        fp_budget = max(fp_budget, 1.0 / n_neg)
    ok_fp = [t for t in GRID if fpr(t) <= fp_budget]
    if not ok_fp:
        return GRID[-1], "no cut meets the false-positive budget"
    if rec(ok_fp[0]) is None:
        return max(ok_fp[0], 0.5), "no positives on val: budget cut, floored at 0.5"
    ok_both = [t for t in ok_fp if rec(t) >= recall_target]
    if ok_both:
        return round(ok_both[len(ok_both) // 2], 3), "middle of the band meeting both budget and recall"
    best = max(rec(t) for t in ok_fp)
    plateau = [t for t in ok_fp if rec(t) >= best - 1e-9]
    return round(plateau[len(plateau) // 2], 3), "recall target unreachable within budget: middle of the best-recall plateau"


def fit(agent, fp_budget=0.01, block_fp=0.005, sets=None, recall_target=0.98, block_recall=0.9):
    out = {}
    for name in (sets or SETS):
        if name not in RISK:
            continue
        rows = _rows(name, "val")
        preds = [_simplify(agent.predict(r["state"], r["questions"])) for r in rows]
        for qid in RISK[name]:
            pos, neg = [], []
            for r, a in zip(rows, preds):
                if qid not in r["gold"] or qid not in a:
                    continue
                s = _signal(qid, a[qid]["p_true"])
                (pos if _bad(qid, r["gold"][qid]) else neg).append(s)
            if not neg:
                continue

            def fpr(t):
                return sum(s >= t for s in neg) / len(neg)

            def rec(t):
                return (sum(s >= t for s in pos) / len(pos)) if pos else None

            low, how_low = _cut(fpr, rec, FP_BUDGET_FOR.get(qid, fp_budget), recall_target, len(neg))
            high, how_high = _cut(fpr, rec, max(block_fp, FP_BUDGET_FOR.get(qid, 0)), block_recall, len(neg))
            high = max(high, low)
            out[qid] = {"low": low, "high": high, "set": name, "n_pos": len(pos), "n_neg": len(neg),
                        "rule_low": how_low, "rule_high": how_high,
                        "val_fpr_at_low": round(fpr(low), 4), "val_recall_at_low": rec(low),
                        "val_recall_at_high": rec(high)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="score through a running laya.serve")
    ap.add_argument("--model", default="auto", help="server slot, e.g. typed-decisions")
    ap.add_argument("--adapter", choices=["cyber", "content", "routing"], help="fit only this adapter's sets")
    ap.add_argument("--checkpoint", default="english")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--fp-budget", type=float, default=0.01)
    ap.add_argument("--block-fp", type=float, default=0.005)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    agent = _ServerAgent(a.url, a.model) if a.url else _LocalAgent(a.checkpoint, f"cuda:{a.gpu}")
    from laya_mcp.ridgeback_packs import ADAPTERS, PACK_ADAPTER
    from finetune.eval_ridgeback import PACK
    sets = None
    if a.adapter:
        sets = [n for n in RISK if PACK_ADAPTER.get(PACK.get(n)) == a.adapter]
    thr = fit(agent, a.fp_budget, a.block_fp, sets=sets)
    thr["_meta"] = {"fitted_on": "val", "fp_budget": a.fp_budget, "block_fp": a.block_fp,
                    "pack_fingerprint": R.fingerprint(), "source": a.url or a.checkpoint}
    with open(a.out, "w") as f:
        json.dump(thr, f, indent=2, sort_keys=True)
    for q, t in sorted(thr.items()):
        if not q.startswith("_"):
            print(f"{q:16s} low={t['low']:.3f} high={t['high']:.3f} fpr@low={t['val_fpr_at_low']} "
                  f"recall@low={t['val_recall_at_low']}")


if __name__ == "__main__":
    main()
