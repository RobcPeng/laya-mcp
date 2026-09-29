"""JSONL rows -> Laya training items, encoded exactly the way `laya.Agent` encodes at inference.

One row holds a state plus several questions; each (row, question) pair becomes one item:
    {"ids", "markers", "qtype", "target": [p per option], "label": argmax, "row", "qid"}
Targets are distributions (a soft gold such as P(true)=0.8 is kept as-is). Optional label smoothing
spreads `smoothing` of the mass uniformly, which keeps a small synthetic set from driving logits to
extremes and helps the temperature fit afterwards.
"""
from laya.common import QTYPES, build_sequence, render_options

from .common import to_internal


def gold_to_target(q, gold, smoothing=0.0):
    t = q["type"]
    if t == "noul":
        p = float(gold) if not isinstance(gold, bool) else (1.0 if gold else 0.0)
        target = [1.0 - p, p]
    elif t == "choice":
        keys = list(q["criteria"].keys())
        if gold not in keys:
            raise ValueError(f"choice gold {gold!r} not in options {keys}")
        target = [1.0 if k == gold else 0.0 for k in keys]
    elif t == "score":
        n = len(q["criteria"])
        g = int(gold)
        if not 0 <= g < n:
            raise ValueError(f"score gold {g} outside 0..{n - 1}")
        target = [1.0 if i == g else 0.0 for i in range(n)]
    else:
        raise ValueError(f"unknown question type {t!r}")
    if smoothing:
        k = len(target)
        target = [(1 - smoothing) * v + smoothing / k for v in target]
    s = sum(target)
    return [v / s for v in target]


def encode_rows(rows, tok, cfg, smoothing=0.0, max_len=None, head_max_len=None):
    """Returns (items, n_dropped). An item is dropped when its options overflow head_max_len
    (markers != options), the same condition that makes Agent.predict refuse the question."""
    max_len = max_len or cfg.get("max_len", 512)
    head_max_len = head_max_len or cfg.get("head_max_len", 192)
    items, dropped = [], 0
    for ri, row in enumerate(rows):
        for qid, gold in row["gold"].items():
            q = row["questions"][qid]
            iq = to_internal(q)
            seq, markers = build_sequence(tok, row["state"], iq, max_len, head_max_len,
                                          truncate_left=isinstance(row["state"], list))
            if len(markers) != len(render_options(iq)):
                dropped += 1
                continue
            target = gold_to_target(q, gold, smoothing)
            items.append({"ids": seq, "markers": markers, "qtype": QTYPES[q["type"]], "target": target,
                          "label": max(range(len(target)), key=target.__getitem__), "row": ri, "qid": qid})
    return items, dropped


def collate(items, pad_id):
    import torch
    n, L = len(items), max(len(it["ids"]) for it in items)
    kmax = max(len(it["markers"]) for it in items)
    ids = torch.full((n, L), pad_id, dtype=torch.long)
    att = torch.zeros((n, L), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    target = torch.zeros((n, kmax), dtype=torch.float32)
    for i, it in enumerate(items):
        ids[i, :len(it["ids"])] = torch.tensor(it["ids"])
        att[i, :len(it["ids"])] = 1
        k = len(it["markers"])
        mpos[i, :k] = torch.tensor(it["markers"])
        mmask[i, :k] = True
        target[i, :len(it["target"])] = torch.tensor(it["target"], dtype=torch.float32)
    return {"input_ids": ids, "attention_mask": att, "marker_pos": mpos, "marker_mask": mmask,
            "target": target, "qtype": torch.tensor([it["qtype"] for it in items]),
            "label": torch.tensor([it["label"] for it in items])}
