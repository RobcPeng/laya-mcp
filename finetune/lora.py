"""LoRA for Laya's ModernBERT encoder, dependency-free (plain torch, no peft).

Why no peft: the shared `laya.serve` venv does not have peft, `laya.Agent` loads a plain checkpoint
directory (encoder + a single `model.safetensors`), and a merged LoRA is byte-identical to a full
fine-tune at inference. So we inject low-rank adapters for training, then MERGE them into the base
weights and export an ordinary checkpoint. Nothing downstream — `laya.serve`, `finetune.serve`,
`finetune.evaluate`, the MLflow pyfunc model — needs to know LoRA was used, and no new runtime
dependency ships. The adapter tensors are also saved on their own (`adapter.safetensors`) for provenance
and so a future serving stack that keeps the base frozen can load just the delta.

Target modules are ModernBERT's four Linear projections per layer: `attn.Wqkv`, `attn.Wo`, `mlp.Wi`,
`mlp.Wo`. The decision head is NOT adapted — it trains in full (it is tiny and is where most of the
task-specific signal lives), the same as every other strategy here.

Hyperparameters come from the recipe's `lora` block: `rank`, `alpha`, `dropout`, `target_modules`.
"""
import os
import re

DEFAULT_TARGETS = ("attn.Wqkv", "attn.Wo", "mlp.Wi", "mlp.Wo")


def _lora_linear_cls():
    import torch
    import torch.nn as nn

    class LoRALinear(nn.Module):
        """A frozen base Linear plus a trainable low-rank update B@A, scaled by alpha/rank."""

        def __init__(self, base: nn.Linear, rank: int, alpha: float, dropout: float):
            super().__init__()
            self.base = base
            for p in self.base.parameters():
                p.requires_grad_(False)
            self.rank = rank
            self.scaling = alpha / rank
            self.drop = nn.Dropout(dropout) if dropout else nn.Identity()
            dev, dt = base.weight.device, base.weight.dtype
            self.A = nn.Parameter(torch.empty(rank, base.in_features, device=dev, dtype=dt))
            self.B = nn.Parameter(torch.zeros(base.out_features, rank, device=dev, dtype=dt))
            nn.init.kaiming_uniform_(self.A, a=5 ** 0.5)   # B stays zero: the adapter starts as a no-op

        def forward(self, x):
            return self.base(x) + (self.drop(x) @ self.A.t() @ self.B.t()) * self.scaling

        @torch.no_grad()
        def merged(self) -> nn.Linear:
            """The base Linear with the delta folded into its weight; the module to export."""
            delta = (self.B @ self.A) * self.scaling
            self.base.weight.add_(delta.to(self.base.weight.dtype))
            return self.base

    return LoRALinear


def _targets_match(name: str, targets) -> bool:
    return any(name.endswith(t) for t in targets)


def inject(model, rank=16, alpha=32, dropout=0.05, targets=DEFAULT_TARGETS):
    """Wrap each target Linear under `model.encoder` in a LoRALinear, freeze everything else in the
    encoder, and return (model, n_adapters, n_trainable_lora_params). The head is left trainable."""
    import torch.nn as nn

    LoRALinear = _lora_linear_cls()
    for p in model.encoder.parameters():
        p.requires_grad_(False)
    n, params = 0, 0
    for mod_name, module in list(model.encoder.named_modules()):
        for child_name, child in list(module.named_children()):
            full = f"{mod_name}.{child_name}" if mod_name else child_name
            if isinstance(child, nn.Linear) and _targets_match(full, targets):
                wrapped = LoRALinear(child, rank, alpha, dropout)
                setattr(module, child_name, wrapped)
                n += 1
                params += wrapped.A.numel() + wrapped.B.numel()
    if n == 0:
        raise RuntimeError(f"LoRA matched no modules for targets {targets}")
    return model, n, params


def adapter_state(model):
    """Just the LoRA tensors, keyed by their module path — for `adapter.safetensors`."""
    return {k: v.detach().cpu() for k, v in model.state_dict().items()
            if re.search(r"\.(A|B)$", k) and (".base." not in k)}


def merge(model):
    """Fold every LoRA delta into its base Linear and unwrap, so the module tree and the state-dict keys
    are identical to the original encoder. Call before `export`."""
    import torch.nn as nn

    LoRALinear = type(next(m for m in model.modules()
                           if m.__class__.__name__ == "LoRALinear"))
    for module in model.modules():
        for child_name, child in list(module.named_children()):
            if isinstance(child, LoRALinear):
                setattr(module, child_name, child.merged())
    for p in model.encoder.parameters():
        p.requires_grad_(True)
    return model


def save_adapter(model, out_dir, meta=None):
    import json
    from safetensors.torch import save_file

    os.makedirs(out_dir, exist_ok=True)
    sd = adapter_state(model)
    if sd:
        save_file({k: v.contiguous().to("cpu").float() for k, v in sd.items()},
                  os.path.join(out_dir, "adapter.safetensors"))
    with open(os.path.join(out_dir, "adapter_config.json"), "w") as f:
        json.dump(meta or {}, f, indent=2)
