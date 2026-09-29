"""Form text-field validation: categorize every entry (`pass` included), then roll up to a form verdict.

Mental model: a clerk at an intake window. First the clerk checks the mechanical things with a ruler:
is the box filled in, is it too long, is the ZIP five digits. Those checks are rules, and a rule never
needs a model. Only then does the clerk read the answer and judge it: is this a real description
of the problem, or "asdf"? That judgment is Laya's job. Last, the clerk looks at the whole form: do the
answers agree with each other?

Three layers:
  1. rules (deterministic, free):   required / min_length / max_length / pattern, plus SSNs,
                                    Luhn-valid card numbers, and password/key assignments
  2. Laya per field:                category (pass | empty_or_placeholder | gibberish | wrong_type |
                                    wrong_format | incomplete | off_topic | sensitive_data | abusive),
                                    needs_review, quality
  3. Laya per form:                 contradiction across fields, genuine vs test/spam submission

Form outcome:
  pass        every field passed and the form is consistent
  fix_fields  some fields failed in ways the submitter can fix (empty, wrong format, incomplete...)
  review      low confidence, a needs-review flag, a contradiction, or sensitive data; a person decides
  reject      abusive content, or a form that is mostly gibberish / not a genuine submission

Field spec (dict):
  {"name": "zip", "label": "ZIP code", "description": "5-digit US ZIP of the service address",
   "required": true, "min_length": 5, "max_length": 10, "pattern": "^\\d{5}(-\\d{4})?$",
   "allow_sensitive": false, "categories": {...optional override...}}
"""
import json
import os
import re

from . import client, packs

# Categories the submitter can fix themselves vs ones that need a person or mean rejection.
FIXABLE = {"empty_or_placeholder", "wrong_type", "wrong_format", "incomplete", "off_topic"}
REVIEW = {"sensitive_data"}
REJECT = {"abusive", "gibberish"}

# Policy knobs. Defaults suit the BASE checkpoint, which spreads probability across nine categories
# (a correct `pass` often lands at 0.4-0.55), so the cutoff is modest. Raise it after fine-tuning.
MIN_CONFIDENCE = float(os.environ.get("LAYA_FORM_MIN_CONFIDENCE", "0.4"))
CONTRADICTION_P = float(os.environ.get("LAYA_FORM_CONTRADICTION_P", "0.6"))
# P(genuine) below this rejects the whole form. Off (0) by default, because the base checkpoint scored a
# clean 311 form at 0.12. Turn it on only with a fine-tuned checkpoint that has been checked on real forms.
GENUINE_MIN_P = float(os.environ.get("LAYA_FORM_GENUINE_MIN_P", "0"))

# Things a rule can find with certainty; no model needed. Checked on free-text fields unless the field
# spec sets "allow_sensitive": true (e.g. a field that legitimately asks for an account number).
_SSN = re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b|\b000-\d{2}-\d{4}\b")
_SECRET = re.compile(r"(?i)\b(pass(word|wd)?|pwd|api[_ -]?key|secret|token)\s*[:=]\s*\S{4,}")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn(digits):
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total, alt = total + n, not alt
    return total % 10 == 0


def has_sensitive(text):
    if _SSN.search(text) or _SECRET.search(text):
        return True
    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            return True
    return False


def _field_text(spec):
    label = spec.get("label") or spec.get("name") or "field"
    desc = spec.get("description")
    return f"{label}: {desc}" if desc else label


def check_rules(spec, value):
    """Deterministic checks. Returns a category string when a rule fails, else None."""
    v = "" if value is None else str(value)
    if not v.strip():
        return "empty_or_placeholder" if spec.get("required", True) else "pass"
    if spec.get("min_length") and len(v.strip()) < int(spec["min_length"]):
        return "incomplete"
    if spec.get("max_length") and len(v) > int(spec["max_length"]):
        return "wrong_format"
    if spec.get("pattern") and not re.search(spec["pattern"], v.strip()):
        return "wrong_format"
    if not spec.get("allow_sensitive") and has_sensitive(v):
        return "sensitive_data"
    return None


def validate_field(spec, value, form="a general web form", model="auto", url=None, use_rules=True):
    """Categorize one entry. Returns {"field","category","source": rules|laya,"confidence","needs_review",
    "quality","probabilities","outcome": pass|fix|review|reject}."""
    name = spec.get("name") or spec.get("label") or "field"
    v = "" if value is None else str(value)
    if use_rules:
        rule = check_rules(spec, v)
        if rule:                                   # a rule decided it (incl. an empty optional field -> pass)
            return _field_result(name, rule, "rules", 1.0, False, None, {})
    pack = packs.get_pack("form-field-validation", categories=spec.get("categories"))
    state = packs.build_state(pack, form=form, field=_field_text(spec), entry=v[:3000])
    res = client.simplify(client.predict(state, pack["questions"], model=model, url=url))
    cat = res["category"]
    return _field_result(name, cat["answer"], "laya", cat["confidence"], res["needs_review"]["answer"],
                         res["quality"]["answer"], cat["probabilities"],
                         review_p=res["needs_review"]["p_true"])


def _field_result(name, category, source, confidence, needs_review, quality, probs, review_p=None):
    if category == "pass":
        outcome = "review" if (needs_review or (confidence or 0) < MIN_CONFIDENCE) else "pass"
    elif category in REJECT:
        outcome = "reject"
    elif category in REVIEW or (confidence or 0) < MIN_CONFIDENCE:
        outcome = "review"
    else:
        outcome = "fix"
    return {"field": name, "category": category, "outcome": outcome, "source": source,
            "confidence": confidence, "needs_review": needs_review, "needs_review_p": review_p,
            "quality": quality, "probabilities": probs}


def validate_form(fields, values, form="a general web form", model="auto", url=None, use_rules=True,
                  check_consistency=True):
    """Validate a whole form. `fields` = list of field specs; `values` = {field name: entry}.
    Returns {"outcome", "summary", "fields": [...per-field results...], "form_checks": {...},
    "fix": [{"field","category","hint"}]}. `fix` is what to tell the submitter."""
    results = [validate_field(s, values.get(s.get("name") or s.get("label")), form=form, model=model,
                              url=url, use_rules=use_rules) for s in fields]
    form_checks = {}
    if check_consistency:
        filled = {(s.get("label") or s.get("name")): values.get(s.get("name") or s.get("label"))
                  for s in fields if str(values.get(s.get("name") or s.get("label")) or "").strip()}
        if len(filled) >= 2:
            pack = packs.get_pack("form-consistency")
            state = packs.build_state(pack, form=form, entries=json.dumps(filled, ensure_ascii=False)[:4000])
            fc = client.simplify(client.predict(state, pack["questions"], model=model, url=url))
            form_checks = {"contradiction_p": fc["contradiction"]["p_true"], "genuine_p": fc["genuine"]["p_true"]}

    outcomes = [r["outcome"] for r in results]
    n_reject = outcomes.count("reject")
    if n_reject and (any(r["category"] == "abusive" for r in results) or n_reject * 2 >= len(results)):
        outcome = "reject"
    elif GENUINE_MIN_P and form_checks and form_checks["genuine_p"] < GENUINE_MIN_P:
        outcome = "reject"
    elif "review" in outcomes or "reject" in outcomes or \
            (form_checks and form_checks["contradiction_p"] >= CONTRADICTION_P):
        outcome = "review"
    elif "fix" in outcomes:
        outcome = "fix_fields"
    else:
        outcome = "pass"
    fix = [{"field": r["field"], "category": r["category"], "hint": HINTS.get(r["category"], "")}
           for r in results if r["outcome"] == "fix"]
    passed = outcomes.count("pass")
    return {"outcome": outcome, "summary": f"{passed}/{len(results)} fields passed",
            "fields": results, "form_checks": form_checks, "fix": fix}


HINTS = {
    "empty_or_placeholder": "This field is required. Please enter a real answer.",
    "wrong_type": "This doesn't look like the information this field asks for.",
    "wrong_format": "The format isn't valid for this field.",
    "incomplete": "Please add more detail.",
    "off_topic": "This doesn't answer the question for this field.",
    "sensitive_data": "Please remove passwords, ID numbers, or card numbers from this field.",
}
