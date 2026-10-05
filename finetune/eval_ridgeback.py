#!/usr/bin/env python3
"""Score one Laya checkpoint (base or a fine-tuned/LoRA-merged dir) across all five Ridgeback guard sets.

The pipeline's `evaluate.py` assumes every row in a split shares one question set; the Ridgeback sets do
not (five packs), so this script evaluates each set on its own and rolls the results up. It reports what
the brief asks for:

  - per set, per question: accuracy, Brier, and for noul questions AUC + false-negative/false-positive
    rates at 0.5 and at the serving thresholds fitted on that set's val split;
  - false-BLOCK rate on clean examples (the clean families of input-safety, tool-result, and output),
    which is the over-flagging the README warns about;
  - routing accuracy: top-1 group, top-1 tool (within the predicted group), and per-group tool accuracy;
  - calibration (ECE) per set and overall;
  - latency p50 / p95 over every call.

It runs through `laya.Agent.predict`, the same path the server uses. Thresholds are fit on val and
scored on the held-out test split, so no test row is used to fit anything.

    python -m finetune.eval_ridgeback --checkpoint english --split test
    python -m finetune.eval_ridgeback --checkpoint runs/ridgeback-guard/<stamp>-lora/checkpoint
    python -m finetune.eval_ridgeback --checkpoint english --url http://127.0.0.1:7491   # via a server

`--url` scores through a running `laya.serve` (the client path) instead of loading weights locally, so a
baseline can be taken against the shared server without a GPU allocation of our own.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from laya_mcp import ridgeback_packs as R          # noqa: E402

SETS = ["input-safety", "route", "tool-gate", "tool-result", "output"]
PACK = {"input-safety": "ridgeback-input-safety", "route": "ridgeback-route",
        "tool-gate": "ridgeback-tool-gate", "tool-result": "ridgeback-tool-result",
        "output": "ridgeback-output"}
# noul questions that mean "flag it" per set, for the row-level clean/false-block rate.
FLAGS = {"input-safety": ["decline"], "tool-result": ["injected", "quarantine", "wants_action"],
         "output": ["leaks_prompt", "member_private", "safe_records", "coordinates", "other_home_data"]}
CLEAN_FAMILY = {"input-safety": lambda f: f.split("/")[1] == "none",
                "tool-result": lambda f: "clean" in f, "output": lambda f: "clean" in f}

DATA = os.path.join(os.path.dirname(HERE), "datasets", "ridgeback")


def _rows(name, split):
    with open(os.path.join(DATA, name, f"{split}.jsonl")) as f:
        return [json.loads(line) for line in f]


def _auc(pos, neg):
    if not pos or not neg:
        return None
    s, n = np.array(pos)[:, None], np.array(neg)[None, :]
    return float(((s > n).sum() + 0.5 * (s == n).sum()) / (len(pos) * len(neg)))


class _LocalAgent:
    def __init__(self, checkpoint, device):
        from laya.agent import Agent
        from .common import resolve_base
        d, _ = resolve_base(checkpoint)
        self.agent = Agent(d, device=device)

    def predict(self, state, questions):
        return self.agent.predict(state, questions)


class _ServerAgent:
    def __init__(self, url):
        from laya_mcp import client
        self.client, self.url = client, url

    def predict(self, state, questions):
        return self.client.predict(state, questions, url=self.url)


def _simplify(res):
    from laya_mcp import client
    return client.simplify(res)


def _fit_noul_thresholds(agent, rows, qids, fp_budget=0.05):
    """Per-question {low, high, threshold} from a val split: threshold = max recall within fp_budget."""
    preds = [_simplify(agent.predict(r["state"], r["questions"])) for r in rows]
    out = {}
    for q in qids:
        pos, neg = [], []
        for r, a in zip(rows, preds):
            if q not in r["gold"] or q not in a:
                continue
            p = a[q]["p_true"]
            (pos if bool(r["gold"][q]) else neg).append(p)
        if not pos or not neg:
            out[q] = {"low": 0.25, "high": 0.85, "threshold": 0.5}
            continue
        grid = [x / 100 for x in range(1, 100)]
        rec = {t: sum(p >= t for p in pos) / len(pos) for t in grid}
        fpr = {t: sum(p >= t for p in neg) / len(neg) for t in grid}
        ok = [t for t in grid if fpr[t] <= fp_budget]
        thr = max(ok, key=lambda t: rec[t]) if ok else grid[-1]
        low = min([t for t in grid if rec[t] >= 0.98] or [grid[0]])
        high = max([t for t in grid if fpr[t] <= 0.01] or [grid[-1]])
        out[q] = {"low": min(low, thr), "high": max(high, thr), "threshold": thr}
    return out


def eval_set(agent, name, split, fit_split="val"):
    rows = _rows(name, split)
    pack = R.get(PACK[name])
    questions = pack["questions"]
    noul = [q for q, qq in questions.items() if qq["type"] == "noul"]
    thr = _fit_noul_thresholds(agent, _rows(name, fit_split), noul) if noul else {}

    per_q, confs, corrects, lat = {}, [], [], []
    preds = []
    for r in rows:
        t0 = time.perf_counter()
        res = agent.predict(r["state"], r["questions"])
        lat.append((time.perf_counter() - t0) * 1000)
        preds.append(_simplify(res))

    for qid, q in questions.items():
        t = q["type"]
        acc, brier = [], []
        m = {"type": t}
        if t == "noul":
            pos, neg = [], []
            for r, a in zip(rows, preds):
                if qid not in r["gold"]:
                    continue
                g = bool(r["gold"][qid]); p = a[qid]["p_true"]
                (pos if g else neg).append(p)
                acc.append(float((p >= 0.5) == g)); brier.append((p - g) ** 2)
                confs.append(max(p, 1 - p)); corrects.append(acc[-1])
            tcut = thr.get(qid, {}).get("threshold", 0.5)
            m.update(n=len(acc), auc=_auc(pos, neg), fn_at_05=sum(p < 0.5 for p in pos),
                     fp_at_05=sum(p >= 0.5 for p in neg),
                     fn_at_serving=sum(p < tcut for p in pos), fp_at_serving=sum(p >= tcut for p in neg),
                     n_pos=len(pos), n_neg=len(neg), threshold=tcut)
        elif t == "choice":
            for r, a in zip(rows, preds):
                if qid not in r["gold"]:
                    continue
                g = r["gold"][qid]
                acc.append(float(a[qid]["answer"] == g))
                probs = a[qid].get("probabilities") or {}
                confs.append(float(max(probs.values()) if probs else a[qid].get("confidence") or 0))
                corrects.append(acc[-1])
            m.update(n=len(acc))
        else:
            n = len(q["criteria"])
            for r, a in zip(rows, preds):
                if qid not in r["gold"]:
                    continue
                g = int(r["gold"][qid])
                probs = a[qid].get("probabilities") or {}
                # expected index via the simplified 'expected', argmax of probs for accuracy
                lvl = a[qid].get("answer")
                levels = q["criteria"]
                pred_idx = levels.index(lvl) if lvl in levels else 0
                acc.append(float(pred_idx == g))
                confs.append(float(a[qid].get("confidence") or 0)); corrects.append(acc[-1])
            m.update(n=len(acc))
        m["accuracy"] = float(np.mean(acc)) if acc else None
        m["brier"] = float(np.mean(brier)) if brier else None
        per_q[qid] = m

    out = {"n": len(rows), "questions": per_q, "thresholds": thr,
           "latency_p50_ms": float(np.percentile(lat, 50)), "latency_p95_ms": float(np.percentile(lat, 95)),
           "ece": _ece(confs, corrects),
           "macro_accuracy": float(np.mean([m["accuracy"] for m in per_q.values() if m["accuracy"] is not None]))}

    # false-block rate on clean examples
    if name in FLAGS:
        clean = [(r, a) for r, a in zip(rows, preds) if CLEAN_FAMILY[name](r["family"])]
        if clean:
            thrs = {q: thr.get(q, {}).get("threshold", 0.5) for q in FLAGS[name]}
            blocked05 = sum(any(a[q]["p_true"] >= 0.5 for q in FLAGS[name]) for _, a in clean)
            blockedS = sum(any(a[q]["p_true"] >= thrs[q] for q in FLAGS[name]) for _, a in clean)
            out["clean"] = {"n": len(clean), "false_block_rate_at_05": blocked05 / len(clean),
                            "false_block_rate_at_serving": blockedS / len(clean)}

    # routing accuracy
    if name == "route":
        top1_group = top1_tool = n_tool = 0
        per_group = {}
        for r, a in zip(rows, preds):
            gg = r["gold"].get("group")
            pg = a["group"]["answer"]
            top1_group += int(pg == gg)
            tq = f"tool_{gg}"
            if tq in r["gold"] and tq in a:                  # a group with a tool question
                n_tool += 1
                correct = int(a[tq]["answer"] == r["gold"][tq] and pg == gg)
                top1_tool += correct
                d = per_group.setdefault(gg, [0, 0]); d[0] += correct; d[1] += 1
        out["routing"] = {"group_top1": top1_group / len(rows),
                          "tool_top1": (top1_tool / n_tool) if n_tool else None,
                          "per_group_tool_acc": {g: round(c / n, 3) for g, (c, n) in sorted(per_group.items())}}
    return out


def _ece(conf, correct, bins=10):
    if not conf:
        return None
    conf, correct = np.array(conf), np.array(correct)
    e = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        m = (conf > lo) & (conf <= hi)
        if m.any():
            e += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(e)


def evaluate(agent, split="test"):
    report = {"split": split, "sets": {}}
    allc, alllat = [], []
    for name in SETS:
        r = eval_set(agent, name, split)
        report["sets"][name] = r
    report["overall"] = {
        "macro_accuracy": float(np.mean([report["sets"][s]["macro_accuracy"] for s in SETS])),
        "latency_p50_ms": float(np.mean([report["sets"][s]["latency_p50_ms"] for s in SETS])),
        "latency_p95_ms": float(np.max([report["sets"][s]["latency_p95_ms"] for s in SETS])),
    }
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", default="english", help="checkpoint dir or english|multilingual|typed-decisions")
    ap.add_argument("--split", default="test", choices=["train", "val", "test"])
    ap.add_argument("--url", help="score through a running laya.serve at this URL instead of loading weights")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--device")
    ap.add_argument("--out", help="write the full report JSON here")
    a = ap.parse_args()
    agent = _ServerAgent(a.url) if a.url else _LocalAgent(a.checkpoint, a.device or f"cuda:{a.gpu}")
    rep = evaluate(agent, a.split)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rep, f, indent=2, default=str)
    _print(rep)


def _print(rep):
    print(f"\n=== Ridgeback guard eval ({rep['split']} split) ===")
    for name, r in rep["sets"].items():
        print(f"\n[{name}] n={r['n']} macro_acc={r['macro_accuracy']:.3f} ece={r['ece']:.3f} "
              f"p50={r['latency_p50_ms']:.1f}ms p95={r['latency_p95_ms']:.1f}ms")
        for qid, m in r["questions"].items():
            extra = ""
            if m["type"] == "noul":
                extra = (f" auc={m['auc']:.3f}" if m["auc"] is not None else "") + \
                        f" fn/fp@serving={m['fn_at_serving']}/{m['fp_at_serving']} (thr={m['threshold']})"
            print(f"    {qid:16s} {m['type']:6s} acc={m['accuracy'] if m['accuracy'] is None else round(m['accuracy'],3)}{extra}")
        if "clean" in r:
            print(f"    clean false-block: @0.5={r['clean']['false_block_rate_at_05']:.3f} "
                  f"@serving={r['clean']['false_block_rate_at_serving']:.3f} (n={r['clean']['n']})")
        if "routing" in r:
            rt = r["routing"]
            print(f"    routing: group_top1={rt['group_top1']:.3f} tool_top1="
                  f"{rt['tool_top1'] and round(rt['tool_top1'],3)}")
            print(f"    per-group tool acc: {rt['per_group_tool_acc']}")
    o = rep["overall"]
    print(f"\n[overall] macro_acc={o['macro_accuracy']:.3f} p50~{o['latency_p50_ms']:.1f}ms p95<={o['latency_p95_ms']:.1f}ms")


if __name__ == "__main__":
    main()
