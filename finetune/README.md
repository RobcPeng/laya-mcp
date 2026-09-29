# Fine-tuning Laya: recipes, pipeline, MLflow

Laya's base checkpoints are fast but, in the upstream authors' words, "a fast base to specialise,
not a zero-shot decision engine". This directory turns that specialisation into one command per
use case: generate or load data, evaluate the base, train or calibrate, evaluate again, compare,
fit serving thresholds and (optionally) register the model. MLflow tracks every step.

```bash
pip install "laya>=0.3.21" mlflow safetensors pandas      # torch with CUDA for training
export USE_TF=0                                           # transformers' TF probe can deadlock laya

python -m finetune.pipeline --list
python -m finetune.pipeline --recipe guard-output-leak                 # full fine-tune (recipe default)
python -m finetune.pipeline --recipe tool-call-safety --gpu 1
python -m finetune.pipeline --recipe guard-input-injection --strategy calibrate   # cheapest
python -m finetune.pipeline --all --strategy calibrate                 # smoke every recipe
python -m finetune.pipeline --recipe guard-output-leak \
    --data datasets/private/my_rows.private.jsonl \
    --extra-negatives datasets/private/my_clean_replies.private.jsonl --register
```

Run from the repository root. Stage-by-stage entry points: `python -m finetune.train`,
`python -m finetune.evaluate`, `python datasets/make_sets.py`.

## Recipes

A recipe (`recipes/<name>.json`) is declarative:

```json
{"name": "tool-call-safety", "pack": "tool-call-safety", "dataset": "tool-call-safety",
 "base": "english", "strategy": "full",
 "hyperparams": {"epochs": 4}, "head_hyperparams": {"lr_head": 0.0005, "epochs": 6},
 "eval": {"fp_budget": 0.05, "recall_target": 0.98, "aggregate": false},
 "gates": {"macro_accuracy": {"min": 0.7}},
 "serving": "Before executing a call: risk>=2 or exfiltration -> confirm or refuse ..."}
```

- `pack` names the question pack in `laya_mcp/packs.py`. It is the single source of question
  wording for training and for the MCP / tool-call / guard surfaces. Recipes never define their
  own wording, so a fine-tuned checkpoint is asked exactly what it learned.
- `base`: `english` (ModernBERT-large, 512 ctx), `multilingual`, `typed-decisions` (already
  fine-tuned on agent traces, customer service, invoices and security incidents), or a local
  checkpoint directory.
- `eval.aggregate`: the noul questions that all mean "bad", combined row-wise as "flag if any
  fires" (default every noul; `false` for packs with mixed polarity such as `matches_request`).
- `gates`: metric → `{min|max}` checked on the fine-tuned test report. A failing gate tags the
  MLflow run `gates_passed=False` and does not overwrite `recipes/<name>.thresholds.json`
  (`--force-thresholds` to write anyway).

Core recipes (datasets in `datasets/`, see `datasets/README.md`): `guard-output-leak`,
`guard-input-injection`, `guard-pii-secrets`, `scope-and-harm`, `tool-routing`,
`tool-call-safety`, `tool-result-injection`, `agent-trace-judge`. The industry accelerator
recipes (support triage, 311 intake, FOIA routing, higher-ed, SOC triage and more) use datasets
from `datasets/accelerators/`, built by their own `build_all.py`.

## Strategies

| strategy | trains | VRAM (measured, RTX 3090) | time, ~2.2k items × 3 epochs | use when |
|---|---|---|---|---|
| `full` | encoder (2.5e-5) + decision head (1e-4) | ~9 GB peak | ~90 s | the default; the task needs distinctions the encoder doesn't draw yet |
| `head` | decision head only, encoder frozen | ~3 GB peak | ~30 s | tiny data, weak GPU, or re-fitting boundaries the base already separates |
| `calibrate` | nothing; fits temperatures + thresholds | inference only | seconds | fixing over-confidence and choosing thresholds on the base model |

The training loop adapts the upstream RLCD recipe (laya's fine-tuning notebook) to a single GPU.
It runs a GRPO-style policy gradient over noisy logits, scored by laya's `proper_reward`, plus
soft cross-entropy guidance. It uses a cosine schedule, gradient checkpointing, bf16 autocast (fp16
with a GradScaler where bf16 is unavailable) and label smoothing (0.05 by default). After training,
one temperature per question type is fitted on the val split, which is never trained on, and
written to `rl_agent_config.json`. Inherited `temperature_by_options` are removed so they cannot
mask the new fit. The exported directory loads with `laya.Agent(dir)` / `laya.load(dir)`.

## What gets tracked in MLflow

Experiment `laya-<recipe>`, one parent run per invocation, with nested child runs
`baseline-eval`, `train-<strategy>` and `finetuned-eval`.

- params: recipe, strategy, base, base revision, every hyperparameter, dataset row counts and
  SHA-256 per split, laya/torch/python versions, GPU
- metrics: per-update `train_loss`, `train_ce`, `train_reward`, `lr_head`; per-epoch loss/reward;
  peak VRAM; `base_*`, `ft_*` and `delta_*` summaries; per-question accuracy, Brier, AUC, FN/FP
- artifacts: `recipe.json`, `base_eval.json`, `finetuned_eval.json` (full threshold tables,
  confusion matrices, per-family breakdown), `comparison.md`, `gates.json`, `temperatures.json`,
  `thresholds.json`, `rl_agent_config.json`, and the checkpoint (skip with `--no-log-checkpoint`)
- `--register` logs an MLflow pyfunc model (`finetune/mlflow_model.py`) wrapping the
  checkpoint and registers it as `laya-<recipe>`. Input: a DataFrame with `state` and `questions`
  (JSON strings or dicts); output: one laya result JSON per row. Serve it with
  `mlflow models serve -m models:/laya-<recipe>/1` or load it with `mlflow.pyfunc.load_model`.

Tracking URI: `MLFLOW_TRACKING_URI` if set; otherwise a local sqlite store at `runs/mlflow.db`,
with artifacts in `runs/mlartifacts` (`mlflow ui --backend-store-uri sqlite:///runs/mlflow.db`).
`LAYA_FT_RUNS` moves the whole `runs/` root; `MLFLOW_ARTIFACT_ROOT` sets the artifact location for
newly created experiments. With `--register` the checkpoint is stored inside the logged model, so it
is not logged a second time as a plain artifact. Calibrate-only runs export the base weights
unchanged (hardlinked when on the same filesystem, otherwise copied), so the exported directory is
self-contained.

A throwaway end-to-end check that keeps runs and MLflow state out of the repo (a run that passes its
gates still writes `recipes/<name>.thresholds.json`; calibrating the base model on this recipe scores
about 0.69 against its 0.7 gate, so it does not):

```bash
export USE_TF=0 LAYA_FT_RUNS=/tmp/laya-ft-smoke
export MLFLOW_TRACKING_URI=sqlite:////tmp/laya-ft-smoke/mlflow.db MLFLOW_ARTIFACT_ROOT=file:///tmp/laya-ft-smoke/mlartifacts
python -m finetune.pipeline --recipe tool-call-safety --strategy calibrate --skip-baseline --register --gpu 0
python -c "import mlflow; print(mlflow.pyfunc.load_model('models:/laya-tool-call-safety/1'))"
```

Other flags: `--device cpu` (or any torch device; overrides `--gpu`), `--out DIR` (runs root for
this invocation), `--epochs`, `--micro-batch`, `--base`.

## Evaluation

`evaluate.py` scores through `laya.Agent.predict`, the same path the server uses:

- per question: accuracy, Brier, ECE; choice → confusion matrix; score → MAE of the expected
  level and within-1 accuracy; noul → AUC and FN/FP across thresholds 0.05–0.95
- row-level `_any` aggregate and a per-family breakdown of the test split. Hard-negative
  families (`clean/topic_*`) report their own false-positive rate
  (`hard_negative_fp_rate_at_05`).
- serving thresholds fitted on val, then scored on the held-out test split (`any_fn_rate_at_serving`,
  `any_fp_rate_at_serving`)
- `--extra-negatives FILE`: false-positive rate on your own known-clean data

### Serving thresholds

`recipes/<name>.thresholds.json` (gitignored, since it points at a local checkpoint), per noul question
plus `_any`:

```json
{"_meta": {"checkpoint": "runs/...", "gates_passed": true, "mlflow_run_id": "..."},
 "exfiltration": {"threshold": 0.5, "low": 0.31, "high": 0.62}, "_any": {"...": "..."}}
```

`threshold` gives maximum recall within the recipe's false-positive budget. A guard allows
below `low`, blocks above `high`, and escalates in between, for example to an LLM judge.

## Serving a fine-tuned checkpoint

`laya.serve` only knows the three published checkpoint names, but its Router accepts a local
directory for any of them. `finetune/serve.py` puts your checkpoint in a slot (default
`typed-decisions`), so the stock auto-routing (english/multilingual) is unchanged and only
requests that name the slot reach your model:

```bash
LAYA_CUSTOM_CHECKPOINT=runs/tool-call-safety/<stamp>-full/checkpoint \
LAYA_HOST=127.0.0.1 LAYA_PORT=7492 LAYA_MODELS=typed-decisions python -m finetune.serve
# POST /v1/systemone {"model": "typed-decisions", "state": {...}, "questions": <the pack's questions>}
```

Run one server per fine-tuned checkpoint, each on its own port, separate from the server that
answers with the base model; `laya_mcp.client.predict(..., url=...)` targets a specific one.
`LAYA_CUSTOM_SLOT=english` instead makes the checkpoint answer every English request.

## Tool routing over large catalogs

Choice accuracy falls off sharply beyond about 20 options, so the `tool-routing` pack refuses
catalogs over 20. For bigger MCP catalogs, shortlist by embedding similarity first, then ask Laya
over the top `k`:

```python
import laya
from laya import predict_shortlist, embed_fn_from_agent, cached_embed_fn
from laya_mcp import packs

agent = laya.load("convaiinnovations/laya")          # or your fine-tuned checkpoint dir
pack = packs.get_pack("tool-routing", tools=big_catalog)  # raises if > 20; build questions yourself for more
embed = cached_embed_fn(embed_fn_from_agent(agent))
res = predict_shortlist(agent, {"request": text}, pack["questions"], embed, k=12)
```

Or split the catalog into a coarse question (tool family) followed by a fine one.

## Measured results (RTX 3090, synthetic sets, held-out phrasing families on test)

`guard-output-leak`, base `english`, `full`, 3 epochs, 2,240 training items, 88 s:

| metric (test, 301 rows) | base | fine-tuned |
|---|---|---|
| row-level AUC (any leak) | 0.674 | 0.984 |
| missed leaks @0.5 | 74.3% | 2.8% |
| false positives @0.5 | 26.6% | 10.9% |
| false positives on hard negatives (topic families) @0.5 | 35.9% | 14.8% |
| macro accuracy | 0.892 | 0.982 |
| latency p50 | 20 ms | 20 ms |

Remaining false positives come almost entirely from one unseen family: generic tech explainers
("most chatbots are a language model plus a prompt"). The `head` strategy on the same data only
reached AUC 0.67–0.75, which is why `full` is the default.

`tool-call-safety`, base `english`, `full`, 4 epochs: macro accuracy 0.687 → 0.896,
`matches_request` 0.849 → 0.993, `side_effect` 0.755 → 1.000, `exfiltration` 0.863 → 1.000,
`risk` (4-level score, exact) 0.281 → 0.590.

Calibrate-only smoke runs (base model, temperatures only) for the other recipes, as test macro
accuracy: input-injection 0.76, pii-secrets 0.87, scope-and-harm 0.50, tool-routing 0.55,
tool-result-injection 0.79, agent-trace-judge 0.72 (typed-decisions base). These are baselines to
beat with `full`.

## Caveats

- **Synthetic data.** The sets are templated. Held-out families make the test honest about
  phrasing, but not about your traffic's distribution. Add your own rows (`--data`) and measure
  false positives on your own clean data (`--extra-negatives`) before trusting a guard.
- **Val-fitted thresholds are optimistic.** Val shares families with train, so a fine-tuned model
  often separates val perfectly. The noul temperature then fits at the 0.5 clamp and `low`/`high`
  collapse to one value (no escalation band). Refit thresholds on data closer to production, for
  example your own labelled rows as a val split, and check `any_*_at_serving` on test.
- **Label wording is part of the model.** Change a pack's instruction text and you must retrain.
  Checkpoints trained on older wording keep working, but only on the wording they learned.
- **bf16 vs fp16 moves probabilities** by a few hundredths (upstream measurement). Fit and serve
  thresholds under the same dtype and device.
- Choice questions stay at 20 options or fewer. Avoid true/false/yes/no as choice labels.
