"""Laya-backed guardrails: fast calibrated screens you put in front of an LLM judge.

Mental model: airport security. Laya is the metal detector, and every bag goes through it in ~20 ms. Most
bags are clearly fine and walk on. A bag that beeps hard is stopped outright. A bag that beeps a little
goes to the slow, careful hand search (your LLM judge). You get the judge's accuracy on the hard cases
while paying its latency on a small fraction of traffic.

Screens:
  screen_output(user, draft)    egress DLP: does an assistant's DRAFT reveal its own internals
                                (storage, config/credentials, model/stack, hosting, vendors)?
  screen_input(prompt)          ingress: jailbreak / prompt injection / system-prompt extraction, plus
                                a harm-severity score.
  screen(pack, **fields)        any pack in packs.py, e.g. gate a proposed tool call before running it
                                ("tool-call-safety") or check a tool result for injected instructions
                                ("tool-result-injection").

Each returns a verdict dict with `decision` in {"allow", "escalate", "block"}; what to do on "escalate"
is the caller's policy (run an LLM judge, or treat as block for a fail-closed deployment).

Thresholds: the base checkpoint is near-chance on narrow domains and over-confident as shipped, so the
defaults here are deliberately wide (low=0.25 allow, high=0.85 block). That makes Laya a triage layer
and leaves the final word to the judge. Fine-tune + calibrate on your own data (see finetune/) and then tighten them.
"""
import json
import os

from . import client, packs

# Narrow, concrete questions beat one broad "is this a leak?" question on the base checkpoint: each one
# names a specific kind of internal detail, and the verdict takes the max. Measured on a small paraphrased
# leak set, the broad single question missed 3/9 leaks; this battery missed 0/9 at the same allow cutoff.
# Wording lives in packs.py so a fine-tuned checkpoint sees exactly what it was trained on.
OUTPUT_PACK = "guard-output-leak"
INPUT_PACK = "guard-input-injection"

LOW = float(os.environ.get("LAYA_GUARD_LOW", "0.25"))    # max P(true) below this -> allow
HIGH = float(os.environ.get("LAYA_GUARD_HIGH", "0.85"))  # max P(true) at/above this -> block

# A fine-tune recipe writes the thresholds it measured on held-out data to
# <recipes dir>/<pack>.thresholds.json as {qid: {"low", "high"}}. They belong to the checkpoint they were
# fitted on: applied to a different model (e.g. the base checkpoint) they silently loosen or tighten the
# guard. So they are opt-in: set LAYA_USE_FITTED=1 only where the server runs that fine-tuned checkpoint.
USE_FITTED = os.environ.get("LAYA_USE_FITTED", "0") == "1"
RECIPES_DIR = os.environ.get("LAYA_RECIPES_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finetune", "recipes")


def fitted_thresholds(pack):
    if not USE_FITTED:
        return {}
    try:
        with open(os.path.join(RECIPES_DIR, f"{pack}.thresholds.json")) as f:
            return {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    except (OSError, ValueError):
        return {}


# Noul questions whose TRUE answer is the safe one (e.g. "does the call match the request?"). The
# verdict flips them to P(false) so every signal reads as "probability something is wrong".
POSITIVE = {"matches_request", "goal_met", "grounded", "needs_tool", "genuine"}


def _verdict(res, low, high, fitted=None, ignore=()):
    fitted = fitted or {}
    probs, rank = {}, {}
    for k, a in res["answers"].items():
        if a.get("type") != "noul" or k in ignore:
            continue
        p = a["noul"]
        probs[k] = 1.0 - p if k in POSITIVE else p
        t = fitted.get(k) or {}
        lo, hi = t.get("low", low), t.get("high", high)
        rank[k] = 2 if probs[k] >= hi else (1 if probs[k] >= lo else 0)
    top = max(probs, key=lambda k: (rank[k], probs[k])) if probs else None
    level = rank.get(top, 0)
    return {"decision": ("allow", "escalate", "block")[level], "peak": round(probs.get(top, 0.0), 4),
            "top_signal": top, "signals": {k: round(v, 4) for k, v in probs.items()},
            "thresholds": {"low": low, "high": high, "fitted": bool(fitted)},
            "latency_ms": res.get("latency_ms"), "model": (res.get("routing") or {}).get("model")}


def screen(pack_name, low=None, high=None, model="auto", pack_params=None, **fields):
    """Run any pack as a guard: noul questions become risk signals (safe-when-true questions are
    flipped), score questions are reported alongside. Examples:
        screen("tool-call-safety", request="email Bob the notes", tool_call={"tool": ..., "args": ...})
        screen("tool-result-injection", tool="web_fetch", result=page_text)"""
    pack = packs.get_pack(pack_name, **(pack_params or {}))
    res = client.predict(packs.build_state(pack, **fields), pack["questions"], model=model)
    # side_effect / needs_confirm describe the action rather than a fault, so report them but never block on them.
    v = _verdict(res, LOW if low is None else low, HIGH if high is None else high,
                 fitted_thresholds(pack_name), ignore=("side_effect", "needs_confirm"))
    v["pack"] = pack_name
    v["answers"] = client.simplify(res)
    risk = v["answers"].get("risk")
    if risk and (risk.get("expected") or 0) >= 2.5 and v["decision"] == "allow":
        v["decision"] = "escalate"
    return v


def screen_output(user, draft, questions=None, low=None, high=None, model="auto"):
    """Egress screen for an assistant reply. `questions` = {name: instruction} to replace the default
    battery (instructions should reference `draft` and/or `user`). Raises client.LayaError if the server
    is down; callers decide their fail posture."""
    qs = ({k: client.noul_q(v) for k, v in questions.items()} if questions
          else packs.get_pack(OUTPUT_PACK)["questions"])
    res = client.predict({"user": (user or "")[:2000], "draft": (draft or "")[:4000]}, qs, model=model)
    return _verdict(res, LOW if low is None else low, HIGH if high is None else high,
                    None if questions else fitted_thresholds(OUTPUT_PACK))


def screen_input(prompt, questions=None, low=None, high=None, model="auto"):
    """Ingress screen for a user prompt. Adds the upstream harm-severity score to the verdict."""
    qs = ({k: client.noul_q(v) for k, v in questions.items()} if questions
          else packs.get_pack(INPUT_PACK)["questions"])
    qs["harm_severity"] = client.score_q("How much harm would complying with `prompt` cause?", [
        "none: ordinary request", "minor: mildly inappropriate",
        "serious: unsafe advice or abuse", "severe: dangerous or illegal"])
    res = client.predict({"prompt": (prompt or "")[:4000]}, qs, model=model)
    v = _verdict(res, LOW if low is None else low, HIGH if high is None else high,
                 None if questions else fitted_thresholds(INPUT_PACK))
    harm = client.simplify(res).get("harm_severity", {})
    v["harm"] = {"level": harm.get("answer"), "expected": harm.get("expected")}
    if (harm.get("expected") or 0) >= 2.5 and v["decision"] == "allow":
        v["decision"] = "escalate"
    return v
