"""Laya as a tool call for chat agents (OpenAI / Ollama / LiteLLM function-calling format).

Two model-facing tools:
  laya_decide   ad-hoc decisions: classify text into options, place it on a scale, or answer yes/no
                questions (several at once), with calibrated probabilities.
  laya_pack     run a named question pack (tool routing, scope/harm, PII check, trace grading, ...).

Opt-in (FORM_TOOL_SCHEMAS, not in TOOL_SCHEMAS so existing agents' tool menus don't change):
  laya_validate_form   categorize every text-field entry of a submitted form (pass or a failure
                       category) and return a form-level outcome: pass / fix_fields / review / reject.

Plus two agent-loop helpers that are not shown to the model:
  gate_tool_call(request, tool, args)   screen a proposed tool/MCP call before executing it
  screen_tool_result(tool, result)      screen a tool/MCP result for indirect prompt injection

Wiring into an agent:
    from laya_mcp import toolcall
    tools = my_tools + toolcall.TOOL_SCHEMAS            # or ALL_TOOL_SCHEMAS to include form validation
    dispatch = {**my_dispatch, **toolcall.DISPATCH}

Every function returns a JSON-serializable dict and never raises. Failures come back as {"error": ...},
so the model can say the classifier is unavailable instead of crashing the turn.
"""
from . import client, forms, guard, packs

# Packs the MODEL may run by name. The guard packs are left out on purpose: those are for the agent loop,
# and letting the model call the leak screen on its own drafts invites it to reason about the guard.
MODEL_PACKS = ("tool-routing", "scope-and-harm", "guard-pii-secrets", "agent-trace-judge")

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "laya_decide",
        "description": "Make a fast, calibrated DECISION about a piece of text with a small local decision "
                       "model (not a chat model: it returns labels + probabilities in ~20 ms, no prose). "
                       "Use to classify text into one of a few options (kind=choice), rate it on an ordered "
                       "scale (kind=score), or answer one or more yes/no questions about it (kind=yes_no). "
                       "Good for: sorting messages/emails/tickets, sentiment or urgency, 'does this text "
                       "mention X', triage. Keep options to 20 or fewer. Probabilities are estimates, so report "
                       "them and treat anything under ~0.7 as uncertain.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "the text to judge (message, email, post, headline...)"},
            "question": {"type": "string", "description": "what to decide, e.g. 'Which team should handle "
                         "this email?' or 'How urgent is this?'. For yes_no with several questions, use "
                         "`questions` instead."},
            "kind": {"type": "string", "enum": ["choice", "score", "yes_no"],
                     "description": "choice = pick one option; score = place on an ordered scale "
                                    "(options lowest first); yes_no = probability the answer is yes"},
            "options": {"type": "array", "items": {"type": "string"},
                        "description": "choice: the labels (optionally 'label: description'); score: the "
                                       "levels, lowest first. Not used for yes_no."},
            "questions": {"type": "array", "items": {"type": "string"},
                          "description": "yes_no only: several yes/no questions answered in one pass"},
            "multilingual": {"type": "boolean", "description": "true for non-English text"}},
            "required": ["text", "kind"]}}},
    {"type": "function", "function": {
        "name": "laya_pack",
        "description": "Run a ready-made decision pack with the local decision model. Packs: "
                       "tool-routing (which tool a request needs; fields: request), "
                       "scope-and-harm (is a request in scope + how harmful; fields: request, optional scope), "
                       "guard-pii-secrets (does text contain credentials or personal data; fields: text), "
                       "agent-trace-judge (did an answer meet the goal and stay grounded; fields: goal, "
                       "tool_calls, answer).",
        "parameters": {"type": "object", "properties": {
            "pack": {"type": "string", "enum": list(MODEL_PACKS)},
            "fields": {"type": "object", "description": "the pack's state fields, e.g. {\"request\": \"...\"}"}},
            "required": ["pack", "fields"]}}},
]


def _split_option(o):
    label, _, desc = str(o).partition(":")
    return label.strip(), (desc.strip() or None)


def laya_decide(text, kind, question="", options=None, questions=None, multilingual=False, **_):
    try:
        model = "multilingual" if multilingual else "auto"
        text = str(text or "")[:6000]
        if not text.strip():
            return {"error": "text is empty"}
        if kind == "yes_no":
            qs = [q for q in (questions or []) if str(q).strip()] or ([question] if question else [])
            if not qs:
                return {"error": "yes_no needs `question` or `questions`"}
            return client.check(text, qs, model=model)
        if not options:
            return {"error": f"{kind} needs `options`"}
        if kind == "choice":
            return client.classify(text, dict(_split_option(o) for o in options),
                                   question=question or "Which option best describes `text`?", model=model)
        if kind == "score":
            return client.score(text, [str(o) for o in options],
                                question=question or "Where does `text` fall on this scale?", model=model)
        return {"error": f"unknown kind '{kind}'"}
    except client.LayaError as e:
        return {"error": str(e)[:200]}
    except Exception as e:
        return {"error": f"laya_decide failed: {str(e)[:160]}"}


def laya_pack(pack, fields=None, **_):
    try:
        if pack not in MODEL_PACKS:
            return {"error": f"pack must be one of {MODEL_PACKS}"}
        p = packs.get_pack(pack)
        res = client.predict(packs.build_state(p, **(fields or {})), p["questions"])
        return {"pack": pack, "answers": client.simplify(res), "latency_ms": res.get("latency_ms")}
    except (client.LayaError, ValueError, KeyError) as e:
        return {"error": str(e)[:200]}
    except Exception as e:
        return {"error": f"laya_pack failed: {str(e)[:160]}"}


FORM_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "laya_validate_form",
        "description": "Validate the text fields of a submitted form. Each entry gets exactly one category: "
                       "pass, empty_or_placeholder, gibberish, wrong_type, wrong_format, incomplete, off_topic, "
                       "sensitive_data, or abusive. Returns a form outcome (pass / fix_fields / review / "
                       "reject), the per-field results, and a `fix` list of plain-language hints to show the "
                       "submitter. Use when someone submits or pastes a form, application, or request and "
                       "asks whether it is complete and valid.",
        "parameters": {"type": "object", "properties": {
            "form": {"type": "string", "description": "what the form is for, e.g. 'city 311 service request'"},
            "fields": {"type": "array", "description": "the form's fields", "items": {
                "type": "object", "properties": {
                    "name": {"type": "string"}, "label": {"type": "string"},
                    "description": {"type": "string", "description": "what the field asks for"},
                    "required": {"type": "boolean"}, "pattern": {"type": "string"},
                    "min_length": {"type": "integer"}, "max_length": {"type": "integer"}},
                "required": ["name"]}},
            "values": {"type": "object", "description": "the entries, keyed by field name"}},
            "required": ["fields", "values"]}}},
]
ALL_TOOL_SCHEMAS = TOOL_SCHEMAS + FORM_TOOL_SCHEMAS


def laya_validate_form(fields, values, form="a general web form", **_):
    try:
        if not isinstance(fields, list) or not fields:
            return {"error": "fields must be a non-empty list of field specs"}
        out = forms.validate_form(fields, values or {}, form=form or "a general web form")
        for f in out["fields"]:          # keep the model-facing payload small
            f.pop("probabilities", None)
        return out
    except client.LayaError as e:
        return {"error": str(e)[:200]}
    except Exception as e:
        return {"error": f"laya_validate_form failed: {str(e)[:160]}"}


DISPATCH = {"laya_decide": laya_decide, "laya_pack": laya_pack}
ALL_DISPATCH = {**DISPATCH, "laya_validate_form": laya_validate_form}


# ---- agent-loop helpers (not model-facing) ---------------------------------------------------

def gate_tool_call(request, tool, args, fail="allow"):
    """Screen a proposed tool call. Returns the guard verdict ({"decision": allow|escalate|block, ...}).
    `fail` is the decision to return when the Laya server is unreachable ("allow" = fail open)."""
    try:
        return guard.screen("tool-call-safety", request=request, tool_call={"tool": tool, "args": args})
    except Exception as e:
        return {"decision": fail, "error": str(e)[:200]}


def screen_tool_result(tool, result, fail="allow"):
    """Screen a tool result for instructions aimed at the agent before feeding it back to the model."""
    try:
        return guard.screen("tool-result-injection", tool=tool, result=str(result)[:6000])
    except Exception as e:
        return {"decision": fail, "error": str(e)[:200]}
