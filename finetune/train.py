#!/usr/bin/env python3
"""Fine-tune (or just calibrate) a Laya checkpoint on a recipe's train split.

Single-GPU adaptation of the upstream RLCD loop (laya's fine-tuning notebook): a GRPO-style
policy gradient over noisy logits scored by laya's proper scoring rule, plus soft cross-entropy
guidance. Three strategies:

  full       encoder + decision head train (encoder at a lower LR). Best accuracy, most VRAM.
  head       encoder frozen, only the decision head trains. ~3x less VRAM, faster, overfits less on
             small sets. A good default for a few hundred rows.
  calibrate  no training: fit per-type temperatures on the val split and export. Cheapest; fixes
             over-confidence and gives usable serving thresholds, but cannot teach new decisions.

The VAL split is never trained on. It is used for temperature fitting (as upstream warns, fitting
temperatures on trained items returns a degenerate scale) and, in evaluate.py, for thresholds.

The exported directory loads with `laya.Agent(dir)` / `laya.load(dir)` and in the serve wrapper.

    python -m finetune.train --recipe guard-output-leak --strategy head --epochs 3 --out runs/leak
"""
import argparse
import json
import math
import os
import random
import shutil
import time

from .common import (QTYPE_IDX, TEMP_MAX, TEMP_MIN, dataset_paths, load_base_cfg, load_recipe,
                     load_rows, load_tokenizer, resolve_base)
from .data import collate, encode_rows

DEFAULTS = {
    "epochs": 3, "micro_batch": 8, "grad_accum": 4, "lr_encoder": 2.5e-5, "lr_head": 1e-4,
    "group_size": 4, "sigma_start": 0.4, "sigma_end": 0.1, "ce_weight": 1.0, "w_sph": 0.75,
    "w_rps": 1.0, "smoothing": 0.05, "weight_decay": 0.01, "seed": 13, "max_len": None,
    "head_max_len": None,
}


def load_model(model_dir, cfg, device):
    import torch
    from laya.common import build_model
    from safetensors.torch import load_file
    model = build_model(cfg, encoder_dir=os.path.join(model_dir, "encoder"))
    model.load_state_dict(load_file(os.path.join(model_dir, "model.safetensors")), strict=True)
    return model.to(torch.device(device))


def _amp_dtype(device):
    import torch
    if device.startswith("cuda") and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float16


def forward_logits(model, items, pad_id, device, batch=16):
    """Raw (untempered) logits per item, eval mode, no grad. Returns list of lists (len k each)."""
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(items), batch):
            chunk = items[i:i + batch]
            b = collate(chunk, pad_id)
            with torch.autocast(device.split(":")[0], dtype=_amp_dtype(device), enabled=device.startswith("cuda")):
                logits, _ = model(b["input_ids"].to(device), b["attention_mask"].to(device),
                                  b["marker_pos"].to(device), b["marker_mask"].to(device), b["qtype"].to(device))
            l = logits.float().cpu()
            for r, it in enumerate(chunk):
                out.append(l[r, :len(it["markers"])].tolist())
    return out


def _parity(model, adapter_dir, cal_items, val_rows, pad_id, device, temps, n=48):
    """Serve-path check: base + adapter loaded the way laya.serve loads it must give the same answers as
    the model that was just trained. Compares argmax and probabilities on up to n val items."""
    import torch
    from . import lora
    items = cal_items[:n]
    # batch=1: the serving computation is one unpadded item per forward. A padded batch moves bf16
    # probabilities on long sequences (measured 0.07 on the 15-option routing group question), which is
    # a property of batching, not of the adapter; comparing like with like isolates the adapter.
    logits = forward_logits(model, items, pad_id, device, batch=1)
    agent = lora.load_agent(adapter_dir, device=device)
    same, worst = 0, 0.0
    for z, it in zip(logits, items):
        row = val_rows[it["row"]]
        qid = it["qid"]
        res = agent.predict(row["state"], {qid: row["questions"][qid]})["answers"][qid]
        t = temps[it["qtype"]]
        p_train = torch.softmax(torch.tensor(z) / t, -1).tolist()
        q = row["questions"][qid]
        if q["type"] == "noul":
            p_serve = [1 - res["noul"], res["noul"]]
        elif q["type"] == "choice":
            p_serve = [res["probabilities"].get(k, 0.0) for k in q["criteria"]]
        else:
            p_serve = [res["probabilities"].get(str(i), 0.0) for i in range(len(q["criteria"]))]
        same += int(max(range(len(p_train)), key=p_train.__getitem__)
                    == max(range(len(p_serve)), key=p_serve.__getitem__))
        worst = max(worst, max(abs(a - b) for a, b in zip(p_train, p_serve)))
    del agent
    out = {"items": len(items), "argmax_agree": same, "max_prob_diff": round(worst, 4)}
    print(f"[train] serve-path parity (base + adapter vs trained model): {out}", flush=True)
    if same < len(items) - 1 or worst > 0.08:
        raise RuntimeError(f"adapter does not reproduce the trained model when served: {out}")
    return out


def _trainable(model, key):
    """True for state-dict keys whose parameter trains (LoRA A/B, the head), so a best-epoch snapshot
    stays small. Buffers and frozen base weights are never touched by training, so they need no copy."""
    params = dict(model.named_parameters())
    p = params.get(key)
    return p is not None and p.requires_grad


def fit_temperature(pairs):
    """One temperature for a list of (logits, target) pairs, LBFGS on soft cross-entropy (upstream)."""
    import torch
    if len(pairs) < 10:
        return None
    kmax = max(len(z) for z, _ in pairs)
    Z = torch.full((len(pairs), kmax), -1e4)
    T = torch.zeros((len(pairs), kmax))
    for i, (z, t) in enumerate(pairs):
        Z[i, :len(z)] = torch.tensor(z)
        T[i, :len(t)] = torch.tensor(t, dtype=torch.float32)
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = -(T * torch.log_softmax(Z / log_t.exp(), -1)).sum(-1).mean()
        loss.backward()
        return loss
    opt.step(closure)
    return float(min(TEMP_MAX, max(TEMP_MIN, log_t.exp().item())))


def fit_temperatures(model, cal_items, pad_id, device, base_temps):
    """Per-type temperatures [choice, score, noul]; a type with too few val items keeps its base value."""
    logits = forward_logits(model, cal_items, pad_id, device)
    temps = list(base_temps)
    for name, qt in QTYPE_IDX.items():
        pairs = [(z, it["target"]) for z, it in zip(logits, cal_items) if it["qtype"] == qt]
        t = fit_temperature(pairs)
        if t is not None:
            temps[qt] = t
    return temps


def train_loop(model, items, pad_id, device, hp, strategy, log_metric=None, on_epoch_end=None):
    """RLCD training. Returns the trained model (in place)."""
    import torch
    from laya.common import proper_reward

    rng = random.Random(hp["seed"])
    torch.manual_seed(hp["seed"])
    head_only = strategy == "head"
    # "lora" freezes the base encoder and trains only the injected adapters (already set up by run());
    # like "head" the base weights do not move, but unlike "head" the encoder still needs its backward
    # pass and checkpointing because the adapters live inside it.
    if head_only:
        for p in model.encoder.parameters():
            p.requires_grad_(False)
    else:
        model.encoder.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.head_checkpointing = not head_only
    model.train()
    if head_only:
        model.encoder.eval()                 # frozen encoder: no dropout noise in its features

    enc = [p for n, p in model.named_parameters() if n.startswith("encoder.") and p.requires_grad]
    head = [p for n, p in model.named_parameters() if not n.startswith("encoder.") and p.requires_grad]
    groups = [{"params": head, "lr": hp["lr_head"]}]
    if enc:
        groups.append({"params": enc, "lr": hp["lr_encoder"]})
    opt = torch.optim.AdamW(groups, weight_decay=hp["weight_decay"])
    mb, ga, epochs = hp["micro_batch"], hp["grad_accum"], hp["epochs"]
    updates = max(1, math.ceil(len(items) / (mb * ga)) * epochs)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=updates, eta_min=1e-6)
    amp = _amp_dtype(device)
    scaler = torch.amp.GradScaler("cuda", enabled=(amp == torch.float16 and device.startswith("cuda")))
    step = 0
    t0 = time.time()
    for epoch in range(epochs):
        rng.shuffle(items)
        sigma = hp["sigma_start"] + (hp["sigma_end"] - hp["sigma_start"]) * (epoch / max(1, epochs - 1))
        tot_loss = tot_reward = 0.0
        nb = 0
        opt.zero_grad(set_to_none=True)
        for bi in range(0, len(items), mb):
            chunk = items[bi:bi + mb]
            b = collate(chunk, pad_id)
            with torch.autocast("cuda", dtype=amp, enabled=device.startswith("cuda")):
                logits, act = model(b["input_ids"].to(device), b["attention_mask"].to(device),
                                    b["marker_pos"].to(device), b["marker_mask"].to(device),
                                    b["qtype"].to(device), detach_encoder=head_only)
            logits = logits.float()
            mask = b["marker_mask"].to(device)
            k = mask.sum(-1, keepdim=True).float()
            target = b["target"].to(device)
            qtype = b["qtype"].to(device)
            # GRPO over G noisy logit samples, zero-mean noise projected onto the valid options
            eps = torch.randn((hp["group_size"],) + logits.shape, device=device) * sigma * mask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mask
            z = logits.detach().unsqueeze(0) + eps
            q = torch.softmax(z.masked_fill(~mask, -1e4), -1)
            with torch.no_grad():
                r = proper_reward(q, target.unsqueeze(0), qtype, mask, w_sph=hp["w_sph"], w_rps=hp["w_rps"])
                adv = (r - r.mean(0, keepdim=True))
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sigma ** 2)
            loss_rl = -(adv * logp).mean()
            loss_ce = -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1)).sum(-1).mean()
            loss = (loss_rl + hp["ce_weight"] * loss_ce) / ga + 0.0 * act.sum()
            scaler.scale(loss).backward()
            nb += 1
            tot_loss += loss.item() * ga
            tot_reward += r.mean().item()
            if nb % ga == 0 or bi + mb >= len(items):
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_([p for g in groups for p in g["params"]], 1.0)
                scaler.step(opt)
                scaler.update()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if log_metric:
                    log_metric("train_loss", loss.item() * ga, step)
                    log_metric("train_ce", loss_ce.item(), step)
                    log_metric("train_reward", r.mean().item(), step)
                    log_metric("lr_head", sched.get_last_lr()[0], step)
        ep = {"epoch_loss": tot_loss / max(1, nb), "epoch_reward": tot_reward / max(1, nb), "sigma": sigma}
        print(f"  epoch {epoch + 1}/{epochs} loss={ep['epoch_loss']:.4f} reward={ep['epoch_reward']:.3f} "
              f"({time.time() - t0:.0f}s)", flush=True)
        if log_metric:
            for kk, v in ep.items():
                log_metric(kk, v, epoch + 1)
        # Early stopping: the callback scores val (never trained on) and returns True to stop.
        if on_epoch_end is not None:
            stop = on_epoch_end(epoch + 1)
            model.train()
            if strategy == "head":
                model.encoder.eval()
            if stop:
                print(f"  early stop after epoch {epoch + 1}", flush=True)
                break
    model.eval()
    return model


def _val_scores(model, cal_items, rows, pad_id, device):
    """Val accuracy overall and per `set` (rows may carry one, as the Ridgeback combined set does),
    plus mean soft cross-entropy, from the raw logits."""
    import math as _m
    logits = forward_logits(model, cal_items, pad_id, device)
    per, ce = {}, []
    for z, it in zip(logits, cal_items):
        pred = max(range(len(z)), key=z.__getitem__)
        ok = float(pred == it["label"])
        name = rows[it["row"]].get("set", "all")
        a = per.setdefault(name, [0.0, 0])
        a[0] += ok
        a[1] += 1
        mx = max(z)
        lse = mx + _m.log(sum(_m.exp(v - mx) for v in z))
        ce.append(-sum(t * (v - lse) for t, v in zip(it["target"], z)))
    acc = {k: v[0] / v[1] for k, v in per.items()}
    total = sum(v[0] for v in per.values()) / max(1, sum(v[1] for v in per.values()))
    return total, acc, sum(ce) / max(1, len(ce))


def export(model, base_dir, cfg, out_dir, temps, recipe_name, strategy, copy_weights_from_base=False):
    """Write a checkpoint dir laya.Agent can load: weights + tokenizer + encoder config + config."""
    os.makedirs(out_dir, exist_ok=True)
    for sub in ("tokenizer", "encoder"):
        dst = os.path.join(out_dir, sub)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(os.path.join(base_dir, sub), dst)       # copytree dereferences HF cache symlinks
    wpath = os.path.join(out_dir, "model.safetensors")
    if os.path.lexists(wpath):
        os.remove(wpath)
    if copy_weights_from_base:
        src = os.path.realpath(os.path.join(base_dir, "model.safetensors"))
        try:
            os.link(src, wpath)          # calibrate-only: weights unchanged, hardlink when on one filesystem
        except OSError:
            shutil.copy2(src, wpath)     # a real file: MLflow refuses symlinks pointing outside the artifact dir
    else:
        from safetensors.torch import save_file
        sd = {k: v.detach().half().contiguous().cpu() for k, v in model.state_dict().items()}
        save_file(sd, wpath)
    new_cfg = dict(cfg)
    new_cfg["temperature"] = [float(t) for t in temps]
    new_cfg.pop("temperature_by_options", None)   # stale bucket temps would override the new fit
    new_cfg["fine_tuned"] = strategy != "calibrate"
    new_cfg["model_name"] = f"laya-{recipe_name}"
    new_cfg.setdefault("training", {})
    new_cfg["recipe"] = {"name": recipe_name, "strategy": strategy}
    with open(os.path.join(out_dir, "rl_agent_config.json"), "w") as f:
        json.dump(new_cfg, f, indent=2)
    return out_dir


def run(recipe, out_dir, strategy=None, base=None, device="cuda:0", overrides=None, log_metric=None,
        extra_data=None):
    """Train/calibrate per recipe; returns dict with checkpoint path, temps and data stats.
    `extra_data` = more train JSONL files (e.g. private rows) mixed into the recipe's train split."""
    import torch
    strategy = strategy or recipe.get("strategy", "head")
    base = base or recipe.get("base", "english")
    hp = {**DEFAULTS, **recipe.get("hyperparams", {}),
          **(recipe.get("head_hyperparams", {}) if strategy == "head" else {}), **(overrides or {})}
    base_dir, revision = resolve_base(base)
    cfg = load_base_cfg(base_dir)
    tok = load_tokenizer(base_dir, cfg)
    paths = dataset_paths(recipe)
    train_rows = load_rows([paths["train"]] + list(extra_data or []), recipe)
    val_rows = load_rows(paths["val"], recipe)
    enc_kw = {"max_len": hp["max_len"], "head_max_len": hp["head_max_len"]}
    cal_items, cal_drop = encode_rows(val_rows, tok, cfg, smoothing=0.0, **enc_kw)
    model = load_model(base_dir, cfg, device)
    stats = {"base": base, "base_dir": base_dir, "base_revision": revision, "strategy": strategy,
             "val_items": len(cal_items), "val_dropped": cal_drop}
    lora_cfg = None
    if strategy == "lora":
        from . import lora
        lora_cfg = {"rank": 16, "alpha": 32, "dropout": 0.05, "target_modules": list(lora.DEFAULT_TARGETS),
                    **recipe.get("lora", {})}
        model, n_adapters, n_params = lora.inject(
            model, rank=lora_cfg["rank"], alpha=lora_cfg["alpha"], dropout=lora_cfg["dropout"],
            targets=tuple(lora_cfg["target_modules"]))
        stats.update(lora_adapters=n_adapters, lora_trainable_params=n_params, lora=lora_cfg)
        print(f"[train] LoRA: {n_adapters} adapters, {n_params:,} trainable adapter params "
              f"(rank={lora_cfg['rank']}, alpha={lora_cfg['alpha']})", flush=True)
    if strategy != "calibrate":
        items, dropped = encode_rows(train_rows, tok, cfg, smoothing=hp["smoothing"], **enc_kw)
        stats.update(train_items=len(items), train_dropped=dropped)
        print(f"[train] {recipe['name']}: {len(items)} items ({dropped} dropped), strategy={strategy}, "
              f"base={base}, device={device}", flush=True)
        t0 = time.time()
        history = []
        best = {"ce": float("inf"), "state": None, "epoch": 0}
        patience = int(hp.get("early_stop_patience", 0) or 0)

        def on_epoch_end(ep):
            total, per_set, ce = _val_scores(model, cal_items, val_rows, tok.pad_token_id, device)
            history.append({"epoch": ep, "val_acc": round(total, 4), "val_ce": round(ce, 4),
                            "val_acc_by_set": {k: round(v, 4) for k, v in sorted(per_set.items())}})
            print(f"  val epoch {ep}: acc={total:.4f} ce={ce:.4f} "
                  + " ".join(f"{k}={v:.3f}" for k, v in sorted(per_set.items())), flush=True)
            if log_metric:
                log_metric("val_acc", total, ep)
                log_metric("val_ce", ce, ep)
            if ce < best["ce"] - 1e-4:
                best.update(ce=ce, epoch=ep, state={k: v.detach().cpu().clone()
                                                    for k, v in model.state_dict().items()
                                                    if _trainable(model, k)})
                return False
            return patience > 0 and ep - best["epoch"] >= patience

        train_loop(model, items, tok.pad_token_id, device, hp, strategy, log_metric,
                   on_epoch_end=on_epoch_end if patience > 0 else None)
        if best["state"] is not None and history and history[-1]["epoch"] != best["epoch"]:
            model.load_state_dict(best["state"], strict=False)
            print(f"[train] restored best val epoch {best['epoch']}", flush=True)
        stats["val_history"] = history
        stats["best_epoch"] = best["epoch"] or (history[-1]["epoch"] if history else None)
        stats["train_seconds"] = round(time.time() - t0, 1)
        if torch.cuda.is_available():
            stats["peak_vram_gb"] = round(torch.cuda.max_memory_allocated(device) / 2 ** 30, 2)
    temps = fit_temperatures(model, cal_items, tok.pad_token_id, device, cfg.get("temperature", [1.0, 1.0, 1.0]))
    stats["temperatures"] = temps
    print(f"[train] fitted temperatures (choice, score, noul): {[round(t, 3) for t in temps]}", flush=True)
    if strategy == "lora":
        # Adapter only: the LoRA tensors and the decision head, in one small directory. The base is never
        # merged into, copied, or rewritten; it is served as base + adapter (lora.load_agent).
        from . import lora
        acfg = lora.save_adapter(model, out_dir, temps=temps, base=base, base_revision=revision,
                                 lora_cfg=lora_cfg, recipe=recipe["name"])
        base_bytes = os.path.getsize(os.path.realpath(os.path.join(base_dir, "model.safetensors")))
        stats.update(adapter_bytes=acfg["bytes"], adapter_params=acfg["params"], base_bytes=base_bytes,
                     adapter_fraction_of_base=round(acfg["bytes"] / base_bytes, 4))
        print(f"[train] adapter: {acfg['bytes'] / 2**20:.1f} MiB ({acfg['params']['total']:,} params: "
              f"{acfg['params']['lora']:,} LoRA + {acfg['params']['head']:,} head) vs base "
              f"{base_bytes / 2**20:.0f} MiB = {100 * acfg['bytes'] / base_bytes:.1f}%", flush=True)
        stats["parity"] = _parity(model, out_dir, cal_items, val_rows, tok.pad_token_id, device, temps)
    else:
        export(model, base_dir, cfg, out_dir, temps, recipe["name"], strategy,
               copy_weights_from_base=(strategy == "calibrate"))
    stats["checkpoint"] = os.path.abspath(out_dir)
    stats["hyperparams"] = hp
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strategy", choices=["full", "head", "lora", "calibrate"])
    ap.add_argument("--base", help="english | multilingual | typed-decisions | checkpoint dir")
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--device", help="explicit torch device (overrides --gpu)")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--micro-batch", type=int)
    ap.add_argument("--data", action="append", default=[],
                    help="extra train JSONL (repeatable), mixed with the recipe's train split")
    a = ap.parse_args()
    over = {k: v for k, v in {"epochs": a.epochs, "micro_batch": a.micro_batch}.items() if v}
    stats = run(load_recipe(a.recipe), a.out, a.strategy, a.base, a.device or f"cuda:{a.gpu}", over,
                extra_data=a.data)
    print(json.dumps({k: v for k, v in stats.items() if k != "hyperparams"}, indent=2, default=str))


if __name__ == "__main__":
    main()
