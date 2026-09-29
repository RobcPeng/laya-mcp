#!/usr/bin/env python3
"""Evaluate a Laya checkpoint (base or fine-tuned) on a recipe split, through `laya.Agent.predict`
(the same code path the server uses), and fit serving thresholds.

Per question:   accuracy, Brier, ECE; choice -> confusion; score -> MAE of expected level, within-1;
                noul -> FN/FP rates across thresholds, AUC, and a recommended threshold
                (maximum recall at a false-positive budget).
Per row:        `_any` aggregate over the noul questions (flag the row if ANY question fires), which
                is how a guard uses a pack. Also broken down by phrasing family, so hard-negative
                families (e.g. "clean/topic_*") show their own false-positive rate.
Extra negatives: --extra-negatives FILE.jsonl, rows known to be clean (e.g. your own real traffic,
                kept out of the public repo). Each line is {"state": {...}} or just the state
                object; every noul answer should be false. Reports FP at the chosen thresholds.

    python -m finetune.evaluate --recipe guard-output-leak --checkpoint english --split test
    python -m finetune.evaluate --recipe guard-output-leak --checkpoint runs/leak/checkpoint \\
        --split test --extra-negatives my_real_replies.jsonl --fit-thresholds-on val
"""
import argparse
import json
import os
import time

import numpy as np

from .common import dataset_paths, load_recipe, load_rows, read_jsonl, resolve_base

THRESHOLDS = [round(x, 2) for x in np.arange(0.05, 1.0, 0.05)]


def load_agent(checkpoint, device):
    from laya.agent import Agent
    ckpt_dir, _ = resolve_base(checkpoint)
    return Agent(ckpt_dir, device=device), ckpt_dir


def predict_rows(agent, rows, questions=None):
    """[(answers, latency_ms)] per row; `questions` overrides the row's own (extra-negatives)."""
    out = []
    for r in rows:
        qs = questions or r["questions"]
        t0 = time.perf_counter()
        res = agent.predict(r["state"], qs)
        out.append((res["answers"], (time.perf_counter() - t0) * 1000))
    return out


def _auc(pos, neg):
    if not pos or not neg:
        return None
    s = np.array(pos)[:, None]
    n = np.array(neg)[None, :]
    return float(((s > n).sum() + 0.5 * (s == n).sum()) / (len(pos) * len(neg)))


def threshold_table(pos, neg):
    rows = []
    for t in THRESHOLDS:
        fn = sum(p < t for p in pos)
        fp = sum(p >= t for p in neg)
        rows.append({"t": t, "fn": fn, "fp": fp, "recall": (1 - fn / len(pos)) if pos else None,
                     "fp_rate": (fp / len(neg)) if neg else None})
    return rows


def recommend(pos, neg, fp_budget=0.05, recall_target=0.98):
    """Serving thresholds for one noul question (or the row-level aggregate):
       threshold  max recall with fp_rate <= fp_budget; ties -> middle of the tied range, so a cleanly
                  separable val set doesn't pin the cut-off against the top of the scale.
       low        below it: confidently clean (middle of the range that still keeps recall_target).
       high       above it: confidently positive (middle of the range where fp_rate <= 1%).
    A guard allows below `low`, blocks above `high`, and escalates in between."""
    if not pos or not neg:
        return {"threshold": 0.5, "low": 0.5, "high": 0.5, "note": "no positives or negatives to fit on"}
    grid = [x / 100 for x in range(1, 100)]
    rec = {t: sum(p >= t for p in pos) / len(pos) for t in grid}
    fpr = {t: sum(p >= t for p in neg) / len(neg) for t in grid}
    mid = (lambda ts: ts[len(ts) // 2])
    ok = [t for t in grid if fpr[t] <= fp_budget]
    if ok:
        best = max(rec[t] for t in ok)
        thr = mid([t for t in ok if rec[t] == best])
    else:
        thr = grid[-1]
    low_range = [t for t in grid if rec[t] >= recall_target] or [grid[0]]
    high_range = [t for t in grid if fpr[t] <= 0.01] or [grid[-1]]
    return {"threshold": thr, "low": min(mid(low_range), thr), "high": max(mid(high_range), thr),
            "val_recall_at_threshold": rec[thr], "val_fp_rate_at_threshold": fpr[thr]}


def score_split(rows, preds, recipe_eval=None):
    ev = recipe_eval or {}
    fp_budget, recall_target = ev.get("fp_budget", 0.05), ev.get("recall_target", 0.98)
    qs = rows[0]["questions"]
    per_q, confs, corrects = {}, [], []
    for qid, q in qs.items():
        t = q["type"]
        acc, brier = [], []
        m = {"type": t}
        if t == "noul":
            pos, neg = [], []
            for r, (ans, _) in zip(rows, preds):
                if qid not in r["gold"]:
                    continue
                g = r["gold"][qid]
                g = float(g) >= 0.5 if not isinstance(g, bool) else g
                p = ans[qid]["noul"]
                (pos if g else neg).append(p)
                acc.append(float((p >= 0.5) == g))
                brier.append((p - float(g)) ** 2)
                confs.append(max(p, 1 - p))
                corrects.append(acc[-1])
            m.update(n=len(acc), n_pos=len(pos), n_neg=len(neg), auc=_auc(pos, neg),
                     thresholds=threshold_table(pos, neg), recommended=recommend(pos, neg, fp_budget, recall_target),
                     fn_at_05=sum(p < 0.5 for p in pos), fp_at_05=sum(p >= 0.5 for p in neg))
        elif t == "choice":
            keys = list(q["criteria"])
            conf_m = {g: {k: 0 for k in keys} for g in keys}
            for r, (ans, _) in zip(rows, preds):
                if qid not in r["gold"]:
                    continue
                g, a = r["gold"][qid], ans[qid]
                conf_m[g][a["choice"]] += 1
                acc.append(float(a["choice"] == g))
                probs = np.array([a["probabilities"].get(k, 0.0) for k in keys])
                onehot = np.array([1.0 if k == g else 0.0 for k in keys])
                brier.append(float(((probs - onehot) ** 2).sum()))
                confs.append(float(probs.max()))
                corrects.append(acc[-1])
            m.update(n=len(acc), confusion=conf_m)
        elif t == "score":
            n = len(q["criteria"])
            mae, w1 = [], []
            for r, (ans, _) in zip(rows, preds):
                if qid not in r["gold"]:
                    continue
                g, a = int(r["gold"][qid]), ans[qid]
                probs = np.array([a["probabilities"].get(str(i), 0.0) for i in range(n)])
                lvl = int(probs.argmax())
                acc.append(float(lvl == g))
                mae.append(abs(a["score"] - g))
                w1.append(float(abs(lvl - g) <= 1))
                onehot = np.eye(n)[g]
                brier.append(float(((probs - onehot) ** 2).sum()))
                confs.append(float(probs.max()))
                corrects.append(acc[-1])
            m.update(n=len(acc), mae=float(np.mean(mae)) if mae else None,
                     within_1=float(np.mean(w1)) if w1 else None)
        m["accuracy"] = float(np.mean(acc)) if acc else None
        m["brier"] = float(np.mean(brier)) if brier else None
        per_q[qid] = m

    # row-level "any noul fires" aggregate + per-family breakdown
    # recipe eval.aggregate: list of noul qids that all mean "bad" (default: every noul), or false
    agg_cfg = ev.get("aggregate", True)
    noul_q = [k for k, q in qs.items() if q["type"] == "noul"] if agg_cfg is True else list(agg_cfg or [])
    agg = None
    if noul_q:
        thr = {k: per_q[k]["recommended"]["threshold"] for k in noul_q}
        pos, neg, fams = [], [], {}
        for r, (ans, _) in zip(rows, preds):
            gold_any = any((r["gold"].get(k) is True) or (not isinstance(r["gold"].get(k), bool)
                           and r["gold"].get(k) is not None and float(r["gold"][k]) >= 0.5) for k in noul_q)
            pmax = max(ans[k]["noul"] for k in noul_q)
            fired_05 = pmax >= 0.5
            fired_rec = any(ans[k]["noul"] >= thr[k] for k in noul_q)
            (pos if gold_any else neg).append(pmax)
            fam = r.get("family", "?").rsplit("/", 1)[0]
            f = fams.setdefault(fam, {"n": 0, "gold_positive": gold_any, "fired_at_05": 0, "fired_at_recommended": 0})
            f["n"] += 1
            f["fired_at_05"] += int(fired_05)
            f["fired_at_recommended"] += int(fired_rec)
        agg = {"n_pos": len(pos), "n_neg": len(neg), "auc": _auc(pos, neg),
               "fn_at_05": sum(p < 0.5 for p in pos), "fp_at_05": sum(p >= 0.5 for p in neg),
               "thresholds": threshold_table(pos, neg), "recommended": recommend(pos, neg, fp_budget, recall_target),
               "by_family": fams}
    from laya.common import ece_score
    lat = [ms for _, ms in preds]
    summary = {
        "rows": len(rows),
        "macro_accuracy": float(np.mean([m["accuracy"] for m in per_q.values() if m["accuracy"] is not None])),
        "ece": ece_score(np.array(confs), np.array(corrects)),
        "latency_p50_ms": float(np.percentile(lat, 50)), "latency_p95_ms": float(np.percentile(lat, 95)),
    }
    if agg:
        summary.update(any_auc=agg["auc"], any_fn_at_05=agg["fn_at_05"], any_fp_at_05=agg["fp_at_05"],
                       any_fn_rate_at_05=agg["fn_at_05"] / max(1, agg["n_pos"]),
                       any_fp_rate_at_05=agg["fp_at_05"] / max(1, agg["n_neg"]))
        hard = {k: v for k, v in agg["by_family"].items() if not v["gold_positive"] and "topic" in k}
        if hard:
            n = sum(v["n"] for v in hard.values())
            summary["hard_negative_fp_rate_at_05"] = sum(v["fired_at_05"] for v in hard.values()) / n
    return {"summary": summary, "questions": per_q, "any": agg}


def extra_negatives(agent, path, questions, thresholds):
    """FP on known-clean rows. `thresholds` = {qid: t} (noul only)."""
    raw = read_jsonl(path)
    rows = [{"state": r.get("state", r)} for r in raw]
    preds = predict_rows(agent, rows, questions)
    noul = [k for k, q in questions.items() if q["type"] == "noul"]
    per_q = {k: {"fp_at_05": sum(a[k]["noul"] >= 0.5 for a, _ in preds),
                 "fp_at_threshold": sum(a[k]["noul"] >= thresholds.get(k, 0.5) for a, _ in preds)} for k in noul}
    any05 = sum(any(a[k]["noul"] >= 0.5 for k in noul) for a, _ in preds)
    anyt = sum(any(a[k]["noul"] >= thresholds.get(k, 0.5) for k in noul) for a, _ in preds)
    return {"rows": len(rows), "any_fp_at_05": any05, "any_fp_rate_at_05": any05 / max(1, len(rows)),
            "any_fp_at_threshold": anyt, "any_fp_rate_at_threshold": anyt / max(1, len(rows)), "questions": per_q}


def thresholds_from(report):
    """Serving thresholds JSON: {qid: {threshold, low, high}} per noul + `_any` aggregate."""
    out = {k: m["recommended"] for k, m in report["questions"].items() if m["type"] == "noul" and "recommended" in m}
    if report.get("any"):
        out["_any"] = report["any"]["recommended"]
    return out


def evaluate(recipe, checkpoint, split="test", device="cuda:0", extra_neg=None, fit_on=None, agent=None):
    """Full evaluation. `fit_on` = split to fit thresholds on (default val); returns report dict."""
    paths = dataset_paths(recipe)
    rows = load_rows(paths[split], recipe)
    own_agent = agent is None
    if own_agent:
        agent, _ = load_agent(checkpoint, device)
    preds = predict_rows(agent, rows)
    report = score_split(rows, preds, recipe.get("eval"))
    report["split"] = split
    report["checkpoint"] = checkpoint
    fit_on = fit_on or "val"
    if fit_on != split and os.path.exists(paths[fit_on]):
        vrows = load_rows(paths[fit_on], recipe)
        report["fitted_on"] = fit_on
        report["serving_thresholds"] = thresholds_from(score_split(vrows, predict_rows(agent, vrows), recipe.get("eval")))
    else:
        report["fitted_on"] = split
        report["serving_thresholds"] = thresholds_from(report)
    # score the eval split at the serving thresholds (fit on another split) for an honest number
    st = report["serving_thresholds"]
    agg_cfg = (recipe.get("eval") or {}).get("aggregate", True)
    noul = ([k for k, q in rows[0]["questions"].items() if q["type"] == "noul"] if agg_cfg is True
            else list(agg_cfg or []))
    if noul:
        thr = {k: st[k]["threshold"] for k in noul if k in st}
        fn = fp = npos = nneg = 0
        for r, (ans, _) in zip(rows, preds):
            gold_any = any(r["gold"].get(k) is True for k in noul)
            fired = any(ans[k]["noul"] >= thr.get(k, 0.5) for k in noul)
            npos += gold_any
            nneg += not gold_any
            fn += gold_any and not fired
            fp += (not gold_any) and fired
        report["summary"].update(any_fn_at_serving=fn, any_fp_at_serving=fp,
                                 any_fn_rate_at_serving=fn / max(1, npos), any_fp_rate_at_serving=fp / max(1, nneg))
    if extra_neg:
        report["extra_negatives"] = extra_negatives(agent, extra_neg, rows[0]["questions"],
                                                    {k: v["threshold"] for k, v in st.items() if k != "_any"})
    if own_agent:
        del agent
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--checkpoint", default="english", help="checkpoint dir or english|multilingual|typed-decisions")
    ap.add_argument("--split", default="test", choices=["train", "val", "test"])
    ap.add_argument("--fit-thresholds-on", default="val", choices=["train", "val", "test"])
    ap.add_argument("--extra-negatives", help="JSONL of known-clean states (kept private)")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--device")
    ap.add_argument("--out", help="write the full report JSON here")
    a = ap.parse_args()
    rep = evaluate(load_recipe(a.recipe), a.checkpoint, a.split, a.device or f"cuda:{a.gpu}",
                   a.extra_negatives, a.fit_thresholds_on)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rep, f, indent=2, default=str)
    print(json.dumps({"summary": rep["summary"], "serving_thresholds": rep["serving_thresholds"],
                      "extra_negatives": rep.get("extra_negatives")}, indent=2, default=str))


if __name__ == "__main__":
    main()
