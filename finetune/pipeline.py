#!/usr/bin/env python3
"""One command per recipe: data -> baseline eval -> train/calibrate -> eval -> compare -> thresholds
-> (optional) register. MLflow tracks everything, with one parent run per invocation (experiment
`laya-<recipe>`) and nested child runs for each stage.

    python -m finetune.pipeline --recipe guard-output-leak
    python -m finetune.pipeline --recipe tool-call-safety --strategy full --epochs 4 --gpu 1
    python -m finetune.pipeline --recipe guard-input-injection --strategy calibrate   # cheapest
    python -m finetune.pipeline --all --strategy calibrate                            # smoke every recipe
    python -m finetune.pipeline --recipe guard-output-leak --data private_train.jsonl \\
        --extra-negatives private_clean_replies.jsonl --register

MLflow: MLFLOW_TRACKING_URI if set, else a local sqlite store in runs/mlflow.db
(`mlflow ui --backend-store-uri sqlite:///runs/mlflow.db` to browse).
Outputs: runs/<recipe>/<timestamp>/{checkpoint/, base_eval.json, finetuned_eval.json, comparison.md}
and finetune/recipes/<recipe>.thresholds.json (read by the MCP/guard at serving time).
"""
import argparse
import datetime as dt
import json
import os
import platform
import sys

from .common import (RECIPES_DIR, RUNS_DIR, dataset_paths, list_recipes, load_recipe, pack_for,
                     sha256_file, setup_mlflow)

COMPARE_KEYS = ["macro_accuracy", "ece", "any_auc", "any_fn_rate_at_05", "any_fp_rate_at_05",
                "any_fn_rate_at_serving", "any_fp_rate_at_serving", "hard_negative_fp_rate_at_05",
                "latency_p50_ms"]


def ensure_data(recipe):
    paths = dataset_paths(recipe)
    if all(os.path.exists(p) for p in paths.values()):
        return paths
    import importlib.util
    import subprocess
    ds_root = os.path.join(os.path.dirname(os.path.dirname(RECIPES_DIR)), "datasets")
    dataset = recipe.get("dataset", recipe["name"])
    if dataset.startswith("accelerators/"):       # industry accelerator sets have their own builder
        subprocess.run([sys.executable, os.path.join(ds_root, "accelerators", "build_all.py"),
                        dataset.split("/", 1)[1]], check=True)
    else:
        spec = importlib.util.spec_from_file_location("make_sets", os.path.join(ds_root, "make_sets.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if dataset not in mod.GENERATORS:
            raise SystemExit(f"no dataset at {os.path.dirname(paths['train'])} and no generator for '{dataset}'")
        print(f"[data] generated {recipe['name']}: {mod.build(dataset)}")
    return paths


def _metrics(prefix, summary):
    return {f"{prefix}{k}": float(v) for k, v in summary.items() if isinstance(v, (int, float)) and v is not None}


def _per_q_metrics(prefix, report):
    out = {}
    for qid, m in report["questions"].items():
        for k in ("accuracy", "brier", "auc", "mae", "within_1"):
            if m.get(k) is not None:
                out[f"{prefix}{qid}.{k}"] = float(m[k])
        if m["type"] == "noul":
            out[f"{prefix}{qid}.fn_at_05"] = float(m["fn_at_05"])
            out[f"{prefix}{qid}.fp_at_05"] = float(m["fp_at_05"])
    return out


def check_gates(gates, summary, per_q=None):
    results = {}
    for metric, rule in (gates or {}).items():
        v = summary.get(metric)
        if v is None and per_q and "." in metric:
            q, k = metric.split(".", 1)
            v = (per_q.get(q) or {}).get(k)
        ok = v is not None and ("min" not in rule or v >= rule["min"]) and ("max" not in rule or v <= rule["max"])
        results[metric] = {"value": v, **rule, "passed": bool(ok)}
    return all(r["passed"] for r in results.values()), results


def comparison_md(recipe, base_rep, ft_rep):
    lines = [f"# {recipe['name']} — base vs fine-tuned (test split, held-out phrasing families)", "",
             "| metric | base | fine-tuned |", "|---|---|---|"]
    for k in COMPARE_KEYS:
        b, f = (base_rep or {}).get("summary", {}).get(k), ft_rep["summary"].get(k)
        if b is None and f is None:
            continue
        fmt = (lambda x: "—" if x is None else f"{x:.3f}")
        lines.append(f"| {k} | {fmt(b)} | {fmt(f)} |")
    lines += ["", "| question | type | base acc | ft acc | base AUC | ft AUC |", "|---|---|---|---|---|---|"]
    for qid, m in ft_rep["questions"].items():
        bm = (base_rep or {}).get("questions", {}).get(qid, {})
        fmt = (lambda x: "—" if x is None else f"{x:.3f}")
        lines.append(f"| {qid} | {m['type']} | {fmt(bm.get('accuracy'))} | {fmt(m.get('accuracy'))} | "
                     f"{fmt(bm.get('auc'))} | {fmt(m.get('auc'))} |")
    fams = (ft_rep.get("any") or {}).get("by_family")
    if fams:
        bf = ((base_rep or {}).get("any") or {}).get("by_family", {})
        lines += ["", "| family (test) | gold | n | base fired@0.5 | ft fired@0.5 | ft fired@serving |",
                  "|---|---|---|---|---|---|"]
        for fam, v in sorted(fams.items()):
            lines.append(f"| {fam} | {'positive' if v['gold_positive'] else 'negative'} | {v['n']} | "
                         f"{bf.get(fam, {}).get('fired_at_05', '—')} | {v['fired_at_05']} | {v['fired_at_recommended']} |")
    return "\n".join(lines) + "\n"


def run_recipe(name, a):
    from . import evaluate as E
    from . import train as T

    recipe = load_recipe(name)
    strategy = a.strategy or recipe.get("strategy", "head")
    base = a.base or recipe.get("base", "english")
    device = a.device or f"cuda:{a.gpu}"
    paths = ensure_data(recipe)
    pack_for(recipe)                                   # fail fast if the pack is missing
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(a.out or os.path.join(RUNS_DIR, name), f"{stamp}-{strategy}")
    os.makedirs(out, exist_ok=True)
    ckpt = os.path.join(out, "checkpoint")
    over = {k: v for k, v in {"epochs": a.epochs, "micro_batch": a.micro_batch}.items() if v}

    mlflow = setup_mlflow(f"laya-{name}")
    with mlflow.start_run(run_name=f"{name}-{strategy}-{stamp}") as parent:
        import laya
        import torch
        counts = {s: sum(1 for _ in open(p)) for s, p in paths.items()}
        mlflow.log_params({"recipe": name, "strategy": strategy, "base": base, "pack": recipe.get("pack", name),
                           "laya_version": laya.__version__, "torch_version": torch.__version__,
                           "gpu": torch.cuda.get_device_name(device) if device.startswith("cuda") else "cpu",
                           "python": platform.python_version(), "extra_train_files": len(a.data),
                           **{f"rows_{s}": n for s, n in counts.items()},
                           **{f"sha256_{s}": sha256_file(p)[:16] for s, p in paths.items()}})
        mlflow.set_tags({"recipe": name, "strategy": strategy, "base": base})
        with open(os.path.join(out, "recipe.json"), "w") as f:
            json.dump(recipe, f, indent=2)
        mlflow.log_artifact(os.path.join(out, "recipe.json"))

        base_rep = None
        if not a.skip_baseline:
            with mlflow.start_run(run_name="baseline-eval", nested=True):
                base_rep = E.evaluate(recipe, base, "test", device, a.extra_negatives)
                mlflow.log_metrics({**_metrics("", base_rep["summary"]), **_per_q_metrics("", base_rep)})
                _dump(out, "base_eval.json", base_rep, mlflow)
            mlflow.log_metrics(_metrics("base_", base_rep["summary"]))
            print(f"[baseline] {json.dumps(base_rep['summary'])}", flush=True)

        with mlflow.start_run(run_name=f"train-{strategy}", nested=True):
            stats = T.run(recipe, ckpt, strategy, base, device, over,
                          log_metric=lambda k, v, s: mlflow.log_metric(k, v, step=s), extra_data=a.data)
            hp = stats.pop("hyperparams")
            mlflow.log_params({f"hp_{k}": v for k, v in hp.items()})
            mlflow.log_params({"base_revision": stats.get("base_revision") or "local"})
            mlflow.log_metrics({k: float(v) for k, v in stats.items() if isinstance(v, (int, float))})
            mlflow.log_dict({"temperatures": stats["temperatures"], "order": ["choice", "score", "noul"]},
                            "temperatures.json")
            mlflow.log_artifact(os.path.join(ckpt, "rl_agent_config.json"))

        with mlflow.start_run(run_name="finetuned-eval", nested=True):
            ft_rep = E.evaluate(recipe, ckpt, "test", device, a.extra_negatives)
            mlflow.log_metrics({**_metrics("", ft_rep["summary"]), **_per_q_metrics("", ft_rep)})
            _dump(out, "finetuned_eval.json", ft_rep, mlflow)
        mlflow.log_metrics(_metrics("ft_", ft_rep["summary"]))
        if base_rep:
            mlflow.log_metrics({f"delta_{k}": float(ft_rep["summary"][k] - base_rep["summary"][k])
                                for k in COMPARE_KEYS if isinstance(ft_rep["summary"].get(k), (int, float))
                                and isinstance(base_rep["summary"].get(k), (int, float))})
        for which, rep in (("base", base_rep), ("ft", ft_rep)):
            if rep and rep.get("extra_negatives"):
                xn = rep["extra_negatives"]
                mlflow.log_metrics({f"{which}_extra_neg_fp_rate_at_05": xn["any_fp_rate_at_05"],
                                    f"{which}_extra_neg_fp_rate_at_threshold": xn["any_fp_rate_at_threshold"]})

        md = comparison_md(recipe, base_rep, ft_rep)
        with open(os.path.join(out, "comparison.md"), "w") as f:
            f.write(md)
        mlflow.log_artifact(os.path.join(out, "comparison.md"))
        passed, gate_res = check_gates(recipe.get("gates"), ft_rep["summary"], ft_rep["questions"])
        mlflow.log_dict(gate_res, "gates.json")
        mlflow.set_tag("gates_passed", str(passed))

        rel = os.path.relpath(ckpt, RUNS_DIR) if os.path.abspath(ckpt).startswith(os.path.abspath(RUNS_DIR)) else os.path.basename(ckpt)
        thr = {"_meta": {"recipe": name, "checkpoint": f"runs/{rel}", "strategy": strategy, "base": base,
                         "fitted_on": ft_rep.get("fitted_on"), "gates_passed": passed,
                         "mlflow_run_id": parent.info.run_id, "created": stamp},
               **ft_rep["serving_thresholds"]}
        _dump(out, "thresholds.json", thr, mlflow)
        if passed or a.force_thresholds:
            with open(os.path.join(RECIPES_DIR, f"{name}.thresholds.json"), "w") as f:
                json.dump(thr, f, indent=2)
        else:
            print(f"[gates] FAILED; not updating recipes/{name}.thresholds.json (use --force-thresholds)")

        if a.register:
            from .mlflow_model import log_model
            ex_row = json.loads(open(paths["test"]).readline())
            info = log_model(mlflow, ckpt, registered_name=f"laya-{name}",
                             example={"state": ex_row["state"], "questions": ex_row["questions"]})
            mlflow.set_tag("model_uri", info.model_uri)
        elif not a.no_log_checkpoint:
            mlflow.log_artifacts(ckpt, artifact_path="checkpoint")

        print(md)
        print(f"[gates] passed={passed} {json.dumps({k: v['value'] for k, v in gate_res.items()})}")
        print(f"[mlflow] experiment=laya-{name} run_id={parent.info.run_id} uri={mlflow.get_tracking_uri()}")
        print(f"[checkpoint] {os.path.abspath(ckpt)}")
        return {"recipe": name, "run_id": parent.info.run_id, "checkpoint": ckpt, "gates_passed": passed,
                "base": base_rep["summary"] if base_rep else None, "finetuned": ft_rep["summary"]}


def _dump(out, fname, obj, mlflow):
    p = os.path.join(out, fname)
    with open(p, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    mlflow.log_artifact(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--recipe", help="recipe name (see --list) or path to a recipe JSON")
    g.add_argument("--all", action="store_true", help="run every recipe")
    g.add_argument("--list", action="store_true")
    ap.add_argument("--strategy", choices=["full", "head", "calibrate"], help="override the recipe's strategy")
    ap.add_argument("--base", help="english | multilingual | typed-decisions | checkpoint dir")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--micro-batch", type=int)
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--device")
    ap.add_argument("--data", action="append", default=[], help="extra train JSONL (repeatable; e.g. private rows)")
    ap.add_argument("--extra-negatives", help="JSONL of known-clean states to measure false positives on")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--register", action="store_true", help="log + register an MLflow pyfunc model")
    ap.add_argument("--no-log-checkpoint", action="store_true", help="don't copy weights into MLflow artifacts")
    ap.add_argument("--force-thresholds", action="store_true", help="write thresholds even if gates fail")
    ap.add_argument("--out", help="runs root for this invocation (default runs/<recipe>/)")
    a = ap.parse_args()
    if a.list:
        for n in list_recipes():
            print(f"{n:24s} {load_recipe(n).get('description', '')[:90]}")
        return
    names = list_recipes() if a.all else [a.recipe]
    results = [run_recipe(n, a) for n in names]
    if len(results) > 1:
        print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
