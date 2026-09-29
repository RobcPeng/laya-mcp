"""Shared helpers for the fine-tune pipeline: base checkpoint resolution, MLflow setup, JSONL IO,
recipe loading and the question -> internal-question conversion that must match inference exactly."""
import hashlib
import json
import os
import sys

os.environ.setdefault("USE_TF", "0")        # transformers probing TF can deadlock model construction

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

RECIPES_DIR = os.path.join(REPO_ROOT, "finetune", "recipes")
DATASETS_DIR = os.path.join(REPO_ROOT, "datasets")
RUNS_DIR = os.environ.get("LAYA_FT_RUNS", os.path.join(REPO_ROOT, "runs"))

BUNDLE_REPO = "convaiinnovations/laya"
BASES = {                                   # name -> (hub repo, subfolder); mirrors laya.router
    "english": (BUNDLE_REPO, None),
    "multilingual": (BUNDLE_REPO, "multilingual"),
    "typed-decisions": (BUNDLE_REPO, "typed-decisions"),
}
QTYPE_IDX = {"choice": 0, "score": 1, "noul": 2}
TEMP_MIN, TEMP_MAX = 0.5, 5.0               # laya clamps loaded temperatures to this range


def resolve_base(spec):
    """Base checkpoint spec -> (local checkpoint dir, revision or None).
    spec: 'english' | 'multilingual' | 'typed-decisions' | a local checkpoint dir | 'repo[:subfolder]'."""
    if os.path.isdir(spec):
        return os.path.abspath(spec), None
    repo, sub = BASES.get(spec) or (tuple(spec.split(":", 1)) if ":" in spec else (spec, None))
    from huggingface_hub import snapshot_download
    from laya.revisions import snapshot_revision
    prefix = f"{sub}/" if sub else ""
    snap = snapshot_download(repo, allow_patterns=[prefix + p for p in (
        "rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")])
    rev = snapshot_revision(snap)
    return (os.path.join(snap, sub) if sub else snap), rev


def load_base_cfg(model_dir):
    with open(os.path.join(model_dir, "rl_agent_config.json")) as f:
        return json.load(f)


def load_tokenizer(model_dir, cfg):
    from laya.agent import _fix_tokenizer_config, _load_tokenizer
    _fix_tokenizer_config(model_dir)
    return _load_tokenizer(os.path.join(model_dir, "tokenizer"), cfg)


def to_internal(q):
    """Public question dict -> the internal form laya.common.build_sequence expects."""
    out = {"t": q["type"], "ins": q["instructions"], "crit": q.get("criteria")}
    if q["type"] == "noul" and q.get("labels"):
        out["labels"] = q["labels"]
    return out


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_recipe(name_or_path):
    path = name_or_path if name_or_path.endswith(".json") else os.path.join(RECIPES_DIR, f"{name_or_path}.json")
    with open(path) as f:
        r = json.load(f)
    r.setdefault("name", os.path.splitext(os.path.basename(path))[0])
    return r


def list_recipes():
    return sorted(f[:-5] for f in os.listdir(RECIPES_DIR)
                  if f.endswith(".json") and not f.endswith((".thresholds.json", ".questions.json")))


def pack_for(recipe):
    """The laya_mcp question pack a recipe trains (single source of question wording)."""
    from laya_mcp import packs
    return packs.get_pack(recipe.get("pack", recipe["name"]), **recipe.get("pack_params", {}))


def load_rows(paths, recipe):
    """Read one or more JSONL files. Rows without "questions" get the recipe pack's questions, and a
    row whose state is given as bare pack fields ({"user":..,"draft":..}) is used as the state."""
    pack = None
    rows = []
    for p in ([paths] if isinstance(paths, str) else paths):
        for r in read_jsonl(p):
            if "questions" not in r or "state" not in r:
                pack = pack or pack_for(recipe)
            if "questions" not in r:
                r["questions"] = pack["questions"]
            if "state" not in r:
                from laya_mcp import packs
                fields = {k: v for k, v in r.items() if k in pack["state_fields"]}
                r["state"] = packs.build_state(pack, **fields)
            rows.append(r)
    return rows


def dataset_paths(recipe):
    d = os.path.join(DATASETS_DIR, recipe.get("dataset", recipe["name"]))
    return {s: os.path.join(d, f"{s}.jsonl") for s in ("train", "val", "test")}


def setup_mlflow(experiment):
    """MLFLOW_TRACKING_URI if set, else a local sqlite store under runs/ (file stores are deprecated)."""
    import mlflow
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        os.makedirs(RUNS_DIR, exist_ok=True)
        uri = "sqlite:///" + os.path.join(RUNS_DIR, "mlflow.db")
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name(experiment) is None:
        art = os.environ.get("MLFLOW_ARTIFACT_ROOT")
        if not art and uri.startswith("sqlite:///") and not os.environ.get("MLFLOW_TRACKING_URI"):
            art = "file://" + os.path.join(RUNS_DIR, "mlartifacts")
        mlflow.create_experiment(experiment, artifact_location=art)
    mlflow.set_experiment(experiment)
    return mlflow
