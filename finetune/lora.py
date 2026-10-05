"""LoRA adapters for Laya, dependency-free (plain torch, no peft). The base model is never changed.

What gets trained: low-rank adapters (A, B) on ModernBERT's four projections per encoder layer
(`attn.Wqkv`, `attn.Wo`, `mlp.Wi`, `mlp.Wo`), plus the decision head (the small typed head that turns
encoder states into choice / score / yes-no answers; it is what a new task most needs to learn). The
421M-parameter base checkpoint stays frozen and untouched on disk.

What gets saved: ONE small adapter directory, never a full checkpoint and never a merge into the base:

    adapter_config.json        rank, alpha, dropout, target modules, which base (+ revision) it sits on,
                               the fitted temperatures, and a digest of the weights file
    adapter_model.safetensors  the LoRA A/B tensors and the decision-head parameters (fp16)

How it is served: base + adapter, combined in memory at load time (`load_agent`). `finetune.serve` with
`LAYA_LORA_ADAPTER=<dir>` builds the stock base Agent, injects the adapters into its in-memory model,
loads the adapter tensors and temperatures, and attaches the result to a router slot. The base files on
disk are only read. `evaluate.py`, `eval_ridgeback.py` and the MLflow pyfunc load adapters the same way.

Why no peft: the shared `laya.serve` venv has none, Laya's DecisionModel is a custom torch module, and
the whole mechanism is ~150 lines. The on-disk layout borrows peft's file names so it is recognisable.
"""
import hashlib
import json
import os

DEFAULT_TARGETS = ("attn.Wqkv", "attn.Wo", "mlp.Wi", "mlp.Wo")
CONFIG = "adapter_config.json"
WEIGHTS = "adapter_model.safetensors"
FORMAT = "laya-lora/1"


def is_adapter(path) -> bool:
    return isinstance(path, str) and os.path.isfile(os.path.join(path, CONFIG))


def _lora_linear_cls():
    import torch.nn as nn

    class LoRALinear(nn.Module):
        """A frozen base Linear plus a trainable low-rank update B@A, scaled by alpha/rank. The base
        weight is the base model's own tensor, never modified."""

        def __init__(self, base, rank, alpha, dropout):
            super().__init__()
            self.base = base
            for p in self.base.parameters():
                p.requires_grad_(False)
            self.rank, self.scaling = rank, alpha / rank
            self.drop = nn.Dropout(dropout) if dropout else nn.Identity()
            dev, dt = base.weight.device, base.weight.dtype
            import torch
            self.A = nn.Parameter(torch.empty(rank, base.in_features, device=dev, dtype=dt))
            self.B = nn.Parameter(torch.zeros(base.out_features, rank, device=dev, dtype=dt))
            nn.init.kaiming_uniform_(self.A, a=5 ** 0.5)   # B starts at zero: the adapter starts as a no-op

        def forward(self, x):
            return self.base(x) + (self.drop(x) @ self.A.t().to(x.dtype) @ self.B.t().to(x.dtype)) * self.scaling

    return LoRALinear


def inject(model, rank=16, alpha=32, dropout=0.05, targets=DEFAULT_TARGETS, train_head=True):
    """Wrap each target Linear under `model.encoder` with a LoRA adapter and freeze every base encoder
    weight. The decision head stays trainable when `train_head` (it is saved with the adapter).
    Returns (model, n_adapters, n_lora_params)."""
    import torch.nn as nn
    LoRALinear = _lora_linear_cls()
    for p in model.encoder.parameters():
        p.requires_grad_(False)
    if not train_head:
        for n, p in model.named_parameters():
            if not n.startswith("encoder."):
                p.requires_grad_(False)
    n, params = 0, 0
    for mod_name, module in list(model.encoder.named_modules()):
        for child_name, child in list(module.named_children()):
            full = f"{mod_name}.{child_name}" if mod_name else child_name
            if isinstance(child, nn.Linear) and any(full.endswith(t) for t in targets):
                wrapped = LoRALinear(child, rank, alpha, dropout)
                setattr(module, child_name, wrapped)
                n += 1
                params += wrapped.A.numel() + wrapped.B.numel()
    if n == 0:
        raise RuntimeError(f"LoRA matched no modules for targets {targets}")
    return model, n, params


def adapter_state(model) -> dict:
    """Exactly the tensors training changed: the LoRA A/B and the trainable head parameters. Nothing
    from the frozen base."""
    sd = model.state_dict()
    trainable = {n for n, p in model.named_parameters() if p.requires_grad}
    return {k: sd[k].detach().cpu() for k in sd if k in trainable}


def save_adapter(model, out_dir, *, temps, base, base_revision, lora_cfg, recipe):
    """Write the adapter directory. Never writes base weights, tokenizer, or encoder config."""
    from safetensors.torch import save_file
    os.makedirs(out_dir, exist_ok=True)
    sd = {k: v.half().contiguous() for k, v in adapter_state(model).items()}
    wpath = os.path.join(out_dir, WEIGHTS)
    save_file(sd, wpath, metadata={"format": FORMAT})
    digest = hashlib.sha256(open(wpath, "rb").read()).hexdigest()
    n_lora = sum(v.numel() for k, v in sd.items() if k.endswith((".A", ".B")))
    n_head = sum(v.numel() for k, v in sd.items() if not k.endswith((".A", ".B")))
    cfg = {"format": FORMAT, "peft_type": "LORA", "base": base, "base_revision": base_revision,
           "r": lora_cfg["rank"], "lora_alpha": lora_cfg["alpha"], "lora_dropout": lora_cfg["dropout"],
           "target_modules": list(lora_cfg["target_modules"]), "modules_to_save": ["decision_head"],
           "temperature": [float(t) for t in temps], "recipe": recipe,
           "params": {"lora": n_lora, "head": n_head, "total": n_lora + n_head},
           "bytes": os.path.getsize(wpath), "sha256": digest}
    with open(os.path.join(out_dir, CONFIG), "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def apply_adapter(model, adapter_dir):
    """Inject adapters into an already-built base model (in memory) and load the adapter tensors."""
    from safetensors.torch import load_file
    with open(os.path.join(adapter_dir, CONFIG)) as f:
        cfg = json.load(f)
    if cfg.get("format") != FORMAT:
        raise ValueError(f"{adapter_dir}: not a {FORMAT} adapter")
    wpath = os.path.join(adapter_dir, WEIGHTS)
    if cfg.get("sha256") and hashlib.sha256(open(wpath, "rb").read()).hexdigest() != cfg["sha256"]:
        raise ValueError(f"{adapter_dir}: adapter weights do not match their recorded digest")
    inject(model, rank=cfg["r"], alpha=cfg["lora_alpha"], dropout=0.0, targets=tuple(cfg["target_modules"]))
    weights = load_file(wpath)
    own = model.state_dict()
    missing = [k for k in weights if k not in own]
    if missing:
        raise ValueError(f"{adapter_dir}: adapter tensors the model does not have: {missing[:5]}")
    model.load_state_dict({k: v.to(own[k].dtype) for k, v in weights.items()}, strict=False)
    lora_keys = {k for k in own if k.endswith((".A", ".B"))}
    if not lora_keys <= set(weights):
        raise ValueError(f"{adapter_dir}: adapter is missing LoRA tensors")
    return cfg


def load_agent(adapter_dir, device=None):
    """A laya.Agent serving base + adapter. The base is built from the Hub cache (read-only) exactly as
    laya.serve builds it; the adapter is then applied to the in-memory model only."""
    from laya.agent import Agent
    from laya.common import clamp_temperature
    from .common import resolve_base
    with open(os.path.join(adapter_dir, CONFIG)) as f:
        cfg = json.load(f)
    base_dir, _ = resolve_base(cfg["base"])
    agent = Agent(base_dir, device=device)
    apply_adapter(agent.model, adapter_dir)
    agent.model.to(agent.device).eval()
    temps = cfg["temperature"]
    agent.temperature_raw = list(temps)
    agent.temperature = [clamp_temperature(t) for t in temps]
    agent.temperature_by_options_raw, agent.temperature_by_options = {}, {}   # base buckets would mask the fit
    agent.cfg = {**agent.cfg, "temperature": list(temps), "model_name": f"laya+{cfg.get('recipe')}"}
    agent.cfg.pop("temperature_by_options", None)
    agent.adapter = {"dir": os.path.abspath(adapter_dir), "sha256": cfg.get("sha256"),
                     "params": cfg.get("params"), "base": cfg["base"]}
    return agent
