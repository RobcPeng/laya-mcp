"""Thin, dependency-free client for a running Laya server (`python -m laya.serve`).

Why a client instead of loading the model in-process: Laya is ~1-4 GB of GPU memory per process.
An MCP server is spawned once per editor/agent session and a chat bot may have several workers, so
loading the weights in each of them multiplies VRAM for no gain. One warm `laya.serve` process owns
the GPU; everything else talks to it over HTTP in ~20 ms.

Stdlib only (urllib + json), so it can be imported into any bot/agent venv without dragging in
torch or transformers.

Env:
  LAYA_URL      base URL of the server           (default http://127.0.0.1:7491)
  LAYA_API_KEY  bearer token, if the server sets LAYA_API_KEY
  LAYA_TIMEOUT  per-request timeout in seconds   (default 15)
"""
import json
import os
import time
import urllib.error
import urllib.request

LAYA_URL = os.environ.get("LAYA_URL", "http://127.0.0.1:7491").rstrip("/")
LAYA_API_KEY = os.environ.get("LAYA_API_KEY", "")
LAYA_TIMEOUT = float(os.environ.get("LAYA_TIMEOUT", "15"))

MODELS = ("auto", "english", "multilingual", "typed-decisions")
QTYPES = ("choice", "score", "noul")
MAX_CHOICE_OPTIONS = 20   # the model card: choice accuracy falls off sharply past ~20 options


class LayaError(RuntimeError):
    """Server unreachable, rejected the request, or returned something unusable."""


def _request(method, path, body=None, timeout=None, url=None):
    headers = {"Content-Type": "application/json"}
    if LAYA_API_KEY:
        headers["Authorization"] = f"Bearer {LAYA_API_KEY}"
    data = json.dumps(body).encode() if body is not None else None
    base = (url or LAYA_URL).rstrip("/")
    req = urllib.request.Request(f"{base}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout or LAYA_TIMEOUT) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("detail", "")
        except Exception:
            detail = ""
        raise LayaError(f"laya server HTTP {e.code}: {detail or e.reason}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LayaError(f"laya server unreachable at {base}: {e}") from None
    except ValueError:
        raise LayaError("laya server returned non-JSON") from None


def health(url=None):
    """Server health: which checkpoints are resident and on which device."""
    return _request("GET", "/health", url=url)


def available():
    """True when the server answers /health with status ok. Never raises."""
    try:
        return health().get("status") == "ok"
    except LayaError:
        return False


# ---- question builders -----------------------------------------------------------------------

def choice_q(instructions, options):
    """Pick-one question. `options` = {label: description|None} or a list of labels."""
    if isinstance(options, (list, tuple)):
        options = {str(o): None for o in options}
    if not options:
        raise LayaError("choice question needs at least one option")
    if len(options) > MAX_CHOICE_OPTIONS:
        raise LayaError(f"choice question has {len(options)} options; keep it <= {MAX_CHOICE_OPTIONS} "
                        "(accuracy collapses on long option lists), or split it into two questions")
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def score_q(instructions, levels):
    """Ordinal rubric question. `levels` = ordered list, lowest first."""
    if not levels or len(levels) < 2:
        raise LayaError("score question needs at least two ordered levels")
    return {"type": "score", "instructions": instructions, "criteria": list(levels)}


def noul_q(instructions):
    """Yes/no question answered as a calibrated P(true)."""
    return {"type": "noul", "instructions": instructions}


# ---- core call -------------------------------------------------------------------------------

def predict(state, questions, model="auto", max_len=None, timeout=None, url=None):
    """Ask `questions` about `state`. Returns the server's result:
        {"model", "answers": {name: {...}}, "usage", "routing", "latency_ms"}
    `state` may be a string or any JSON object; questions refer to fields in backticks (`draft`).
    `url` targets a different server than LAYA_URL (e.g. a second server running a fine-tuned checkpoint)."""
    if not isinstance(questions, dict) or not questions:
        raise LayaError("questions must be a non-empty {name: question} object")
    for name, q in questions.items():
        if not isinstance(q, dict) or q.get("type") not in QTYPES:
            raise LayaError(f"question '{name}' needs type in {QTYPES}")
    body = {"state": state, "questions": questions}
    if model and model != "auto":
        if model not in MODELS:
            raise LayaError(f"model must be one of {MODELS}")
        body["model"] = model
    if max_len:
        body["max_len"] = int(max_len)
    t0 = time.perf_counter()
    res = _request("POST", "/v1/systemone", body, timeout=timeout, url=url)
    res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return res


def simplify(result):
    """Collapse a raw result to the fields a caller (or an LLM) needs:
        choice -> {"type","answer","confidence","probabilities"}
        score  -> {"type","answer": most-likely level label,"expected": fractional index (0 = lowest),
                   "confidence","probabilities": {label: p}}
        noul   -> {"type","answer": bool,"p_true","confidence"}
    `confidence` is the probability of the reported answer (the server's answer_confidence)."""
    out = {}
    for name, a in (result.get("answers") or {}).items():
        t = a.get("type")
        conf = a.get("answer_confidence", a.get("confidence"))
        probs = a.get("probabilities") or {}
        if t == "choice":
            out[name] = {"type": t, "answer": a.get("choice"), "confidence": conf, "probabilities": probs}
        elif t == "score":
            legend = a.get("legend") or {}
            labelled = {legend.get(k, k): p for k, p in probs.items()}
            top = max(probs, key=probs.get) if probs else None
            out[name] = {"type": t, "answer": legend.get(top, top), "expected": a.get("score"),
                         "confidence": conf, "probabilities": labelled}
        elif t == "noul":
            p = a.get("noul")
            out[name] = {"type": t, "answer": (p is not None and p >= 0.5), "p_true": p, "confidence": conf}
        else:
            out[name] = a
    return out


# ---- convenience wrappers (one question each) -----------------------------------------------

def classify(text, options, question="Which option best describes `text`?", model="auto"):
    res = predict({"text": text}, {"label": choice_q(question, options)}, model=model)
    return {**simplify(res)["label"], "latency_ms": res["latency_ms"]}


def score(text, levels, question="Where does `text` fall on this scale?", model="auto"):
    res = predict({"text": text}, {"score": score_q(question, levels)}, model=model)
    return {**simplify(res)["score"], "latency_ms": res["latency_ms"]}


def check(text, statements, model="auto"):
    """Batch yes/no: `statements` = list of questions (or {name: question}). One forward pass."""
    if isinstance(statements, str):
        statements = [statements]
    if isinstance(statements, (list, tuple)):
        statements = {f"q{i + 1}": s for i, s in enumerate(statements)}
    qs = {k: noul_q(v) for k, v in statements.items()}
    res = predict({"text": text}, qs, model=model)
    simple = simplify(res)
    return {"answers": {k: {"question": statements[k], "p_true": v["p_true"], "answer": v["answer"]}
                        for k, v in simple.items()},
            "latency_ms": res["latency_ms"]}
