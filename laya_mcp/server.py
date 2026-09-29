"""MCP server for Laya: calibrated classify / score / yes-no decisions, guardrails, and tool-call gating.

Talks to a running `laya.serve` over HTTP (see client.py), so this process stays small: no torch, no
weights, starts instantly, and any number of MCP sessions share one warm model.

Run:   LAYA_URL=http://127.0.0.1:7491 python -m laya_mcp.server        (stdio transport)

Tools
  laya_status              server health, loaded checkpoints, packs, fitted thresholds
  laya_predict             raw call: any state + any questions (choice / score / noul)
  laya_classify            pick one of <= 20 options for a text
  laya_score               place a text on an ordered scale
  laya_check               several yes/no questions about a text in one pass
  laya_batch               the same questions over many texts
  laya_list_packs          the ready-made question packs and the fields each one reads
  laya_pack                run a pack (tool routing, scope/harm, PII, trace judge, guards, ...)
  laya_guard_output        egress DLP: does an assistant reply leak its own internals?
  laya_guard_input         ingress: jailbreak / prompt injection / extraction + harm severity
  laya_gate_tool_call      should this proposed tool/MCP call run? (allow / escalate / block)
  laya_screen_tool_result  does a tool/MCP result carry injected instructions?
  laya_validate_field      categorize one form text-field entry (pass or a failure category)
  laya_validate_form       validate every field of a form + form-level checks -> pass/fix_fields/review/reject
"""
import json

from mcp.server.fastmcp import FastMCP

from . import client, forms, guard, packs

mcp = FastMCP("laya")
packs.load_accelerators()


def _out(fn, *a, **kw):
    try:
        return json.dumps(fn(*a, **kw), ensure_ascii=False, default=str)
    except client.LayaError as e:
        return json.dumps({"error": str(e)})
    except (ValueError, KeyError, TypeError) as e:
        return json.dumps({"error": f"bad input: {e}"})


@mcp.tool()
def laya_status() -> str:
    """Laya server health (resident checkpoints and the device each runs on), the available question
    packs, and which packs have fitted thresholds from a fine-tune run."""
    def run():
        try:
            h = client.health()
        except client.LayaError as e:
            h = {"status": "down", "error": str(e)}
        return {"server": client.LAYA_URL, "health": h, "packs": packs.names(),
                "fitted_thresholds": {n: guard.fitted_thresholds(n) for n in packs.names()
                                      if guard.fitted_thresholds(n)},
                "defaults": {"low": guard.LOW, "high": guard.HIGH}}
    return _out(run)


@mcp.tool()
def laya_predict(state: dict | str, questions: dict, model: str = "auto", max_len: int = 0) -> str:
    """Raw Laya call. `state` = text or a JSON object; `questions` = {name: question}, where a question is
    {"type": "choice", "instructions": "...", "criteria": {label: description|null}}
    | {"type": "score", "instructions": "...", "criteria": [lowest, ..., highest]}
    | {"type": "noul", "instructions": "..."}   (yes/no -> P(true)).
    Refer to state fields in backticks inside instructions (e.g. "Is `body` urgent?").
    model: auto | english | multilingual | typed-decisions. max_len raises the token budget for long
    states or many options. Returns simplified answers plus the raw result."""
    def run():
        res = client.predict(state, questions, model=model, max_len=max_len or None)
        return {"answers": client.simplify(res), "latency_ms": res["latency_ms"],
                "routing": (res.get("routing") or {}).get("model"), "raw": res.get("answers")}
    return _out(run)


@mcp.tool()
def laya_classify(text: str, options: dict | list, question: str = "Which option best describes `text`?",
                  model: str = "auto") -> str:
    """Pick exactly one option for `text`. options = {label: short description} (or a list of labels);
    20 or fewer. Avoid true/false/yes/no as labels. Returns answer, confidence, and the distribution."""
    return _out(client.classify, text, options, question=question, model=model)


@mcp.tool()
def laya_score(text: str, levels: list, question: str = "Where does `text` fall on this scale?",
               model: str = "auto") -> str:
    """Place `text` on an ordered rubric. levels = descriptions from lowest to highest. Returns the most
    likely level, the expected (fractional) level index, and the distribution."""
    return _out(client.score, text, levels, question=question, model=model)


@mcp.tool()
def laya_check(text: str, questions: list | dict, model: str = "auto") -> str:
    """Answer several yes/no questions about `text` in one forward pass. questions = list of questions
    (or {name: question}). Each answer carries P(true)."""
    return _out(client.check, text, questions, model=model)


@mcp.tool()
def laya_batch(texts: list, questions: dict, field: str = "text", model: str = "auto") -> str:
    """Run the same `questions` over many texts (each placed in state field `field`). Use this to label a
    list of emails, tickets, or messages. Returns one simplified result per text, in order."""
    def run():
        out = []
        for t in texts[:500]:
            try:
                res = client.predict({field: t}, questions, model=model)
                out.append({"answers": client.simplify(res), "latency_ms": res["latency_ms"]})
            except client.LayaError as e:
                out.append({"error": str(e)})
        return {"n": len(out), "results": out}
    return _out(run)


@mcp.tool()
def laya_list_packs() -> str:
    """Ready-made question packs: description, the state fields each reads, and its questions."""
    return _out(packs.describe)


@mcp.tool()
def laya_pack(pack: str, fields: dict, pack_params: dict | None = None, as_guard: bool = False,
              model: str = "auto") -> str:
    """Run a question pack. fields = the pack's state fields (see laya_list_packs). pack_params
    customizes parameterized packs: tool-routing takes {"tools": {name: description}}, scope-and-harm
    takes {"scope": "...", "topics": {...}}. as_guard=true returns an allow/escalate/block verdict."""
    def run():
        if as_guard:
            return guard.screen(pack, model=model, pack_params=pack_params, **fields)
        p = packs.get_pack(pack, **(pack_params or {}))
        res = client.predict(packs.build_state(p, **fields), p["questions"], model=model)
        return {"pack": pack, "answers": client.simplify(res), "latency_ms": res["latency_ms"]}
    return _out(run)


@mcp.tool()
def laya_guard_output(user: str, draft: str, low: float = -1, high: float = -1) -> str:
    """Egress DLP for an assistant reply: does `draft` reveal how the assistant is built (storage,
    config/credentials, model, hosting, vendors)? Returns allow / escalate / block with per-signal
    probabilities. Treat 'escalate' as "send to a stronger judge". low/high override the thresholds."""
    return _out(guard.screen_output, user, draft, low=None if low < 0 else low, high=None if high < 0 else high)


@mcp.tool()
def laya_guard_input(prompt: str, low: float = -1, high: float = -1) -> str:
    """Ingress screen for a user prompt: jailbreak, prompt injection, system-prompt extraction, and a
    harm-severity score. Returns allow / escalate / block."""
    return _out(guard.screen_input, prompt, low=None if low < 0 else low, high=None if high < 0 else high)


@mcp.tool()
def laya_gate_tool_call(request: str, tool: str, args: dict | None = None) -> str:
    """Before executing a tool/MCP call: does it match what the user asked, does it have side effects,
    does it send private data out, and how risky is it? Returns allow / escalate / block plus answers."""
    return _out(guard.screen, "tool-call-safety", request=request, tool_call={"tool": tool, "args": args or {}})


@mcp.tool()
def laya_screen_tool_result(tool: str, result: str) -> str:
    """After a tool/MCP call returns: does the result (web page, email, file) contain instructions aimed
    at the agent (indirect prompt injection)? Returns allow / escalate / block."""
    return _out(guard.screen, "tool-result-injection", tool=tool, result=result[:6000])


@mcp.tool()
def laya_validate_field(entry: str, label: str, description: str = "", form: str = "a general web form",
                        required: bool = True, pattern: str = "", min_length: int = 0, max_length: int = 0,
                        allow_sensitive: bool = False) -> str:
    """Categorize one form text-field entry. Deterministic rules run first (required, length, regex
    pattern, SSN / card / password detection); otherwise Laya picks one category: pass,
    empty_or_placeholder, gibberish, wrong_type, wrong_format, incomplete, off_topic, sensitive_data,
    abusive. Returns the category, its source (rules|laya), confidence, needs_review, quality, and an
    outcome (pass / fix / review / reject)."""
    spec = {"name": label, "label": label, "description": description, "required": required,
            "pattern": pattern or None, "min_length": min_length or None, "max_length": max_length or None,
            "allow_sensitive": allow_sensitive}
    return _out(forms.validate_field, spec, entry, form=form)


@mcp.tool()
def laya_validate_form(fields: list, values: dict, form: str = "a general web form",
                       check_consistency: bool = True) -> str:
    """Validate a whole form. fields = [{"name", "label", "description", "required", "pattern",
    "min_length", "max_length", "allow_sensitive"}]; values = {name: entry}. Every field gets a category
    (pass included); then a form-level contradiction check across fields. Returns outcome
    (pass / fix_fields / review / reject), per-field results, form checks, and `fix` hints for the
    submitter."""
    return _out(forms.validate_form, fields, values, form=form, check_consistency=check_consistency)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
